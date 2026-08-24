from django.urls import path
from . import views

urlpatterns = [

    # home
    path('', views.home, name='home'),

    # about
    path('about/', views.about, name='about'),

    # services
    path('services/', views.ServiceList.as_view(), name='services'),

    # rooms
    path('rooms/', views.MeetingRoomListView.as_view(), name='rooms'),
    path('rooms/<int:pk>/', views.MeetingRoomDetailView.as_view(), name='room_detail'),

    # offices
    path("offices/", views.OfficeListView.as_view(), name="offices"),
    path("offices/<int:pk>/", views.OfficeDetailView.as_view(), name="office_detail"),

    # gallery
    path('gallery/', views.GalleryListView.as_view(), name='gallery'),
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

    # business
    path('register/', views.BusinessRegistrationCreateView.as_view(), name='business_register'),
    path('register/success/', views.business_success, name='business_success'),

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
