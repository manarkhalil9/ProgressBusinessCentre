from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import BookingForm
from .models import Branch, Booking, BusinessRegistration, MeetingRoom, Office, VisitRequest


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

    def test_status_email_only_on_actual_transition(self):
        booking = self.booking()
        mail.outbox.clear()
        booking.status = "approved"
        booking.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Approved", mail.outbox[0].subject)
        booking.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), 1)

    def test_visit_and_registration_status_transitions_email_once(self):
        visit = VisitRequest.objects.create(
            user=self.user, full_name="Client", email="client@example.com", phone="1",
            preferred_date=date.today() + timedelta(days=3), preferred_time=time(10), status="pending"
        )
        registration = BusinessRegistration.objects.create(
            user=self.user, company_name="Example", owner_name="Client", business_type="Consulting"
        )
        mail.outbox.clear()
        visit.status = "approved"
        visit.save(update_fields=["status"])
        registration.status = "active"
        registration.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), 2)
        visit.save(update_fields=["status"])
        registration.save(update_fields=["status"])
        self.assertEqual(len(mail.outbox), 2)

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
