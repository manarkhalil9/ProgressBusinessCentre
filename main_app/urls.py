from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [

    # home
    path('', views.home, name='home'),

    # about
    path('about/', views.about, name='about'),

    # services
    path('services/', views.ServiceList.as_view(), name='services'),

    # spaces
    path('spaces/', views.SpacesListView.as_view(), name='spaces'),
    path('rooms/', RedirectView.as_view(pattern_name='spaces', permanent=True), name='rooms'),
    path('rooms/<int:pk>/', views.MeetingRoomDetailView.as_view(), name='room_detail'),

    # legacy office listing redirect and current detail route
    path("offices/", RedirectView.as_view(pattern_name='spaces', permanent=True), name="offices"),
    path("offices/<int:pk>/", views.OfficeDetailView.as_view(), name="office_detail"),

    # legacy public gallery redirect; images are now presented on the homepage
    path('gallery/', RedirectView.as_view(pattern_name='home', permanent=True), name='gallery'),
    path('gallery/<int:pk>/', views.GalleryDetailView.as_view(), name='gallery_detail'),

    # faq
    path('faqs/', views.FAQListView.as_view(), name='faqs'),

    # contact
    path('contact/', views.ContactView.as_view(), name='contact'),

    # visit
    path('visit/', views.VisitCreateView.as_view(), name='visit'),
    path('visit/success/', views.visit_success, name='visit_success'),

    # referral
    path('referral/', views.ReferralCreateView.as_view(), name='referral_create'),
    path('referral/success/', views.referral_success, name='referral_success'),

    # CR support
    path('cr-support/', views.BusinessRegistrationCreateView.as_view(), name='cr_support'),
    path('cr-support/success/', views.cr_support_success, name='cr_support_success'),
    path('register/', RedirectView.as_view(pattern_name='cr_support', permanent=True), name='business_register'),
    path('register/success/', RedirectView.as_view(pattern_name='cr_support_success', permanent=True), name='business_success'),

    # bookings
    path("book/<str:resource_type>/<int:pk>/", views.BookingCreateView.as_view(), name="book"),
    path("book/success/", views.booking_success, name="booking_success"),

    # client portal
    path("dashboard/", views.UserDashboardView.as_view(), name="dashboard"),
    
    # payment page
    # path("booking/<int:pk>/payment/", views.booking_payment, name="booking_payment"),

    # auth
    path('accounts/signup/', views.signup, name='signup'),
]
