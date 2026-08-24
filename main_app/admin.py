from django.contrib import admin

from .models import (
    Service, Feature, Branch, MeetingRoom, Event, GalleryImage, FAQ, Contact,
    VisitRequest, BusinessRegistration, Referral, Office, Booking,
)


@admin.action(description="Approve selected requests")
def approve_bookings(modeladmin, request, queryset):
    for booking in queryset.exclude(status="approved"):
        booking.status = "approved"
        booking.save(update_fields=["status"])


@admin.action(description="Reject selected requests")
def reject_bookings(modeladmin, request, queryset):
    for booking in queryset.exclude(status="rejected"):
        booking.status = "rejected"
        booking.save(update_fields=["status"])


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("client_name", "resource", "resource_type", "business_type", "start_date", "status", "created_at")
    list_filter = ("status", "start_date", "created_at", "meeting_room__branch", "office__branch")
    search_fields = ("client_name", "email", "phone", "commercial_registration", "business_type", "reason_for_booking")
    readonly_fields = ("created_at", "total_price")
    actions = (approve_bookings, reject_bookings)

    @admin.display(description="Resource")
    def resource(self, obj):
        return obj.meeting_room or obj.office

    @admin.display(description="Type")
    def resource_type(self, obj):
        return "Meeting Room" if obj.meeting_room else "Office"


@admin.action(description="Mark selected applications active")
def activate_registrations(modeladmin, request, queryset):
    for registration in queryset.exclude(status="active"):
        registration.status = "active"
        registration.save(update_fields=["status"])


@admin.action(description="Reject selected applications")
def reject_registrations(modeladmin, request, queryset):
    for registration in queryset.exclude(status="rejected"):
        registration.status = "rejected"
        registration.save(update_fields=["status"])


@admin.register(BusinessRegistration)
class BusinessRegistrationAdmin(admin.ModelAdmin):
    list_display = ("company_name", "owner_name", "request_type", "business_type", "status", "submitted_at")
    list_filter = ("status", "request_type", "submitted_at")
    search_fields = ("company_name", "owner_name", "commercial_registration", "business_type", "user__email")
    readonly_fields = ("submitted_at",)
    actions = (activate_registrations, reject_registrations)


@admin.action(description="Approve selected visits")
def approve_visits(modeladmin, request, queryset):
    for visit in queryset.exclude(status="approved"):
        visit.status = "approved"
        visit.save(update_fields=["status"])


@admin.action(description="Reject selected visits")
def reject_visits(modeladmin, request, queryset):
    for visit in queryset.exclude(status="rejected"):
        visit.status = "rejected"
        visit.save(update_fields=["status"])


@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "preferred_date", "preferred_time", "status", "submitted_at")
    list_filter = ("status", "preferred_date", "submitted_at")
    search_fields = ("full_name", "email", "phone", "notes")
    readonly_fields = ("submitted_at",)
    actions = (approve_visits, reject_visits)


for model in (Service, Feature, Branch, MeetingRoom, Event, GalleryImage, FAQ, Contact, Referral, Office):
    admin.site.register(model)
