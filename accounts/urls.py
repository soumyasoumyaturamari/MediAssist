from django.urls import path
from . import views


urlpatterns = [
    # Home
    path("", views.home, name="home"),

    # =========================
    # PATIENT URLs
    # =========================
    path("patient/register/", views.patient_register, name="patient_register"),
    path("patient/login/", views.patient_login, name="patient_login"),
    path("patient/dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("patient/profile/", views.patient_profile, name="patient_profile"),
    path("patient/medical-history/", views.medical_history, name="medical_history"),
    path("patient/appointments/", views.appointments, name="appointments"),
    path(
        "patient/book-appointment/",
        views.book_appointment,
        name="book_appointment"
    ),
    path(
        "patient/booked-slots/",
        views.get_booked_slots,
        name="booked_slots"
    ),
    path(
        "patient/appointments/cancel/<int:appointment_id>/",
        views.cancel_appointment,
        name="cancel_appointment"
    ),
    path("patient/ai-assistant/", views.ai_assistant, name="ai_assistant"),
    path("patient/logout/", views.patient_logout, name="patient_logout"),

    # =========================
    # DOCTOR URLs
    # =========================
    path("doctor/register/", views.doctor_register, name="doctor_register"),
    path("doctor/login/", views.doctor_login, name="doctor_login"),
    path("doctor/dashboard/", views.doctor_dashboard, name="doctor_dashboard"),
    path("doctor/profile/", views.doctor_profile, name="doctor_profile"),
    path("doctor/logout/", views.doctor_logout, name="doctor_logout"),

    # =========================
    # APPOINTMENT STATUS
    # =========================
    path(
        "doctor/appointment/<int:appointment_id>/<str:status>/",
        views.update_appointment_status,
        name="update_appointment_status"
    ),

    # =========================
    # MEDICAL RECORD
    # =========================
    path(
        "doctor/add-medical-record/<int:appointment_id>/",
        views.add_medical_record,
        name="add_medical_record"
    ),
    path("doctor/appointment/<int:appointment_id>/medical-records/", views.view_patient_medical_records, name="view_patient_medical_records"),
]
