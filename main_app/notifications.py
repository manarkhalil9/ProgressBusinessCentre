from django.conf import settings
from django.core.mail import send_mail


def send_client_email(subject, message, recipient):
    """Send a customer notification without making an admin save fail."""
    if not recipient:
        return
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True,
    )


def booking_resource(booking):
    return booking.meeting_room or booking.office


def booking_schedule(booking):
    if booking.meeting_room:
        return f"{booking.start_date} from {booking.start_time} to {booking.end_time}"
    return f"{booking.start_date} to {booking.end_date or booking.start_date}"


def notify_booking_status(booking):
    resource = booking_resource(booking)
    schedule = booking_schedule(booking)
    if booking.status == "approved":
        subject = "Booking Request Approved - Progress Business Centre"
        message = (
            f"Dear {booking.client_name},\n\n"
            f"Your booking request for {resource} has been approved.\n\n"
            f"Requested schedule: {schedule}\nStatus: Approved\n\n"
            "Our management team may contact you regarding final arrangements and pricing.\n\n"
            "Best regards,\nProgress Business Centre"
        )
    elif booking.status == "rejected":
        subject = "Booking Request Update - Progress Business Centre"
        message = (
            f"Dear {booking.client_name},\n\n"
            f"After reviewing your request for {resource}, we are unable to approve this booking at this time.\n\n"
            f"Requested schedule: {schedule}\nStatus: Rejected\n\n"
            "Please contact Progress Business Centre and our team will be pleased to discuss alternatives.\n\n"
            "Best regards,\nProgress Business Centre"
        )
    elif booking.status == "pending":
        subject = "Booking Request Under Review - Progress Business Centre"
        message = (
            f"Dear {booking.client_name},\n\nYour booking request for {resource} is pending review.\n\n"
            "Our team will contact you after reviewing the request.\n\nBest regards,\nProgress Business Centre"
        )
    else:
        return
    send_client_email(subject, message, booking.email)


def notify_registration_status(registration):
    recipient = registration.user.email
    name = registration.user.get_full_name() or registration.owner_name
    if registration.status == "active":
        subject = "Business Registration Approved - Progress Business Centre"
        body = f"Your application for {registration.company_name} has been approved and is now active."
    elif registration.status == "rejected":
        subject = "Business Registration Update - Progress Business Centre"
        body = f"After reviewing the application for {registration.company_name}, we are unable to approve it at this time. Please contact our team for assistance."
    elif registration.status == "pending":
        subject = "Business Registration Under Review - Progress Business Centre"
        body = f"Your application for {registration.company_name} is pending review."
    else:
        return
    send_client_email(subject, f"Dear {name},\n\n{body}\n\nBest regards,\nProgress Business Centre", recipient)


def notify_visit_status(visit):
    if visit.status == "approved":
        subject = "Visit Request Approved - Progress Business Centre"
        body = f"Your visit request for {visit.preferred_date} at {visit.preferred_time} has been approved."
    elif visit.status == "rejected":
        subject = "Visit Request Update - Progress Business Centre"
        body = "After reviewing your visit request, we are unable to approve the requested time. Please contact our team to arrange an alternative."
    elif visit.status == "pending":
        subject = "Visit Request Under Review - Progress Business Centre"
        body = "Your visit request is pending confirmation by our team."
    else:
        return
    send_client_email(subject, f"Dear {visit.full_name},\n\n{body}\n\nBest regards,\nProgress Business Centre", visit.email)
