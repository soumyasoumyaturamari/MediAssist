from django.contrib import admin
from django import forms
from django.contrib.auth.hashers import identify_hasher, make_password
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import models

from .models import Patient, MedicalRecord, Appointment, Doctor

admin.site.site_header = "Administration"
admin.site.site_title = "Administration"
admin.site.index_title = "Administration Dashboard"


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "age", "gender")
    search_fields = ("name", "email", "phone")
    change_list_template = "admin/accounts/patient/change_list.html"
    actions = ("add_patient_action",)

    @admin.action(description="Add Patient")
    def add_patient_action(self, request, queryset):
        return HttpResponseRedirect(reverse("admin:accounts_patient_add"))


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor_name", "visit_date")
    list_filter = ("visit_date",)
    search_fields = ("patient__name", "doctor_name", "diagnosis")

    def get_readonly_fields(self, request, obj=None):
        # Existing medical records are view-only; new records can still be added.
        return tuple(field.name for field in MedicalRecord._meta.fields) if obj else ()

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.method in ("GET", "HEAD", "OPTIONS")
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class AppointmentAdminForm(forms.ModelForm):
    # In the admin interface, staff may set an appointment to only these two
    # terminal states. The wider model choices remain available to the app's
    # patient/doctor workflows.
    status = forms.ChoiceField(
        choices=(("", "---------"), ("Completed", "Completed"), ("Cancelled", "Cancelled")),
        required=True,
        label="Status",
    )

    class Meta:
        model = Appointment
        fields = "__all__"
        widgets = {
            "appointment_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not silently change a legacy Pending/Approved/Rejected appointment
        # just by opening and saving the form. Require an explicit selection.
        if self.instance and self.instance.pk:
            current_status = self.instance.status
            self.initial["status"] = current_status if current_status in ("Completed", "Cancelled") else ""
        elif not self.is_bound:
            self.initial["status"] = ""


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    change_list_template = "admin/accounts/appointment/change_list.html"
    list_display = ("patient", "doctor_name", "appointment_date", "formatted_time", "status")
    list_filter = ("status", "appointment_date")
    search_fields = ("patient__name", "doctor_name")
    actions = ("add_appointment_action",)

    @admin.action(description="Add Appointment")
    def add_appointment_action(self, request, queryset):
        return HttpResponseRedirect(reverse("admin:accounts_appointment_add"))

    @admin.display(description="Appointment time", ordering="appointment_time")
    def formatted_time(self, obj):
        return obj.appointment_time.strftime("%H:%M") if obj.appointment_time else "—"


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    change_list_template = "admin/accounts/doctor/change_list.html"
    list_display = ("name", "email", "specialization", "is_available", "formatted_available_from", "formatted_available_to")
    search_fields = ("name", "email", "specialization")
    actions = ("add_doctor_action",)
    formfield_overrides = {
        models.TimeField: {"widget": forms.TimeInput(format="%H:%M", attrs={"type": "time"})}
    }

    @admin.action(description="Add Doctor")
    def add_doctor_action(self, request, queryset):
        return HttpResponseRedirect(reverse("admin:accounts_doctor_add"))

    @admin.display(description="Available from", ordering="available_from")
    def formatted_available_from(self, obj):
        return obj.available_from.strftime("%H:%M") if obj.available_from else "—"

    @admin.display(description="Available to", ordering="available_to")
    def formatted_available_to(self, obj):
        return obj.available_to.strftime("%H:%M") if obj.available_to else "—"

    def save_model(self, request, obj, form, change):
        # Admin-created doctors use the same hashed-password format as doctor registration.
        if obj.password:
            try:
                identify_hasher(obj.password)
            except (ValueError, TypeError):
                obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)
