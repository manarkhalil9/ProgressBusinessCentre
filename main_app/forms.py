from django import forms
from .models import BusinessRegistration, VisitRequest, Booking, MeetingRoom, Office, Referral
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _  # Import the translation tool


class BusinessRegistrationForm(forms.ModelForm):
    class Meta:
        model = BusinessRegistration
        fields = [
            "request_type", 
            "company_name",
            "owner_name",
            "commercial_registration",
            "business_type",
            "cpr_number",
            "cpr_document",
            "passport_document",
        ]
        labels = {
            "request_type": _("Request Type"),
            "company_name": _("Company Name"),
            "owner_name": _("Owner Name"),
            "commercial_registration": _("Commercial Registration"),
            "business_type": _("Business Type"),
            "cpr_number": _("CPR Number"),
            "cpr_document": _("Upload CPR"),
            "passport_document": _("Upload Passport"),
        }

class VisitRequestForm(forms.ModelForm):
    class Meta:
        model = VisitRequest
        fields = [
            'full_name',
            'email',
            'phone',
            'preferred_date',
            'preferred_time',
            'notes',
        ]

        labels = {
            "full_name": _("Full Name"),
            "email": _("Email Address"),
            "phone": _("Phone Number"),
            "preferred_date": _("Preferred Date"),
            "preferred_time": _("Preferred Time"),
            "notes": _("Notes"),
        }

        widgets = {
            'preferred_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
            'preferred_time': forms.TimeInput(
                attrs={'type': 'time'}
            ),
        }


class BookingForm(forms.ModelForm):
    business_type = forms.CharField(
        required=True,
        label=_("Business Type"),
        help_text=_("Describe your business or activity."),
        widget=forms.TextInput(attrs={
            "class": "booking-text-control",
            "placeholder": _("e.g. Consulting, Technology, Trading, Marketing"),
        }),
    )
    reason_for_booking = forms.CharField(
        required=True,
        label=_("Reason for Booking"),
        help_text=_("Tell us briefly how you plan to use the space."),
        widget=forms.Textarea(attrs={
            "class": "booking-text-control booking-reason-control",
            "rows": 4,
            "placeholder": _("Tell us briefly how you plan to use the space."),
        }),
    )

    class Meta:
        model = Booking
        fields = [
            "client_name",
            "phone",
            "email",
            "commercial_registration",
            "business_type",
            "reason_for_booking",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
        ]

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

        labels = {
            "client_name": _("Client Name"),
            "phone": _("Phone Number"),
            "email": _("Email Address"),
            "commercial_registration": _("Commercial Registration (CR)"),
            "start_date": _("Start Date"),
            "end_date": _("End Date"),
            "start_time": _("Start Time"),
            "end_time": _("End Time"),
        }

    def __init__(self, *args, resource=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource = resource

    def clean(self):
        cleaned_data = super().clean()
        resource = self.resource

        if not resource:
            raise ValidationError("No resource selected.")

        if isinstance(resource, MeetingRoom):
            start_date = cleaned_data.get('start_date')
            start_time = cleaned_data.get('start_time')
            end_time = cleaned_data.get('end_time')
            if start_date and start_time and end_time:
                start_dt = datetime.combine(start_date, start_time)
                end_dt = datetime.combine(start_date, end_time)
                if not resource.is_available(start_dt, end_dt):
                    self.add_error('start_time', _('This time slot is already booked.'))
                    self.add_error('end_time', _('Please choose an available slot.'))

        elif isinstance(resource, Office):
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')

            if start_date and not end_date:
                end_date = start_date
                cleaned_data['end_date'] = end_date
                self.instance.end_date = end_date

            if start_date and end_date:
                if end_date < start_date:
                    self.add_error('end_date', _('End date cannot be earlier than start date.'))
                elif not resource.is_available(start_date, end_date):
                    self.add_error('end_date', _('This date or date range is not fully available.'))

        return cleaned_data

    def get_available_slots(self, date):
        """Return available time slots for a meeting room on a given date."""
        if isinstance(self.resource, MeetingRoom):
            return self.resource.get_available_time_slots(date)
        return []
    
class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = ['full_name', 'email', 'phone', 'referred_company']
        labels = {
            'full_name': _('Full Name'),
            'email': _('Email Address'),
            'phone': _('Phone Number'),
            'referred_company': _('Referred Company Name'),
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': _('Enter full name')}),
            'email': forms.EmailInput(attrs={'placeholder': 'name@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+973 ...'}),
            'referred_company': forms.TextInput(attrs={'placeholder': _('Enter company name')}),
        }
