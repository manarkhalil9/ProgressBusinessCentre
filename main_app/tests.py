from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import BookingForm
from .models import Branch, Booking, BusinessRegistration, MeetingRoom, Office, VisitRequest
from .admin import approve_bookings, progress_registrations, reject_visits


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RequestWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("client", "client@example.com", "pass")
        self.other_user = User.objects.create_user("other", "other@example.com", "pass")
        self.branch = Branch.objects.create(
            name="Seef", address="Bahrain", phone="1", email="branch@example.com", opening_hours="8-6"
        )
        self.room = MeetingRoom.objects.create(
            branch=self.branch, name="Boardroom", capacity=8, price_per_hour=Decimal("18.000")
        )
        self.office = Office.objects.create(
            branch=self.branch, name="Office A", description="Private office", price_per_month=Decimal("500.000")
        )

    def booking(self, **overrides):
        values = {
            "user": self.user,
            "meeting_room": self.room,
            "client_name": "Client",
            "phone": "123",
            "email": "client@example.com",
            "business_type": "Consulting",
            "reason_for_booking": "Client meeting",
            "start_date": date.today() + timedelta(days=10),
            "start_time": time(9),
            "end_time": time(10),
            "status": "pending",
        }
        values.update(overrides)
        return Booking.objects.create(**values)

    def test_new_booking_form_requires_business_context(self):
        form = BookingForm(data={}, resource=self.room)
        self.assertFalse(form.is_valid())
        self.assertIn("business_type", form.errors)
        self.assertIn("reason_for_booking", form.errors)

    def test_client_submission_is_pending_and_sends_received_emails(self):
        self.client.force_login(self.user)
        requested_date = date.today() + timedelta(days=11)
        response = self.client.post(reverse("book", args=("room", self.room.pk)), {
            "client_name": "Client",
            "phone": "123",
            "email": "client@example.com",
            "commercial_registration": "",
            "business_type": "Consulting",
            "reason_for_booking": "Client workshop",
            "start_date": requested_date.isoformat(),
            "end_date": "",
            "start_time": "09:00",
            "end_time": "10:00",
        })
        self.assertRedirects(response, reverse("booking_success"))
        booking = Booking.objects.get(reason_for_booking="Client workshop")
        self.assertEqual(booking.status, "pending")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("requires review", mail.outbox[0].body)
        self.assertIn("pending review", mail.outbox[1].body)
        self.assertEqual(mail.outbox[1].to, ["client@example.com"])
        self.assertEqual(mail.outbox[1].subject, "Booking Request Received - Progress Business Centre")

    def test_pending_and_approved_block_but_rejected_and_cancelled_release_slot(self):
        booking = self.booking()
        start = booking.start_date
        self.assertFalse(self.room.is_available(
            datetime.combine(start, time(9)),
            datetime.combine(start, time(10)),
        ))
        booking.status = "rejected"
        booking.save(update_fields=["status"])
        self.assertTrue(self.room.is_available(
            datetime.combine(start, time(9)),
            datetime.combine(start, time(10)),
        ))

    def test_booking_status_emails_cover_every_transition_without_duplicates(self):
        booking = self.booking()
        mail.outbox.clear()
        expected = [
            ("approved", "Booking Request Approved - Progress Business Centre", "final arrangements and pricing"),
            ("rejected", "Booking Request Update - Progress Business Centre", "unable to approve"),
            ("cancelled", "Booking Request Cancelled - Progress Business Centre", "has been cancelled"),
            ("pending", "Booking Request Under Review - Progress Business Centre", "pending review"),
        ]
        for index, (status, subject, body_text) in enumerate(expected, start=1):
            booking.status = status
            booking.save(update_fields=["status"])
            self.assertEqual(len(mail.outbox), index)
            self.assertEqual(mail.outbox[-1].to, [booking.email])
            self.assertEqual(mail.outbox[-1].subject, subject)
            self.assertIn(body_text, mail.outbox[-1].body)

        booking.client_name = "Updated Client"
        booking.save(update_fields=["client_name"])
        self.assertEqual(len(mail.outbox), len(expected))
        booking.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), len(expected))

    def test_cr_support_initial_submission_emails_admin_and_client(self):
        self.client.force_login(self.user)
        mail.outbox.clear()
        response = self.client.post(reverse("cr_support"), {
            "request_type": "new",
            "company_name": "Example CR",
            "owner_name": "Client",
            "commercial_registration": "",
            "business_type": "Consulting",
            "cpr_number": "",
        })
        self.assertRedirects(response, reverse("cr_support_success"))
        registration = BusinessRegistration.objects.get(company_name="Example CR")
        self.assertEqual(registration.status, "pending")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("New CR Support Request", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[1].to, [self.user.email])
        self.assertEqual(mail.outbox[1].subject, "CR Support Request Received - Progress Business Centre")
        self.assertIn("does not issue or authorize", mail.outbox[1].body)

    def test_cr_support_status_emails_cover_every_transition_without_duplicates(self):
        registration = BusinessRegistration.objects.create(
            user=self.user, company_name="Example", owner_name="Client", business_type="Consulting"
        )
        mail.outbox.clear()
        expected = [
            ("approved", "CR Support Request Approved - Progress Business Centre", "assist you with the process"),
            ("in_progress", "CR Support in Progress - Progress Business Centre", "started providing CR support"),
            ("completed", "CR Support Completed - Progress Business Centre", "has been completed"),
            ("rejected", "CR Support Request Update - Progress Business Centre", "unable to proceed"),
            ("pending", "CR Support Request Under Review - Progress Business Centre", "pending review"),
        ]
        for index, (status, subject, body_text) in enumerate(expected, start=1):
            registration.status = status
            registration.save(update_fields=["status"])
            self.assertEqual(len(mail.outbox), index)
            self.assertEqual(mail.outbox[-1].to, [self.user.email])
            self.assertEqual(mail.outbox[-1].subject, subject)
            self.assertIn(body_text, mail.outbox[-1].body)

        registration.owner_name = "Updated Owner"
        registration.save(update_fields=["owner_name"])
        registration.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), len(expected))

    def test_visit_initial_submission_emails_admin_and_client(self):
        self.client.force_login(self.user)
        mail.outbox.clear()
        response = self.client.post(reverse("visit"), {
            "full_name": "Client",
            "email": "visit@example.com",
            "phone": "123",
            "preferred_date": (date.today() + timedelta(days=5)).isoformat(),
            "preferred_time": "10:00",
            "notes": "Tour",
        })
        self.assertRedirects(response, reverse("visit_success"))
        visit = VisitRequest.objects.get(email="visit@example.com")
        self.assertEqual(visit.status, "pending")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("New Visit Request", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[1].to, ["visit@example.com"])
        self.assertEqual(mail.outbox[1].subject, "Visit Request Received - Progress Business Centre")
        self.assertIn("visit request", mail.outbox[1].body)

    def test_visit_status_emails_cover_every_transition_without_duplicates(self):
        visit = VisitRequest.objects.create(
            user=self.user, full_name="Client", email="client@example.com", phone="1",
            preferred_date=date.today() + timedelta(days=3), preferred_time=time(10), status="pending"
        )
        mail.outbox.clear()
        expected = [
            ("approved", "Visit Request Approved - Progress Business Centre", "has been approved"),
            ("rejected", "Visit Request Update - Progress Business Centre", "unable to approve"),
            ("pending", "Visit Request Under Review - Progress Business Centre", "pending confirmation"),
        ]
        for index, (status, subject, body_text) in enumerate(expected, start=1):
            visit.status = status
            visit.save(update_fields=["status"])
            self.assertEqual(len(mail.outbox), index)
            self.assertEqual(mail.outbox[-1].to, [visit.email])
            self.assertEqual(mail.outbox[-1].subject, subject)
            self.assertIn(body_text, mail.outbox[-1].body)

        visit.notes = "Updated"
        visit.save(update_fields=["notes"])
        visit.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), len(expected))

    def test_admin_bulk_actions_use_save_and_trigger_status_notifications(self):
        booking = self.booking(start_date=date.today() + timedelta(days=30))
        registration = BusinessRegistration.objects.create(
            user=self.user, company_name="Bulk CR", owner_name="Client", business_type="Trading"
        )
        visit = VisitRequest.objects.create(
            user=self.user, full_name="Client", email="client@example.com", phone="1",
            preferred_date=date.today() + timedelta(days=31), preferred_time=time(11)
        )
        mail.outbox.clear()
        approve_bookings(None, None, Booking.objects.filter(pk=booking.pk))
        progress_registrations(None, None, BusinessRegistration.objects.filter(pk=registration.pk))
        reject_visits(None, None, VisitRequest.objects.filter(pk=visit.pk))
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            {message.subject for message in mail.outbox},
            {
                "Booking Request Approved - Progress Business Centre",
                "CR Support in Progress - Progress Business Centre",
                "Visit Request Update - Progress Business Centre",
            },
        )

    def test_dashboard_requires_login_and_never_exposes_other_users_requests(self):
        mine = self.booking()
        other = self.booking(user=self.other_user, email="other@example.com", client_name="Other",
                             start_date=date.today() + timedelta(days=20))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, mine.client_name)
        self.assertNotContains(response, other.client_name)


class SpacesPageTests(TestCase):
    def setUp(self):
        self.head_office = Branch.objects.create(
            name="Progress Business Center Head Office",
            address="Seef",
            phone="1",
            email="head@example.com",
            opening_hours="8-6",
        )
        self.al_raya = Branch.objects.create(
            name="Al Raya Branch",
            address="Bahrain",
            phone="2",
            email="raya@example.com",
            opening_hours="8-6",
        )
        self.room = MeetingRoom.objects.create(
            branch=self.head_office,
            name="Executive Boardroom",
            capacity=10,
            price_per_hour=Decimal("20.000"),
        )
        self.head_office_space = Office.objects.create(
            branch=self.head_office,
            name="Head Office Suite",
            description="Private workspace",
            price_per_month=Decimal("500.000"),
        )
        self.al_raya_space = Office.objects.create(
            branch=self.al_raya,
            name="Al Raya Suite",
            description="Private workspace",
            price_per_month=Decimal("450.000"),
        )

    def test_spaces_page_groups_records_by_their_branch_relationship(self):
        response = self.client.get(reverse("spaces"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.room.name)
        self.assertEqual(list(response.context["head_office_offices"]), [self.head_office_space])
        self.assertEqual(list(response.context["al_raya_offices"]), [self.al_raya_space])

    def test_old_listing_and_cr_paths_redirect_to_canonical_routes(self):
        self.assertRedirects(
            self.client.get(reverse("rooms")),
            reverse("spaces"),
            status_code=301,
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse("offices")),
            reverse("spaces"),
            status_code=301,
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get(reverse("business_register")),
            reverse("cr_support"),
            status_code=301,
            fetch_redirect_response=False,
        )
