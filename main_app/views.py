from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from .models import (
    Service, Feature, Branch, MeetingRoom, Event, GalleryImage,
    FAQ, Contact, VisitRequest, BusinessRegistration, Referral,
    Office, Booking
)
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import (
    BusinessRegistrationForm, VisitRequestForm, BookingForm, ReferralForm
)
from django.db.models import Q
from django.http import Http404
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from datetime import date, datetime, timedelta
import calendar


# ---------- HOME ----------
def home(request):

    all_images = GalleryImage.objects.all() 

    context = {'all_images' : all_images,}

    return render(request, 'index.html', context)


# ---------- ABOUT ----------
def about(request):
    # Get all features, limit to 6 (no 'available' filter)
    features = Feature.objects.all()[:6]
    
    return render(
        request,
        'about.html',
        {'features': features}
    )


# ---------- SERVICES ----------
class ServiceList(ListView):
    model = Service
    template_name = 'services/index.html'
    context_object_name = 'services'


# ---------- MEETING ROOMS ----------
class MeetingRoomListView(ListView):
    model = MeetingRoom
    template_name = 'rooms/index.html'
    context_object_name = 'rooms'


class MeetingRoomDetailView(DetailView):
    model = MeetingRoom
    template_name = 'rooms/detail.html'
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = date.today()
        return context


# ---------- OFFICES ----------
class OfficeListView(ListView):
    model = Office
    template_name = "offices/index.html"
    context_object_name = "offices"

    def get_queryset(self):
        return Office.objects.select_related("branch")


class OfficeDetailView(DetailView):
    model = Office
    template_name = "offices/detail.html"
    context_object_name = "office"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = date.today()
        return context


# ---------- GALLERY ----------
class GalleryListView(ListView):
    model = GalleryImage
    template_name = 'gallery/index.html'
    context_object_name = 'gallery'


class GalleryDetailView(DetailView):
    model = GalleryImage
    template_name = 'gallery/detail.html'
    context_object_name = 'image'


# ---------- FAQ ----------
class FAQListView(ListView):
    model = FAQ
    template_name = 'faq/index.html'
    context_object_name = 'faqs'


# ---------- CONTACT ----------
class ContactView(DetailView):
    model = Contact
    template_name = 'contact/detail.html'
    context_object_name = 'contact'

    def get_object(self):
        return Contact.objects.first()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['branches'] = Branch.objects.all()
        return context

# ---------- VISIT REQUESTS ----------
class VisitCreateView(LoginRequiredMixin, CreateView):
    model = VisitRequest
    form_class = VisitRequestForm
    template_name = "visits/register.html"
    success_url = reverse_lazy("visit_success")

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = "pending"
        response = super().form_valid(form)
        visit = self.object

        # Retrieve information safely from visit or request user
        user_email = getattr(visit, 'email', None) or self.request.user.email
        client_name = getattr(visit, 'name', None) or self.request.user.get_full_name() or self.request.user.username
        preferred_date = getattr(visit, 'preferred_date', getattr(visit, 'date', 'Not specified'))
        preferred_time = getattr(visit, 'preferred_time', getattr(visit, 'time', 'Not specified'))

        # 1. Admin Email
        admin_subject = f"New Visit Request: {client_name}"
        admin_message = (
            f"A new visit request has been submitted.\n\n"
            f"--- Visitor Details ---\n"
            f"Name: {client_name}\n"
            f"Email: {user_email}\n"
            f"Phone: {getattr(visit, 'phone', 'Not provided')}\n"
            f"Preferred Date: {preferred_date}\n"
            f"Preferred Time: {preferred_time}\n"
        )

        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )

        # 2. Client Confirmation Email
        if user_email:
            client_subject = "Visit Request Received - Progress Business Centre"
            client_message = (
                f"Dear {client_name},\n\n"
                f"Thank you for arranging a visit to Progress Business Centre.\n\n"
                f"We have received your meeting request for {preferred_date} at {preferred_time}.\n"
                f"Your request is pending confirmation. Our team will review your preferred schedule and reach out to you shortly.\n\n"
                f"Status: Pending\n\n"
                f"Best regards,\nThe Progress Center Team"
            )

            send_mail(
                subject=client_subject,
                message=client_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=True,
            )

        return response


def visit_success(request):
    return render(request, "visits/success.html")


# ---------- REFERRALS ----------
class ReferralCreateView(LoginRequiredMixin, CreateView):
    model = Referral
    form_class = ReferralForm
    template_name = "referrals/index.html"
    success_url = reverse_lazy("referral_success")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        referral = self.object

        referrer_name = self.request.user.get_full_name() or self.request.user.username
        referrer_email = self.request.user.email

        referred_name = getattr(referral, 'referred_name', getattr(referral, 'name', 'N/A'))
        referred_email = getattr(referral, 'referred_email', getattr(referral, 'email', 'N/A'))
        referred_phone = getattr(referral, 'referred_phone', getattr(referral, 'phone', 'N/A'))

        # 1. Admin Email
        admin_subject = f"New Referral Received from {referrer_name}"
        admin_message = (
            f"A new referral has been submitted on the portal.\n\n"
            f"--- Referrer (Submitted By) ---\n"
            f"Name: {referrer_name}\n"
            f"Email: {referrer_email}\n\n"
            f"--- Referred Lead Info ---\n"
            f"Name: {referred_name}\n"
            f"Email: {referred_email}\n"
            f"Phone: {referred_phone}\n"
        )

        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )

        # 2. Referrer Confirmation Email
        if referrer_email:
            client_subject = "Thank You for Your Referral - Progress Center"
            client_message = (
                f"Dear {referrer_name},\n\n"
                f"Thank you for referring {referred_name} to Progress Business Centre!\n\n"
                f"We have received the referral information and our team will get in touch with them promptly.\n"
                f"We appreciate your support and confidence in our workspace solutions.\n\n"
                f"Best regards,\nThe Progress Center Team"
            )

            send_mail(
                subject=client_subject,
                message=client_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[referrer_email],
                fail_silently=True,
            )

        return response


def referral_success(request):
    return render(request, "referrals/success.html")


# ---------- BUSINESS REGISTRATION ----------
class BusinessRegistrationCreateView(LoginRequiredMixin, CreateView):
    model = BusinessRegistration
    form_class = BusinessRegistrationForm
    template_name = "business/register.html"
    success_url = reverse_lazy("business_success")

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = "pending"
        
        # super().form_valid(form) saves the object to the database, 
        # which means the files are now successfully uploaded and accessible.
        response = super().form_valid(form)
        registration = self.object

        user_email = getattr(registration, 'email', None) or self.request.user.email
        client_name = getattr(registration, 'full_name', None) or getattr(registration, 'client_name', None) or self.request.user.get_full_name() or self.request.user.username
        company_name = getattr(registration, 'company_name', 'Business Setup Request')

        # 1. Admin Email (Updated to use EmailMessage for attachments)
        admin_subject = f"New Business Registration: {company_name}"
        admin_message = (
            f"A new business registration application has been submitted.\n\n"
            f"--- Client Information ---\n"
            f"Name: {client_name}\n"
            f"Company / Activity: {company_name}\n"
            f"Email: {user_email}\n"
            f"Phone: {getattr(registration, 'phone', 'Not provided')}\n"
        )

        # Initialize the EmailMessage object
        admin_email = EmailMessage(
            subject=admin_subject,
            body=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_EMAIL],
        )

        # Attach CPR Document if the user uploaded one
        if registration.cpr_document:
            admin_email.attach(
                registration.cpr_document.name,
                registration.cpr_document.read()
            )

        # Attach Passport Document if the user uploaded one
        if registration.passport_document:
            admin_email.attach(
                registration.passport_document.name,
                registration.passport_document.read()
            )

        # Send the admin email with attachments
        admin_email.send(fail_silently=True)

        # 2. Client Confirmation Email (Can remain as send_mail since there are no attachments)
        if user_email:
            client_subject = "Business Registration Received - Progress Business Centre"
            client_message = (
                f"Dear {client_name},\n\n"
                f"Thank you for submitting your business registration request for {company_name}.\n\n"
                f"Your application is pending review. Our corporate setup specialists will reach out to assist with the next steps.\n\n"
                f"Status: Pending / Under Review\n\n"
                f"Best regards,\nThe Progress Center Team"
            )

            send_mail(
                subject=client_subject,
                message=client_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=True,
            )

        return response


def business_success(request):
    return render(request, 'business/success.html')


# ---------- BOOKING ----------
class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = "bookings/create.html"

    def get_resource(self):
        resource_type = self.kwargs["resource_type"]
        pk = self.kwargs["pk"]

        if resource_type == "room":
            return get_object_or_404(MeetingRoom, pk=pk)

        if resource_type == "office":
            return get_object_or_404(Office, pk=pk)

        raise Http404("Booking item not found.")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.user = self.request.user
        resource = self.get_resource()
        
        if isinstance(resource, MeetingRoom):
            form.instance.meeting_room = resource
        elif isinstance(resource, Office):
            form.instance.office = resource
            
        return form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["resource"] = self.get_resource()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["client_name"] = (
            self.request.user.get_full_name()
            or self.request.user.username
        )
        initial["email"] = self.request.user.email
        initial["start_date"] = date.today()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.get_resource()

        context["resource"] = resource
        context["resource_type"] = self.kwargs["resource_type"]

        today = date.today()
        context["today"] = today

        # Provide a 5-year range for long-term leases (e.g., 2026 to 2031)
        context["years"] = range(today.year, today.year + 6)

        # Helper function to securely parse incoming date strings
        def parse_date(date_str, default=None):
            if date_str:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            return default

        # 1. Retrieve actively selected dates (from POST, GET parameters, or defaults)
        selected_start_date = parse_date(
            self.request.POST.get("start_date") or self.request.GET.get("start_date"), 
            today
        )
        selected_end_date = parse_date(
            self.request.POST.get("end_date") or self.request.GET.get("end_date"), 
            None
        )

        context["selected_start_date"] = selected_start_date
        context["selected_end_date"] = selected_end_date

        # 2. Retrieve independent view months for start and end calendars
        start_view_date = parse_date(self.request.GET.get("start_view"), selected_start_date)
        end_view_date = parse_date(self.request.GET.get("end_view"), selected_end_date or start_view_date)

        context["start_view_date"] = start_view_date
        context["end_view_date"] = end_view_date

        # 3. Generate independent calendar data for BOTH views using prefixes
        def get_cal_data(view_date, prefix):
            year = view_date.year
            month = view_date.month
            cal = calendar.Calendar(firstweekday=6) # Sunday
            
            prev_month = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1)
            next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

            return {
                f"{prefix}_month_days": cal.monthdatescalendar(year, month),
                f"{prefix}_month_name": calendar.month_name[month],
                f"{prefix}_year": year,
                f"{prefix}_month": month,
                f"{prefix}_previous_month": prev_month.strftime("%Y-%m-%d"),
                f"{prefix}_next_month": next_month.strftime("%Y-%m-%d"),
            }

        context.update(get_cal_data(start_view_date, "start"))
        context.update(get_cal_data(end_view_date, "end"))

        # 4. Handle unavailable dates and time slots
        if isinstance(resource, Office):
            unavail_start = resource.get_unavailable_dates(start_view_date.year, start_view_date.month)
            unavail_end = resource.get_unavailable_dates(end_view_date.year, end_view_date.month)
            context["unavailable_dates"] = unavail_start.union(unavail_end)
        else:
            context["unavailable_dates"] = set()

        if isinstance(resource, MeetingRoom):
            context["available_slots"] = resource.get_available_time_slots(
                selected_start_date,
                interval_minutes=60,
            )
        else:
            context["available_slots"] = None

        return context

    def form_valid(self, form):
        resource = self.get_resource()

        if isinstance(resource, MeetingRoom):
            start_dt = datetime.combine(
                form.cleaned_data["start_date"],
                form.cleaned_data["start_time"],
            )

            end_dt = datetime.combine(
                form.cleaned_data["start_date"],
                form.cleaned_data["end_time"],
            )

            duration_info = f"Time: {form.cleaned_data['start_time'].strftime('%I:%M %p')} to {form.cleaned_data['end_time'].strftime('%I:%M %p')}"

        else:
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date") or start_date
            form.instance.end_date = end_date

            duration_info = f"Duration: {start_date} to {end_date}"

        # Availability controls whether the request may be submitted; staff approval
        # is always a separate manual decision in Django Admin.
        form.instance.status = "pending"

        response = super().form_valid(form)
        booking = self.object

        contact_number = getattr(booking, 'phone', 'Not provided')
        admin_subject = f"New Booking Request: {booking.client_name}"
        admin_message = (
            f"A new space booking request requires review.\n\n"
            f"--- Client Information ---\n"
            f"Name: {booking.client_name}\n"
            f"Email: {booking.email}\n"
            f"Contact Number: {contact_number}\n\n"
            f"Commercial Registration: {booking.commercial_registration or 'Not provided'}\n"
            f"Business Type: {booking.business_type}\n"
            f"Reason for Booking: {booking.reason_for_booking}\n\n"
            f"--- Booking Details ---\n"
            f"Resource: {booking.meeting_room or booking.office}\n"
            f"Resource Type: {'Meeting Room' if booking.meeting_room else 'Office'}\n"
            f"Branch: {(booking.meeting_room or booking.office).branch if (booking.meeting_room or booking.office) else 'Not provided'}\n"
            f"Start Date: {booking.start_date}\n"
            f"{duration_info}\n"
            f"Status: Pending\n"
        )

        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )

        client_subject = "Booking Request Received - Progress Business Centre"
        client_message = (
            f"Dear {booking.client_name},\n\n"
            f"Thank you for submitting your booking request for {booking.meeting_room or booking.office}.\n\n"
            "Your request has been received and is currently pending review by our team.\n\n"
            "Submitting a request does not confirm the booking. Our team will review the requested dates, "
            "intended use, availability, and final pricing before approval.\n\n"
            "You will receive another email once your request has been approved or rejected.\n\n"
            "Status: Pending\n\nBest regards,\nProgress Business Centre"
        )

        send_mail(
            subject=client_subject,
            message=client_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
            fail_silently=True,
        )

        return response

    def form_invalid(self, form):
        print("========== BOOKING FORM ERRORS ==========")
        print(form.errors)
        print(form.non_field_errors())
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("booking_success")

def booking_success(request):
    return render(request, "bookings/success.html")


# ---------- USER DASHBOARD ----------
class UserDashboardView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "dashboard/index.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "meeting_room__branch", "office__branch"
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registrations = BusinessRegistration.objects.filter(user=self.request.user).order_by("-submitted_at")
        visits = VisitRequest.objects.filter(user=self.request.user).order_by("-submitted_at")
        bookings = context["bookings"]
        all_statuses = list(bookings.values_list("status", flat=True)) + list(registrations.values_list("status", flat=True)) + list(visits.values_list("status", flat=True))
        context.update({
            "registrations": registrations,
            "visits": visits,
            "total_requests": len(all_statuses),
            "pending_count": all_statuses.count("pending"),
            "approved_count": all_statuses.count("approved") + all_statuses.count("active"),
            "rejected_count": all_statuses.count("rejected"),
        })
        return context


# ---------- SIGNUP ----------
def signup(request):
    next_url = request.POST.get("next") or request.GET.get("next")

    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("business_register")

    form = UserCreationForm()
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("business_register")
    return render(
        request,
        "registration/signup.html",
        {"form": form, "next": next_url},
    )
