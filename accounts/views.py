from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .models import Patient, MedicalRecord, Appointment, Doctor
from ollama import chat


def home(request):
    return render(request, "accounts/home.html")


def patient_register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        age = request.POST.get("age")
        gender = request.POST.get("gender")
        address = request.POST.get("address")
        password = request.POST.get("password")

        if Patient.objects.filter(email=email).exists():
            return render(
                request,
                "accounts/patient_register.html",
                {
                    "error": "An account with this email already exists. Please login."
                }
            )

        Patient.objects.create(
            name=name,
            email=email,
            phone=phone,
            age=age,
            gender=gender,
            address=address,
            password=make_password(password),
        )

        return redirect("patient_login")

    return render(request, "accounts/patient_register.html")


def patient_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            patient = Patient.objects.get(email=email)

            if check_password(password, patient.password):
                request.session["patient_id"] = patient.id
                request.session["patient_name"] = patient.name
                return redirect("patient_dashboard")

            return render(
                request,
                "accounts/patient_login.html",
                {"error": "Invalid email or password"}
            )

        except Patient.DoesNotExist:
            return render(
                request,
                "accounts/patient_login.html",
                {"error": "Invalid email or password"}
            )

    return render(request, "accounts/patient_login.html")


def patient_dashboard(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(
            id=request.session["patient_id"]
        )
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    all_appointments = Appointment.objects.filter(
        patient=patient
    )

    total_appointments = all_appointments.count()

    pending_appointments = all_appointments.filter(
        status="Pending"
    ).count()

    approved_appointments = all_appointments.filter(
        status="Approved"
    ).count()

    completed_appointments = all_appointments.filter(
        status="Completed"
    ).count()

    cancelled_appointments = all_appointments.filter(
        status="Cancelled"
    ).count()

    return render(
        request,
        "accounts/patient_dashboard.html",
        {
            "patient": patient,
            "total_appointments": total_appointments,
            "pending_appointments": pending_appointments,
            "approved_appointments": approved_appointments,
            "completed_appointments": completed_appointments,
            "cancelled_appointments": cancelled_appointments,
        }
    )


def patient_profile(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(id=request.session["patient_id"])
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    if request.method == "POST":
        patient.name = request.POST.get("name")
        patient.email = request.POST.get("email")
        patient.phone = request.POST.get("phone")
        patient.age = request.POST.get("age")
        patient.gender = request.POST.get("gender")
        patient.address = request.POST.get("address")
        patient.save()

        request.session["patient_name"] = patient.name

        return render(
            request,
            "accounts/patient_profile.html",
            {
                "patient": patient,
                "success": "Profile updated successfully!"
            }
        )

    return render(
        request,
        "accounts/patient_profile.html",
        {"patient": patient}
    )


def medical_history(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(id=request.session["patient_id"])
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    records = patient.medical_records.all().order_by("-visit_date")

    return render(
        request,
        "accounts/medical_history.html",
        {
            "patient": patient,
            "records": records
        }
    )


def appointments(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(id=request.session["patient_id"])
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    appointment_list = Appointment.objects.filter(
        patient=patient
    ).order_by(
        "-appointment_date",
        "-appointment_time"
    )

    return render(
        request,
        "accounts/appointments.html",
        {
            "patient": patient,
            "appointments": appointment_list
        }
    )


def book_appointment(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(
            id=request.session["patient_id"]
        )
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    doctors = Doctor.objects.filter(
        is_available=True
    ).order_by("name")

    context = {
        "patient": patient,
        "doctors": doctors,
        "today": timezone.localdate().isoformat(),
    }

    if request.method == "POST":
        doctor_id = request.POST.get("doctor_id")
        appointment_date_value = request.POST.get("appointment_date")
        appointment_time_value = request.POST.get("appointment_time")
        reason = request.POST.get("reason", "").strip()

        context.update({
            "selected_doctor_id": doctor_id,
            "appointment_date_value": appointment_date_value,
            "appointment_time_value": appointment_time_value,
            "reason": reason,
        })

        if not doctor_id or not appointment_date_value or not appointment_time_value or not reason:
            context["error"] = (
                "Please select a doctor, date, time, and enter the reason."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        try:
            appointment_date = datetime.strptime(
                appointment_date_value,
                "%Y-%m-%d"
            ).date()

            appointment_time = datetime.strptime(
                appointment_time_value,
                "%H:%M"
            ).time()

        except (TypeError, ValueError):
            context["error"] = (
                "Please select a valid appointment date and time."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        try:
            selected_doctor = Doctor.objects.get(
                id=doctor_id,
                is_available=True
            )
        except Doctor.DoesNotExist:
            context["error"] = (
                "This doctor is currently unavailable. "
                "Please select another doctor."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        if not selected_doctor.available_from or not selected_doctor.available_to:
            context["error"] = (
                "This doctor has not set working hours yet. "
                "Please select another doctor."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        if selected_doctor.available_from >= selected_doctor.available_to:
            context["error"] = (
                "This doctor's working hours are not configured correctly."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        now = timezone.localtime()
        today = now.date()
        current_time = now.time().replace(second=0, microsecond=0)

        if appointment_date < today:
            context["error"] = (
                "You cannot book an appointment for a past date."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        if appointment_date == today and appointment_time <= current_time:
            context["error"] = (
                "You cannot select a time that has already passed. "
                "Please select a future time."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        duration = selected_doctor.appointment_duration or 30

        work_start = datetime.combine(
            appointment_date,
            selected_doctor.available_from
        )
        work_end = datetime.combine(
            appointment_date,
            selected_doctor.available_to
        )
        selected_start = datetime.combine(
            appointment_date,
            appointment_time
        )

        if selected_start < work_start:
            context["error"] = (
                f"This doctor is available from "
                f"{selected_doctor.available_from.strftime('%I:%M %p')}."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        if selected_start + timedelta(minutes=duration) > work_end:
            context["error"] = (
                f"The appointment must finish by "
                f"{selected_doctor.available_to.strftime('%I:%M %p')}."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        minutes_from_start = int(
            (selected_start - work_start).total_seconds() // 60
        )

        if minutes_from_start % duration != 0:
            context["error"] = (
                f"Please select a valid {duration}-minute appointment slot."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        duplicate_appointment = Appointment.objects.filter(
            doctor=selected_doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).exclude(
            status__in=["Rejected", "Cancelled"]
        ).exists()

        if duplicate_appointment:
            context["error"] = (
                "This time slot is already booked. "
                "Please select another available time."
            )
            return render(
                request,
                "accounts/book_appointment.html",
                context
            )

        Appointment.objects.create(
            patient=patient,
            doctor=selected_doctor,
            doctor_name=(
                f"Dr. {selected_doctor.name} - "
                f"{selected_doctor.specialization}"
            ),
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status="Pending"
        )

        messages.success(
            request,
            "Appointment booked successfully and is waiting for doctor approval."
        )
        return redirect("appointments")

    return render(
        request,
        "accounts/book_appointment.html",
        context
    )


def get_booked_slots(request):
    if "patient_id" not in request.session:
        return JsonResponse(
            {"error": "Authentication required."},
            status=403
        )

    doctor_id = request.GET.get("doctor_id")
    appointment_date_value = request.GET.get("appointment_date")

    if not doctor_id or not appointment_date_value:
        return JsonResponse(
            {"error": "Doctor and appointment date are required."},
            status=400
        )

    try:
        appointment_date = datetime.strptime(
            appointment_date_value,
            "%Y-%m-%d"
        ).date()

        doctor = Doctor.objects.get(
            id=doctor_id,
            is_available=True
        )

    except (ValueError, Doctor.DoesNotExist):
        return JsonResponse(
            {"error": "Invalid doctor or appointment date."},
            status=400
        )

    booked_slots = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=appointment_date
    ).exclude(
        status__in=["Rejected", "Cancelled"]
    ).values_list(
        "appointment_time",
        flat=True
    )

    booked_times = [
        booked_time.strftime("%H:%M")
        for booked_time in booked_slots
    ]

    return JsonResponse({
        "booked_times": booked_times
    })

def ai_assistant(request):
    if "patient_id" not in request.session:
        return redirect("patient_login")

    try:
        patient = Patient.objects.get(id=request.session["patient_id"])
    except Patient.DoesNotExist:
        request.session.flush()
        return redirect("patient_login")

    response = None
    symptoms = ""
    error = None

    if request.method == "POST":
        symptoms = request.POST.get("symptoms", "").strip()

        if not symptoms:
            error = "Please describe your symptoms."
        else:
            try:
                ai_response = chat(
                    model="llama3.2:1b",
                    messages=[
                        {
                            "role": "system",
                            "content": """
You are MediAssist AI Health Assistant.

Your role is to provide general health information based on
symptoms described by the user.

IMPORTANT SAFETY RULES:
1. Do not claim to provide a definite medical diagnosis.
2. Do not prescribe medicines or provide medication dosages.
3. Clearly explain that the response is general health information.
4. Recommend consulting a qualified doctor when appropriate.
5. If symptoms appear serious, recommend urgent medical evaluation.
6. If there are emergency warning signs such as severe difficulty
   breathing, severe chest pain, unconsciousness, or severe bleeding,
   clearly advise immediate emergency medical help.
7. Keep the response simple and easy to understand.

Structure your response with these headings:
Possible considerations:
General self-care:
When to see a doctor:
Emergency warning signs:
"""
                        },
                        {
                            "role": "user",
                            "content": symptoms
                        }
                    ]
                )

                response = ai_response.message.content

            except Exception as e:
                print("OLLAMA ERROR:", repr(e))

                error = (
                    "Sorry, the AI Health Assistant is temporarily "
                    "unavailable. Please make sure Ollama is running."
                )

    return render(
        request,
        "accounts/ai_assistant.html",
        {
            "patient": patient,
            "response": response,
            "symptoms": symptoms,
            "error": error
        }
    )


def patient_logout(request):
    request.session.flush()
    return redirect("home")


# =========================
# DOCTOR FEATURES
# =========================

def doctor_register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        specialization = request.POST.get("specialization")
        password = request.POST.get("password")

        if Doctor.objects.filter(email=email).exists():
            return render(
                request,
                "accounts/doctor_register.html",
                {
                    "error": "An account with this email already exists. Please login."
                }
            )

        Doctor.objects.create(
            name=name,
            email=email,
            phone=phone,
            specialization=specialization,
            password=make_password(password),
            is_available=True
        )

        return redirect("doctor_login")

    return render(request, "accounts/doctor_register.html")


def doctor_login(request):
    # Older project versions could queue this message when a stale URL was
    # opened. Remove only that obsolete message while preserving other notices.
    pending_messages = list(messages.get_messages(request))
    for pending_message in pending_messages:
        if str(pending_message) != "Invalid appointment status.":
            messages.add_message(
                request,
                pending_message.level,
                str(pending_message),
                extra_tags=pending_message.extra_tags,
            )

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            doctor = Doctor.objects.get(email=email)

            if check_password(password, doctor.password):
                request.session["doctor_id"] = doctor.id
                request.session["doctor_name"] = doctor.name
                return redirect("doctor_dashboard")

            messages.error(request, "Invalid email or password!")

        except Doctor.DoesNotExist:
            messages.error(request, "Doctor account not found!")

    return render(request, "accounts/doctor_login.html")


def doctor_dashboard(request):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        request.session.flush()
        return redirect("doctor_login")

    all_appointments = Appointment.objects.filter(
        doctor=doctor
    ).order_by("-appointment_date", "-appointment_time")

    active_appointments = all_appointments.exclude(
        status__in=["Cancelled", "Rejected"]
    )

    total_appointments = active_appointments.count()

    pending_appointments = all_appointments.filter(
        status="Pending"
    ).count()

    approved_appointments = all_appointments.filter(
        status="Approved"
    ).count()

    completed_appointments = all_appointments.filter(
        status="Completed"
    ).count()

    cancelled_appointments = all_appointments.filter(
        status="Cancelled"
    ).count()

    selected_status = request.GET.get("status", "All")
    search_query = request.GET.get("search", "").strip()

    appointments = all_appointments

    if selected_status != "All":
        appointments = appointments.filter(
            status=selected_status
        )

    if search_query:
        appointments = appointments.filter(
            patient__name__icontains=search_query
        )

    return render(
        request,
        "accounts/doctor_dashboard.html",
        {
            "doctor": doctor,
            "appointments": appointments,
            "total_appointments": total_appointments,
            "pending_appointments": pending_appointments,
            "approved_appointments": approved_appointments,
            "completed_appointments": completed_appointments,
            "cancelled_appointments": cancelled_appointments,
            "selected_status": selected_status,
            "search_query": search_query,
        }
    )


# =========================
# DOCTOR PROFILE
# =========================

def doctor_profile(request):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        request.session.flush()
        return redirect("doctor_login")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        available_from_value = request.POST.get("available_from", "").strip()
        available_to_value = request.POST.get("available_to", "").strip()
        appointment_duration_value = request.POST.get(
            "appointment_duration",
            "30"
        ).strip()
        is_available = request.POST.get("is_available") == "on"

        if not all([
            name,
            email,
            phone,
            specialization,
            available_from_value,
            available_to_value,
            appointment_duration_value
        ]):
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Please fill in all required profile and schedule fields."
                }
            )

        try:
            available_from = datetime.strptime(
                available_from_value,
                "%H:%M"
            ).time()
            available_to = datetime.strptime(
                available_to_value,
                "%H:%M"
            ).time()
            appointment_duration = int(appointment_duration_value)
        except (TypeError, ValueError):
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Please enter valid working hours and appointment duration."
                }
            )

        if available_from >= available_to:
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Available from time must be earlier than available to time."
                }
            )

        if appointment_duration <= 0 or appointment_duration > 240:
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Appointment duration must be between 1 and 240 minutes."
                }
            )

        total_minutes = (
            datetime.combine(datetime.today(), available_to)
            - datetime.combine(datetime.today(), available_from)
        ).total_seconds() / 60

        if appointment_duration > total_minutes:
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Appointment duration cannot be longer than total working hours."
                }
            )

        if Doctor.objects.filter(email=email).exclude(
            id=doctor.id
        ).exists():
            return render(
                request,
                "accounts/doctor_profile.html",
                {
                    "doctor": doctor,
                    "error": "Another doctor account already uses this email."
                }
            )

        doctor.name = name
        doctor.email = email
        doctor.phone = phone
        doctor.specialization = specialization
        doctor.available_from = available_from
        doctor.available_to = available_to
        doctor.appointment_duration = appointment_duration
        doctor.is_available = is_available
        doctor.save()

        request.session["doctor_name"] = doctor.name

        return render(
            request,
            "accounts/doctor_profile.html",
            {
                "doctor": doctor,
                "success": "Profile, availability, and appointment schedule updated successfully!"
            }
        )

    return render(
        request,
        "accounts/doctor_profile.html",
        {"doctor": doctor}
    )

def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


def update_appointment_status(request, appointment_id, status):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    # This endpoint is only for the doctor's Approve/Reject actions.
    # Ignore stale bookmarks or old dashboard links using other status values;
    # do not leave a repeated error message in the session/admin message queue.
    if status not in ["Approved", "Rejected"]:
        return redirect("doctor_dashboard")

    try:
        appointment = Appointment.objects.get(
            id=appointment_id,
            doctor_id=doctor_id
        )

        if appointment.status == "Cancelled":
            messages.error(
                request,
                "This appointment has been cancelled by the patient and cannot be updated."
            )
            return redirect("doctor_dashboard")

        if appointment.status == "Completed":
            messages.error(
                request,
                "A completed appointment cannot be updated."
            )
            return redirect("doctor_dashboard")

        if appointment.status == "Rejected":
            messages.error(
                request,
                "A rejected appointment cannot be updated."
            )
            return redirect("doctor_dashboard")

        if status == "Approved":
            if appointment.status != "Pending":
                messages.error(
                    request,
                    "Only pending appointments can be approved."
                )
                return redirect("doctor_dashboard")

            appointment.status = "Approved"

        elif status == "Rejected":
            if appointment.status != "Pending":
                messages.error(
                    request,
                    "Only pending appointments can be rejected."
                )
                return redirect("doctor_dashboard")

            appointment.status = "Rejected"

        appointment.save()

        messages.success(
            request,
            f"Appointment {appointment.status.lower()} successfully."
        )

    except Appointment.DoesNotExist:
        messages.error(
            request,
            "Appointment not found or access denied."
        )

    return redirect("doctor_dashboard")


def add_medical_record(request, appointment_id):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    try:
        doctor = Doctor.objects.get(id=doctor_id)

        appointment = Appointment.objects.get(
            id=appointment_id,
            doctor=doctor,
            status="Approved"
        )

    except (Doctor.DoesNotExist, Appointment.DoesNotExist):
        messages.error(
            request,
            "Appointment not found or access denied."
        )
        return redirect("doctor_dashboard")

    if request.method == "POST":
        visit_date = request.POST.get("visit_date")
        symptoms = request.POST.get("symptoms")
        diagnosis = request.POST.get("diagnosis")
        prescription = request.POST.get("prescription")
        doctor_notes = request.POST.get("doctor_notes")

        MedicalRecord.objects.create(
            patient=appointment.patient,
            doctor_name=f"Dr. {doctor.name}",
            visit_date=visit_date,
            symptoms=symptoms,
            diagnosis=diagnosis,
            prescription=prescription,
            doctor_notes=doctor_notes
        )

        appointment.status = "Completed"
        appointment.save()

        messages.success(
            request,
            "Medical record added successfully."
        )

        return redirect("doctor_dashboard")

    return render(
        request,
        "accounts/add_medical_record.html",
        {
            "appointment": appointment,
            "doctor": doctor
        }
    )


def cancel_appointment(request, appointment_id):
    patient_id = request.session.get("patient_id")

    if not patient_id:
        return redirect("patient_login")

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("appointments")

    try:
        appointment = Appointment.objects.get(
            id=appointment_id,
            patient_id=patient_id
        )

        if appointment.status in ["Pending", "Approved"]:
            appointment.status = "Cancelled"
            appointment.save()

            messages.success(
                request,
                "Appointment cancelled successfully."
            )
        else:
            messages.error(
                request,
                "Only pending or approved appointments can be cancelled."
            )

    except Appointment.DoesNotExist:
        messages.error(
            request,
            "Appointment not found."
        )

    return redirect("appointments")


def view_patient_medical_records(request, appointment_id):
    """Allow the logged-in doctor to view medical records for a completed appointment."""
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        request.session.flush()
        messages.error(request, "Please log in again to view medical records.")
        return redirect("doctor_login")

    try:
        appointment = Appointment.objects.select_related(
            "patient", "doctor"
        ).get(id=appointment_id)
    except Appointment.DoesNotExist:
        messages.error(request, "The requested appointment could not be found.")
        return redirect("doctor_dashboard")

    # The current Appointment model normally stores the assigned Doctor
    # in appointment.doctor. Older appointments may have only doctor_name,
    # so support both forms.
    is_assigned_doctor = (
        appointment.doctor_id is not None
        and appointment.doctor_id == doctor.id
    )

    def normalize_name(value):
        value = " ".join((value or "").casefold().split())
        if value.startswith("dr. "):
            value = value[4:]
        return value

    assigned_name = normalize_name(appointment.doctor_name)
    logged_in_doctor_name = normalize_name(doctor.name)

    is_legacy_assignment = (
        appointment.doctor_id is None
        and bool(logged_in_doctor_name)
        and (
            assigned_name == logged_in_doctor_name
            or assigned_name.startswith(logged_in_doctor_name + " -")
            or assigned_name.startswith(logged_in_doctor_name + " ")
        )
    )

    if not (is_assigned_doctor or is_legacy_assignment):
        messages.error(
            request,
            "This appointment is not assigned to your doctor account."
        )
        return redirect("doctor_dashboard")

    if appointment.status != "Completed":
        messages.error(
            request,
            "Medical records can be viewed only for completed appointments."
        )
        return redirect("doctor_dashboard")

    records = appointment.patient.medical_records.all().order_by(
        "-visit_date",
        "-created_at"
    )

    return render(
        request,
        "accounts/doctor_medical_records.html",
        {
            "doctor": doctor,
            "appointment": appointment,
            "patient": appointment.patient,
            "records": records,
        }
    )
