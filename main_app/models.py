from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, date
from django.utils.translation import gettext_lazy as _

# Create your models here.

# services
class Service(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    
# features
class Feature(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='features/', blank=True, null=True)


    def __str__(self):
        return self.title

    
# branches
class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    google_map = models.URLField(blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    opening_hours = models.CharField(max_length=100)
    image = models.ImageField(upload_to='branches/', blank=True, null=True)

    def __str__(self):
        return self.name

    
# meeting rooms
class MeetingRoom(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='meeting_rooms')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='meeting_rooms/', blank=True, null=True)
    capacity = models.PositiveIntegerField()
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=3)

    def __str__(self):
        return self.name

    def is_available(self, start_datetime, end_datetime):
        """Check if this room is free for the given datetime range."""
        # Note: status__in=['pending', 'approved'] automatically excludes cancelled bookings
        overlapping = self.bookings.filter(
            start_date=start_datetime.date(),
            start_time__lt=end_datetime.time(),
            end_time__gt=start_datetime.time(),
            status__in=['pending', 'approved']
        ).exists()
        return not overlapping

    def get_available_time_slots(self, date, interval_minutes=30):
        """
        Return a list of available time slots for a given date.
        Slots are returned as (start_time, end_time) tuples.
        """
        start_hour, end_hour = 9, 18
        slots = []
        time = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
        while time < end_time:
            slot_start = time.time()
            slot_end = (time + timedelta(minutes=interval_minutes)).time()
            if self.is_available(
                datetime.combine(date, slot_start),
                datetime.combine(date, slot_end)
            ):
                slots.append((slot_start, slot_end))
            time += timedelta(minutes=interval_minutes)
        return slots

    
# office
class Office(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='offices')
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='offices/', blank=True, null=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return self.name

    def is_available(self, start_date, end_date):
        """Check if this office is free for the given date range (inclusive)."""
        # Updated to __lte and __gte so single-day & short-term overlaps are accurately caught
        overlapping = self.bookings.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=['pending', 'approved']
        ).exists()
        return not overlapping

    def get_unavailable_dates(self, year, month):
        """Return a set of date objects for this month where the office is not available."""
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        
        bookings = self.bookings.filter(
            start_date__lte=end,
            end_date__gte=start,
            status__in=['pending', 'approved']
        )
        unavailable = set()
        for b in bookings:
            current = max(b.start_date, start)
            while current <= min(b.end_date, end):
                unavailable.add(current)
                current += timedelta(days=1)
        return unavailable

    def is_available_on_date(self, check_date):
        """Check if the office is free on a given date."""
        return not self.bookings.filter(
            start_date__lte=check_date,
            end_date__gte=check_date,
            status__in=['pending', 'approved']
        ).exists()

    def get_next_available_date(self, from_date):
        """Return the first date >= from_date where the office is available, or None."""
        max_lookahead = 90
        for i in range(max_lookahead + 1):
            check_date = from_date + timedelta(days=i)
            if self.is_available_on_date(check_date):
                return check_date
        return None

    
# booking
class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("cancelled", _("Cancelled")),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    meeting_room = models.ForeignKey(
        MeetingRoom,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bookings"
    )

    office = models.ForeignKey(
        Office,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bookings"
    )

    client_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    commercial_registration = models.CharField(max_length=100, blank=True)
    # Blank-compatible for historical production rows; BookingForm requires both
    # fields for every new client submission.
    business_type = models.CharField(max_length=200, blank=True)
    reason_for_booking = models.TextField(blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        editable=False
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if bool(self.meeting_room) == bool(self.office):
            raise ValidationError(
                "Choose either a meeting room or an office."
            )

        if self.meeting_room:
            if not self.start_time or not self.end_time:
                raise ValidationError(
                    "Start time and end time are required for meeting rooms."
                )

            if self.end_time <= self.start_time:
                raise ValidationError(
                    "End time must be after start time."
                )

        if self.office:
            # Auto-set end_date to start_date for single-day office bookings if omitted
            if not self.end_date:
                self.end_date = self.start_date

            # Updated validation: allow end_date == start_date (single day booking)
            if self.end_date < self.start_date:
                raise ValidationError(
                    "End date cannot be earlier than start date."
                )

    def save(self, *args, **kwargs):
        # Run model cleaning prior to save
        self.clean()

        if self.meeting_room and self.start_time and self.end_time:
            start = datetime.combine(self.start_date, self.start_time)
            end = datetime.combine(self.start_date, self.end_time)

            hours = Decimal(
                str((end - start).total_seconds() / 3600)
            )

            self.total_price = self.meeting_room.price_per_hour * hours

        elif self.office and self.end_date:
            # Calculate duration in days (inclusive)
            total_days = (self.end_date - self.start_date).days + 1

            if total_days < 30:
                # Prorated daily pricing for short-term/single-day bookings
                daily_rate = self.office.price_per_month / Decimal('30')
                self.total_price = (daily_rate * Decimal(total_days)).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )
            else:
                # Full monthly rate calculation
                months = (
                    (self.end_date.year - self.start_date.year) * 12
                    + self.end_date.month - self.start_date.month
                )
                if self.end_date.day > self.start_date.day:
                    months += 1

                months = max(1, months)
                self.total_price = self.office.price_per_month * Decimal(months)

        super().save(*args, **kwargs)

    def __str__(self):
        if self.meeting_room:
            return f"{self.client_name} - {self.meeting_room.name}"
        elif self.office:
            return f"{self.client_name} - {self.office.name}"
        return f"{self.client_name} - Booking #{self.id}"

    
# events
class Event(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    event_date = models.DateField()
    location = models.CharField(max_length=150)

    def __str__(self):
        return self.title

    
# gallery
class GalleryImage(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    
# FAQ
class FAQ(models.Model):
    question = models.CharField(max_length=250)
    answer = models.TextField()

    def __str__(self):
        return self.question

    
# contact
class Contact(models.Model):
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.phone

    
# visit requests
class VisitRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    
# business registrations
class BusinessRegistration(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending Review")),
        ("approved", _("Approved for CR Support")),
        ("in_progress", _("CR Support in Progress")),
        ("completed", _("Completed")),
        ("rejected", _("Rejected")),
    ]
    
    REQUEST_TYPE = [('new', 'New Registration'), ('renewal', 'CR Renewal')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_requests")
    company_name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    commercial_registration = models.CharField(max_length=100, blank=True, help_text="Required for renewals.")
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE, default='new')
    business_type = models.CharField(max_length=100)
    cpr_number = models.CharField(max_length=20, blank=True, null=True)
    
    cpr_document = models.FileField(upload_to='business_docs/cpr/', blank=True, null=True, help_text="Upload copy of CPR.")
    passport_document = models.FileField(upload_to='business_docs/passport/', blank=True, null=True, help_text="Upload copy of Passport.")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} ({self.get_request_type_display()})"


# referrals
class Referral(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    referred_company = models.CharField(max_length=150)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
