from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from dotenv import dotenv_values
import json
import os
import re
import time
import urllib.error
import urllib.request

from datetime import date, timedelta

from .models import DEPARTMENT_CHOICES, District, Hospital, Doctor, Patient, Appointment, Treatment, Availability
from .utils import validate_profile_photo
from .payments import (
    PaymentError, configured_appointment_fee, create_appointment_order,
    razorpay_test_client, verify_appointment_payment,
)

from accounts.decorators import admin_required
from accounts.decorators import patient_required, doctor_required


def _posted_hospital(request):
    try:
        hospital_id = int(request.POST.get("hospital", ""))
    except (TypeError, ValueError):
        return None
    return Hospital.objects.filter(pk=hospital_id).first()

# ADMIN PAGES

@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    total_doctors = Doctor.objects.count()
    total_patients = Patient.objects.count()
    total_hospitals = Hospital.objects.filter(is_active=True).count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(date=today).select_related(
        "doctor__user", "patient__user"
    ).order_by("time")
    upcoming_appointments = Appointment.objects.filter(
        date__gt=today
    ).exclude(status="Cancelled").select_related(
        "doctor__user", "patient__user"
    ).order_by("date", "time")[:5]
    status_counts = {
        status: Appointment.objects.filter(status=status).count()
        for status, _label in Appointment.STATUS_CHOICES
    }

    return render(request, "admin/dashboard.html", {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_hospitals": total_hospitals,
        "total_appointments": total_appointments,
        "today": today,
        "today_appointments": today_appointments,
        "upcoming_appointments": upcoming_appointments,
        "status_counts": status_counts,
        "admin_display": request.user.get_full_name() or request.user.get_username(),
    })



#DOCTORS
@admin_required
def admin_doctors(request):
    doctors = Doctor.objects.all()
    return render(request, "admin/doctors.html", {"doctors": doctors})

@admin_required
@require_POST
def admin_doctors_delete(request, id):
    doctor = get_object_or_404(Doctor, id=id)
    user = doctor.user  # linked user

    doctor.delete()     # delete doctor record
    user.delete()       # delete user account

    messages.success(request, "Doctor deleted successfully!")
    return redirect("admin_doctors")

@admin_required
def admin_doctors_form(request):
    """Add doctor"""
    if request.method == "POST":
        fname = request.POST["fname"]
        lname = request.POST["lname"]
        specialization = request.POST["specialization"]
        dept = request.POST["department"]
        exp = request.POST["experience"]
        language = request.POST["language"]
        location = request.POST["location"]

        user = User.objects.create(
            username=fname.lower(),
            first_name=fname,
            last_name=lname
        )

        Doctor.objects.create(
            user=user,
            hospital=_posted_hospital(request),
            specialization=specialization,
            experience=exp,
            department=dept,
            language=language,
            location=location
        )

        messages.success(request, "Doctor added successfully!")
        return redirect("admin_doctors")

    return render(request, "admin/doctors_form.html", {
        "departments": DEPARTMENT_CHOICES,
        "hospitals": Hospital.objects.filter(is_active=True).select_related("district"),
    })


# PATIENTS
@admin_required
def admin_patients(request):
    patients = Patient.objects.all()
    return render(request, "admin/patients.html", {"patients": patients})

@admin_required
def admin_add_patient(request):
    if request.method == "POST":
        fname = request.POST["fname"]
        lname = request.POST["lname"]
        age = request.POST["age"]
        gender = request.POST["gender"]
        address = request.POST["address"]
        phone = request.POST["phone"]

        user = User.objects.create(
            username=fname.lower(),
            first_name=fname,
            last_name=lname
        )

        Patient.objects.create(
            user=user,
            age=age,
            gender=gender,
            address=address,
            phone_number=phone
        )

        messages.success(request, "Patient added successfully!")
        return redirect("admin_patients")

    return render(request, "admin/add_patient.html")


# APPOINTMENTS
@admin_required
def admin_appointments(request):
    appointments = Appointment.objects.select_related(
        "doctor__user", "patient__user"
    ).order_by("-date", "-time")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    department = request.GET.get("department", "")
    appointment_date = request.GET.get("date", "")

    if query:
        filters = Q(patient__user__first_name__icontains=query) | Q(
            patient__user__last_name__icontains=query
        ) | Q(doctor__user__first_name__icontains=query) | Q(
            doctor__user__last_name__icontains=query
        )
        if query.isdigit():
            filters |= Q(pk=int(query))
        appointments = appointments.filter(filters)
    if status in dict(Appointment.STATUS_CHOICES):
        appointments = appointments.filter(status=status)
    if department:
        appointments = appointments.filter(doctor__department=department)
    if appointment_date:
        appointments = appointments.filter(date=appointment_date)

    return render(request, "admin/appointments.html", {
        "appointments": appointments,
        "query": query,
        "selected_status": status,
        "selected_department": department,
        "selected_date": appointment_date,
        "statuses": Appointment.STATUS_CHOICES,
        "departments": Doctor.objects.order_by("department").values_list(
            "department", flat=True
        ).distinct(),
    })
@admin_required
def admin_edit_appointment(request, id):
    appointment = get_object_or_404(Appointment, id=id)

    if request.method == "POST":
        appointment.date = request.POST["date"]
        appointment.time = request.POST["time"]
        appointment.status = request.POST["status"]
        appointment.save()

        messages.success(request, "Appointment updated successfully!")
        return redirect("admin_appointments")

    return render(request, "admin/edit_appointment.html", {
        "appointment": appointment
    })

@admin_required
def admin_edit_patient(request, id):
    patient = get_object_or_404(Patient, id=id)

    if request.method == "POST":
        patient.user.first_name = request.POST["fname"]
        patient.user.last_name = request.POST["lname"]
        patient.age = request.POST["age"]
        patient.gender = request.POST["gender"]
        patient.phone_number = request.POST["phone"]
        patient.address = request.POST["address"]

        patient.user.save()
        patient.save()

        messages.success(request, "Patient updated successfully!")
        return redirect("admin_patients")

    return render(request, "admin/edit_patient.html", {"patient": patient})

@admin_required
@require_POST
def admin_delete_patient(request, id):
    patient = get_object_or_404(Patient, id=id)
    user = patient.user
    patient.delete()
    user.delete()
    messages.success(request, "Patient deleted successfully!")
    return redirect("admin_patients")

@admin_required
def admin_doctors_edit(request, id):
    doctor = get_object_or_404(Doctor, id=id)

    if request.method == "POST":
        doctor.user.first_name = request.POST["fname"]
        doctor.user.last_name = request.POST["lname"]
        doctor.hospital = _posted_hospital(request)
        doctor.specialization = request.POST["specialization"]
        doctor.department = request.POST["department"]
        doctor.experience = request.POST["experience"]
        doctor.language = request.POST["language"]
        doctor.location = request.POST["location"]

        doctor.user.save()
        doctor.save()

        messages.success(request, "Doctor updated successfully!")
        return redirect("admin_doctors")

    return render(request, "admin/edit_doctor.html", {
        "doctor": doctor,
        "departments": DEPARTMENT_CHOICES,
        "hospitals": Hospital.objects.filter(is_active=True).select_related("district"),
    })


@admin_required
@require_POST
def admin_delete_appointment(request, id):
    appointment = get_object_or_404(Appointment, id=id)
    appointment.delete()

    messages.success(request, "Appointment deleted successfully!")
    return redirect("admin_appointments")


# ---------- SEARCH ----------
@admin_required
def admin_search(request):
    query = request.GET.get("q", "")

    doctors = Doctor.objects.filter(user__first_name__icontains=query)
    patients = Patient.objects.filter(user__first_name__icontains=query)

    return render(request, "admin/search.html", {
        "doctors": doctors,
        "patients": patients,
        "query": query,
    })



# DOCTOR PAGES


@doctor_required
def doctor_dashboard(request):
    doctor = Doctor.objects.get(user=request.user)
    today = date.today()

    today_appointments = Appointment.objects.filter(
        doctor=doctor, date=today, payment_status__in=("Paid", "Legacy")
    ).order_by("time")

    today_count = today_appointments.count()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_count = Appointment.objects.filter(
        doctor=doctor,
        payment_status__in=("Paid", "Legacy"),
        date__range=[week_start, week_end]
    ).count()

    working_hours = today_count * 2

    return render(request, "doctor/dashboard.html", {
        "doctor": doctor,
        "today_appointments": today_appointments,
        "today_count": today_count,
        "week_count": week_count,
        "working_hours": working_hours
    })


@doctor_required
def doctor_appointments(request):
    doctor = Doctor.objects.get(user=request.user)
    today = date.today()

    appointments = Appointment.objects.filter(
        doctor=doctor,
        payment_status__in=("Paid", "Legacy"),
        date__gte=today,
    ).select_related("patient__user").order_by("date", "time")

    return render(request, "doctor/appointments.html", {"appointments": appointments})


@doctor_required
def doctor_patient_history(request):
    doctor = Doctor.objects.get(user=request.user)
    records = Treatment.objects.filter(appointment__doctor=doctor)

    return render(request, "doctor/patient_history.html", {"records": records})


@doctor_required
def doctor_treatment_form(request, appointment_id):
    doctor = Doctor.objects.get(user=request.user)
    appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)

    if request.method == "POST":
        diagnosis = request.POST.get("diagnosis")
        prescription = request.POST.get("prescription")
        notes = request.POST.get("notes")

        # Save treatment on existing appointment
        Treatment.objects.create(
            appointment=appointment,
            diagnosis=diagnosis,
            prescription=prescription,
            notes=notes
        )

        # Mark appointment completed
        appointment.status = "Completed"
        appointment.save()

        messages.success(request, "Treatment added successfully!")
        return redirect("doctor_patient_history")

    return render(request, "doctor/treatment_form.html", {"appointment": appointment})



@doctor_required
def doctor_availability(request):
    doctor = Doctor.objects.get(user=request.user)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if request.method == "POST":
        for day in days:
            value = request.POST.get(day)
            obj, created = Availability.objects.get_or_create(doctor=doctor, day=day)
            obj.time_range = value
            obj.save()

        messages.success(request, "Availability updated!")
        return redirect("doctor_availability")

    availability = {a.day: a.time_range for a in Availability.objects.filter(doctor=doctor)}

    return render(request, "doctor/availability.html", {
        "availability": availability,
        "days": days
    })

@doctor_required
def doctor_profile(request):
    doctor = Doctor.objects.get(user=request.user)

    return render(request, "doctor/profile.html", {
        "doctor": doctor
    })

@doctor_required
def doctor_profile_edit(request):
    doctor = Doctor.objects.get(user=request.user)

    if request.method == "POST":
        uploaded_photo = request.FILES.get("profile_photo")
        photo_error = validate_profile_photo(uploaded_photo)
        if photo_error:
            messages.error(request, photo_error)
            return render(request, "doctor/profile_edit.html", {
                "doctor": doctor,
                "departments": DEPARTMENT_CHOICES,
            })

        previous_photo = doctor.profile_photo.name
        doctor.user.first_name = request.POST["fname"]
        doctor.user.last_name = request.POST["lname"]
        doctor.specialization = request.POST["specialization"]
        doctor.department = request.POST["department"]
        doctor.experience = request.POST["experience"]
        doctor.language = request.POST["language"]
        doctor.location = request.POST["location"]
        if uploaded_photo:
            doctor.profile_photo = uploaded_photo

        doctor.user.save()
        doctor.save()
        if uploaded_photo and previous_photo:
            doctor.profile_photo.storage.delete(previous_photo)

        messages.success(request, "Profile updated successfully!")
        return redirect("doctor_profile")

    return render(request, "doctor/profile_edit.html", {
        "doctor": doctor,
        "departments": DEPARTMENT_CHOICES,
    })




import json
import logging
import os
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from dotenv import dotenv_values

from .models import DEPARTMENT_CHOICES

logger = logging.getLogger(__name__)

# Model name can be changed from .env (GEMINI_MODEL) without touching code.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def _chat_language_instruction(message):
    """Pick the answer language from the latest message, including Roman Hindi."""
    if re.search(r"[\u0900-\u097f]", message):
        return "Reply only in Hindi using Devanagari script."

    roman_hindi = re.compile(
        r"\b(main|mujhe|mere|mera|meri|ko|kya|kyu|kaise|hai|hain|hoon|"
        r"raha|rahi|bukhar|bukhaar|dard|sar|kaunsi|konsi|dawa|dawai|"
        r"lu|karu|karo|batao|paani|thoda|nahi|nahin|se|aur)\b",
        re.IGNORECASE,
    )
    if roman_hindi.search(message):
        return (
            "MANDATORY LANGUAGE: Write the whole answer in Romanized Hindi/Hinglish using English letters. "
            "Use Hindi sentence structure and everyday Hindi words (for example: 'Bukhar ke liye pehle temperature check karein. Aapki age kya hai?'). "
            "Do not answer in English sentences and do not use Devanagari."
        )
    return "Reply in clear, simple English."


def _env_value(name):
    value = os.getenv(name, "").strip()
    if not value:
        local = dotenv_values(settings.BASE_DIR / ".env").get(name)
        if local and local.strip():
            value = local.strip()
    return value


@require_http_methods(["GET", "POST"])
def health_chat(request):
    """Public, privacy-conscious chatbot endpoint. Chat content is not persisted."""
    if request.method == "GET":
        return render(request, "patient/health_chat.html")

    now = int(time.time())
    window = request.session.get("health_chat_rate_window", 0)
    count = request.session.get("health_chat_rate_count", 0)
    if now - window >= 60:
        window, count = now, 0
    if count >= 15:
        return JsonResponse({"error": "Please wait a moment before sending another message."}, status=429)
    request.session["health_chat_rate_window"] = window
    request.session["health_chat_rate_count"] = count + 1

    try:
        payload = json.loads(request.body)
        messages_in = payload.get("messages", [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Please send a valid chat message."}, status=400)

    if not isinstance(messages_in, list) or not messages_in:
        return JsonResponse({"error": "Type a message to start the chat."}, status=400)

    safe_messages = []
    for item in messages_in[-10:]:
        if not isinstance(item, dict) or item.get("role") not in ("user", "assistant"):
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            safe_messages.append({"role": item["role"], "content": content[:1200]})
    if not safe_messages or safe_messages[-1]["role"] != "user":
        return JsonResponse({"error": "Please send a valid user message."}, status=400)

    api_key = _env_value("GEMINI_API_KEY")
    if not api_key:
        return JsonResponse({
            "error": "Gemini AI key is not configured yet. Add GEMINI_API_KEY to your local .env file to enable AI replies."
        }, status=503)

    model = _env_value("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

    department_names = ", ".join(label for _value, label in DEPARTMENT_CHOICES)
    latest_user_message = safe_messages[-1]["content"]
    response_format = _chat_language_instruction(latest_user_message)
    if re.search(r"\b(fever|bukhar|bukhaar|temperature|taap)\b|[\u092c\u0941\u0916\u093e\u0930]", latest_user_message, re.IGNORECASE):
        response_format += (
            " Address fever directly: suggest rest, fluids, and checking the temperature; "
            "do not name or dose medicines. Ask the user's age, measured temperature, and how long the fever has lasted."
        )
    instructions = (
        "You are MeCare, a careful hospital health-information assistant. "
        f"For this latest message, {response_format} "
        "Understand Hindi in Devanagari, Romanized Hindi, Hinglish, and English. "
        "For symptom questions (for example fever/bukhar or headache/sar dard), acknowledge that exact symptom and give concise, relevant, "
        "safe general self-care information; do not give a generic refusal. For fever, suggest checking temperature, rest, and fluids; "
        "For a fever question, always ask how high the temperature is, how long it has lasted, and the patient's age. "
        "For headache, ask when it started and whether there are other symptoms. "
        "Never diagnose, prescribe, recommend a specific medicine, or give a medicine dose. Explain that a clinician or pharmacist can advise "
        "on medicines based on age, conditions, allergies, pregnancy, and other medicines. "
        "If a symptom could be urgent, identify the relevant warning signs and advise urgent/emergency care. Fever in a baby under 3 months "
        "with temperature 38 C or above needs urgent medical assessment. For severe breathing difficulty, chest pain, stroke signs, heavy bleeding, "
        "loss of consciousness, seizure, or suicidal intent, tell them to contact local emergency services now. "
        "Do not claim to book appointments or access private records. For department guidance, only suggest these hospital departments when relevant: "
        f"{department_names}. Keep replies concise, empathetic, easy to understand, and use plain text."
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": instructions}]},
        "contents": [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{
                    "text": (
                        message["content"] + "\n\n" +
                        "IMPORTANT: " + response_format
                        if message is safe_messages[-1] and message["role"] == "user"
                        else message["content"]
                    )
                }],
            }
            for message in safe_messages
        ],
        # FIX: 350 was too small. Newer Gemini models use output tokens for
        # internal "thinking", which left no tokens for the visible answer.
        "generationConfig": {
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingLevel": "minimal"},
        },
    }).encode("utf-8")

    api_request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        # Gemini may spend time reasoning or briefly return an overloaded response.
        # Keep the retry bounded so a single chat turn cannot loop indefinitely.
        for attempt in range(2):
            try:
                with urllib.request.urlopen(api_request, timeout=30) as response:
                    result = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                if attempt == 0 and error.code in (500, 502, 503):
                    logger.warning("Gemini transient HTTP %s for model=%s; retrying once", error.code, model)
                    time.sleep(0.8)
                    continue
                raise

        candidates = result.get("candidates") or [{}]
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        # Skip internal "thought" parts if the API returns them.
        answer = "".join(
            part.get("text", "") for part in parts if not part.get("thought")
        ).strip()

        if not answer:
            finish_reason = candidate.get("finishReason")
            block_reason = (result.get("promptFeedback") or {}).get("blockReason")
            logger.warning(
                "Gemini empty reply: model=%s finishReason=%s blockReason=%s",
                model, finish_reason, block_reason,
            )
            if finish_reason == "MAX_TOKENS":
                msg = "The AI ran out of space while thinking. Please ask a shorter question or try again."
            elif finish_reason in ("SAFETY", "PROHIBITED_CONTENT") or block_reason:
                msg = "I can't answer that one. Please rephrase, or contact a doctor directly."
            else:
                msg = "Gemini could not respond right now. Please try again shortly."
            return JsonResponse({"error": msg}, status=502)

        return JsonResponse({"reply": answer})

    except urllib.error.HTTPError as error:
        logger.warning("Gemini HTTP %s for model=%s", error.code, model)
        if error.code == 429:
            return JsonResponse({
                "error": "Gemini free-tier limit reached. Please try again later; no paid model is being used."
            }, status=429)
        if error.code in (401, 403):
            return JsonResponse({"error": "Gemini rejected this API key or the key does not have access to this model."}, status=502)
        if error.code == 404:
            return JsonResponse({"error": f"Gemini model '{model}' was not found. Set GEMINI_MODEL in .env to a valid model name."}, status=502)
        return JsonResponse({"error": "Gemini could not respond right now. Please check the API key and try again."}, status=502)
    except urllib.error.URLError:
        return JsonResponse({
            "error": "This server cannot reach Google's Gemini API. Check outbound internet, proxy, or firewall access to generativelanguage.googleapis.com."
        }, status=502)
    except TimeoutError:
        return JsonResponse({"error": "Gemini took too long to respond. Please try again shortly."}, status=502)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Gemini could not respond right now. Please try again shortly."}, status=502)

@patient_required
def patient_dashboard(request):
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Patient profile does not exist. Please contact admin.")
        return redirect("login")

    doctors = Doctor.objects.all()
    availability = Availability.objects.all()

    upcoming = Appointment.objects.filter(
        patient=patient,
        date__gte=date.today()
    ).select_related("doctor__user", "doctor__hospital__district").order_by("date", "time")

    departments = [label for _value, label in DEPARTMENT_CHOICES]

    return render(request, "patient/dashboard.html", {
        "patient": patient,
        "doctors": doctors,
        "availability": availability,
        "upcoming": upcoming,
        "departments": departments,
    })


@patient_required
def patient_appointments(request):
    patient = Patient.objects.get(user=request.user)

    upcoming = Appointment.objects.filter(
        patient=patient,
        date__gte=date.today()
    ).select_related("doctor__user", "doctor__hospital__district").order_by("date", "time")

    past = Appointment.objects.filter(
        patient=patient,
        date__lt=date.today()
    ).select_related("doctor__user", "doctor__hospital__district").order_by("-date", "-time")

    return render(request, "patient/appointments.html", {
        "upcoming": upcoming,
        "past": past
    })


from .models import Doctor

from datetime import datetime

@patient_required
def patient_book_appointment(request):
    if request.method == "POST":
        try:
            appointment_fee = configured_appointment_fee()
            if appointment_fee is not None:
                razorpay_test_client()
        except PaymentError as exc:
            messages.error(request, str(exc))
            return redirect("patient_book_appointment")

        district_id = request.POST.get("district")
        hospital_id = request.POST.get("hospital")
        department = request.POST.get("department", "").strip()
        doctor_id = request.POST.get("doctor")
        try:
            district_id, hospital_id, doctor_id = int(district_id), int(hospital_id), int(doctor_id)
        except (TypeError, ValueError):
            messages.error(request, "Choose a valid district, hospital, department, and doctor.")
            return redirect("patient_book_appointment")
        try:
            appointment_date = datetime.strptime(request.POST.get("date", ""), "%Y-%m-%d").date()
            appointment_time = datetime.strptime(request.POST.get("time", ""), "%H:%M").time()
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid appointment date and time.")
            return redirect("patient_book_appointment")
        if appointment_date < timezone.localdate() + timedelta(days=1):
            messages.error(request, "Choose tomorrow or a later date.")
            return redirect("patient_book_appointment")

        hospital = get_object_or_404(Hospital, pk=hospital_id, district_id=district_id, is_active=True)
        doctor = get_object_or_404(Doctor.objects.select_related("user", "hospital"), pk=doctor_id,
                                   hospital=hospital, department=department)
        appointment = Appointment(patient=request.user.patient, doctor=doctor,
                                  date=appointment_date, time=appointment_time,
                                  symptoms=request.POST.get("symptoms", "").strip(),
                                  status="Pending Payment" if appointment_fee else "Waiting",
                                  payment_status="Pending" if appointment_fee else "Legacy",
                                  payment_amount=appointment_fee or 0)
        try:
            appointment.full_clean()
            with transaction.atomic():
                appointment.save()
        except (IntegrityError, ValidationError):
            messages.error(request, "That time slot is unavailable. Choose another date or time.")
            return redirect("patient_book_appointment")
        if appointment_fee:
            try:
                order = create_appointment_order(appointment)
                appointment.razorpay_order_id = order["id"]
                appointment.save(update_fields=["razorpay_order_id"])
            except Exception as exc:
                appointment.payment_status = "Failed"
                appointment.status = "Cancelled"
                appointment.save(update_fields=["payment_status", "status"])
                messages.error(request, str(exc) if isinstance(exc, PaymentError) else "Could not start payment. Please try again.")
                return redirect("patient_book_appointment")
            return redirect("patient_payment_checkout", appointment_id=appointment.pk)
        messages.success(request, "Appointment booked successfully. No payment is required.")
        return redirect("patient_appointment_success", booking_reference=appointment.booking_reference)

    try:
        appointment_fee = configured_appointment_fee()
    except PaymentError as exc:
        appointment_fee = None
        messages.error(request, str(exc))
    return render(request, "patient/book_appointment.html", {
        "districts": District.objects.all(),
        "min_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        "appointment_fee": appointment_fee,
    })


@patient_required
def patient_payment_checkout(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor__user", "doctor__hospital", "doctor__hospital__district"),
        pk=appointment_id, patient=request.user.patient,
    )
    if appointment.payment_status == "Paid":
        return redirect("patient_appointment_success", booking_reference=appointment.booking_reference)
    if appointment.payment_status != "Pending" or not appointment.razorpay_order_id:
        messages.error(request, "This payment is no longer pending. Please book a new appointment.")
        return redirect("patient_appointments")
    return render(request, "patient/payment_checkout.html", {
        "appointment": appointment,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": int(appointment.payment_amount * 100),
        "verify_url": reverse("patient_verify_payment", args=[appointment.pk]),
        "failure_url": reverse("patient_payment_failed", args=[appointment.pk]),
    })


@patient_required
@require_POST
def patient_verify_payment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user.patient)
    success_url = reverse("patient_appointment_success", args=[appointment.booking_reference])
    slip_url = reverse("appointment_pdf", args=[appointment.booking_reference])
    if appointment.payment_status == "Paid":
        return JsonResponse({"ok": True, "success_url": success_url, "slip_url": slip_url})
    if appointment.payment_status != "Pending" or appointment.status != "Pending Payment":
        return JsonResponse({"ok": False, "error": "This appointment payment is no longer pending."}, status=409)

    order_id = request.POST.get("razorpay_order_id", "")
    payment_id = request.POST.get("razorpay_payment_id", "")
    signature = request.POST.get("razorpay_signature", "")
    if order_id != appointment.razorpay_order_id:
        return JsonResponse({"ok": False, "error": "Payment order does not match this appointment."}, status=400)

    try:
        verify_appointment_payment(appointment, payment_id, signature)
        with transaction.atomic():
            locked_appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
            locked_success_url = reverse("patient_appointment_success", args=[locked_appointment.booking_reference])
            locked_slip_url = reverse("appointment_pdf", args=[locked_appointment.booking_reference])
            if locked_appointment.payment_status == "Paid":
                return JsonResponse({"ok": True, "success_url": locked_success_url, "slip_url": locked_slip_url})
            if locked_appointment.payment_status != "Pending":
                return JsonResponse({"ok": False, "error": "This payment is no longer pending."}, status=409)
            locked_appointment.payment_status = "Paid"
            locked_appointment.razorpay_payment_id = payment_id
            locked_appointment.status = "Waiting"
            locked_appointment.save(update_fields=["payment_status", "razorpay_payment_id", "status"])
    except PaymentError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except Exception:
        return JsonResponse({"ok": False, "error": "Payment was received but could not be linked. Contact hospital support with your Razorpay payment ID."}, status=409)

    final_success_url = reverse("patient_appointment_success", args=[appointment.booking_reference])
    final_slip_url = reverse("appointment_pdf", args=[appointment.booking_reference])
    return JsonResponse({"ok": True, "success_url": final_success_url, "slip_url": final_slip_url})


@patient_required
@require_POST
def patient_payment_failed(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user.patient)
    if appointment.payment_status == "Pending":
        appointment.payment_status = "Failed"
        appointment.status = "Cancelled"
        appointment.save(update_fields=["payment_status", "status"])
    return JsonResponse({"ok": True})


@patient_required
def patient_appointment_success(request, booking_reference):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient__user", "doctor__user", "doctor__hospital", "doctor__hospital__district"
        ),
        booking_reference=booking_reference,
        patient=request.user.patient,
        payment_status__in=("Paid", "Legacy"),
    )
    return render(request, "patient/payment_success.html", {
        "appointment": appointment,
        "pdf_url": reverse("appointment_pdf", args=[appointment.booking_reference]),
    })


@patient_required
def appointment_pdf(request, booking_reference):
    from io import BytesIO
    from pathlib import Path
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    appointment = get_object_or_404(
        Appointment.objects.select_related("patient__user", "doctor__user", "doctor__hospital__district"),
        booking_reference=booking_reference, patient=request.user.patient,
        payment_status__in=("Paid", "Legacy"), status__in=("Waiting", "In Process", "Completed"),
    )
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
                                 topMargin=18 * mm, bottomMargin=18 * mm)
    font_name = "Helvetica"
    font_candidates = [
        settings.BASE_DIR / "static" / "fonts" / "NotoSansDevanagari-Regular.ttf",
        Path("C:/Windows/Fonts/mangal.ttf"),
        Path("C:/Windows/Fonts/Nirmala.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("MeCareUnicode", str(font_path), subfontIndex=0 if font_path.suffix.lower() == ".ttc" else 0))
                font_name = "MeCareUnicode"
                break
            except Exception:
                continue

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SlipTitle", parent=styles["Title"], fontName=font_name, textColor=colors.HexColor("#1268e8"), alignment=TA_CENTER)
    body_style = ParagraphStyle("SlipBody", parent=styles["BodyText"], fontName=font_name, leading=17)
    small_style = ParagraphStyle("SlipSmall", parent=body_style, fontSize=9, textColor=colors.HexColor("#526070"))
    story = [
        Paragraph("MeCare HMS", title_style),
        Paragraph("Appointment confirmation / अपॉइंटमेंट पर्ची", body_style),
        Spacer(1, 7 * mm),
        Paragraph(f"Booking reference: <b>{appointment.booking_reference}</b>", body_style),
        Paragraph(
            "Payment: Not required" if appointment.payment_status == "Legacy"
            else f"Payment: PAID · ₹{appointment.payment_amount:.2f}",
            body_style,
        ),
        Spacer(1, 4 * mm),
    ]
    hospital_name = appointment.doctor.hospital.name if appointment.doctor.hospital else "Not assigned"
    district_name = appointment.doctor.hospital.district.name if appointment.doctor.hospital else ""
    rows = [
        ["Patient", appointment.patient.user.get_full_name() or appointment.patient.user.username],
        ["Doctor", f"Dr. {appointment.doctor.user.get_full_name()}"],
        ["Department", dict(DEPARTMENT_CHOICES).get(appointment.doctor.department, appointment.doctor.department)],
        ["Hospital", hospital_name],
        ["District", district_name],
        ["Address", appointment.doctor.hospital.address if appointment.doctor.hospital else appointment.doctor.location],
        ["Hospital phone", appointment.doctor.hospital.phone if appointment.doctor.hospital and appointment.doctor.hospital.phone else "—"],
        ["Appointment date", appointment.date.strftime("%d %B %Y")],
        ["Appointment time", appointment.time.strftime("%I:%M %p")],
    ]
    table_data = [[Paragraph(f"<b>{escape(str(label))}</b>", body_style), Paragraph(escape(str(value or "—")), body_style)] for label, value in rows]
    table = Table(table_data, colWidths=[45 * mm, 115 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4ff")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e2f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 8 * mm), Paragraph("Please arrive 15 minutes before your appointment and show this slip at the hospital desk.", small_style)])
    document.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="MeCare-appointment-{appointment.booking_reference}.pdf"'
    return response


@patient_required
def api_hospitals(request):
    try:
        district_id = int(request.GET.get("district", ""))
    except (TypeError, ValueError):
        district_id = -1
    items = Hospital.objects.filter(district_id=district_id, is_active=True).order_by("name")
    return JsonResponse({"results": [{"id": h.id, "name": h.name} for h in items]})


@patient_required
def api_departments(request):
    try:
        hospital_id = int(request.GET.get("hospital", ""))
    except (TypeError, ValueError):
        hospital_id = -1
    items = Doctor.objects.filter(hospital_id=hospital_id, hospital__is_active=True).values_list("department", flat=True).distinct().order_by("department")
    department_labels = dict(DEPARTMENT_CHOICES)
    return JsonResponse({"results": [{"id": name, "name": department_labels.get(name, name)} for name in items]})


@patient_required
def api_hospital_doctors(request):
    try:
        hospital_id = int(request.GET.get("hospital", ""))
    except (TypeError, ValueError):
        hospital_id = -1
    items = Doctor.objects.filter(hospital_id=hospital_id, department=request.GET.get("department", ""), hospital__is_active=True).select_related("user").order_by("user__last_name", "user__first_name")
    return JsonResponse({"results": [{
        "id": d.id,
        "name": f"Dr. {d.user.get_full_name()}" if d.user.get_full_name().strip() else "Dr. Prince Chauhan",
    } for d in items]})


@patient_required
def patient_cancel_appointment(request, appointment_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user.patient)
    if appointment.payment_status not in ("Paid", "Legacy"):
        messages.error(request, "This appointment cannot be cancelled in its current state.")
        return redirect("patient_appointments")
    appointment.status = "Cancelled"
    appointment.save(update_fields=["status"])
    messages.success(request, "Appointment cancelled.")
    return redirect("patient_appointments")







@patient_required
def patient_doctors_list(request):
    doctors = Doctor.objects.all()
    return render(request, "patient/doctors_list.html", {"doctors": doctors})


@patient_required
def patient_doctor_profile(request):
    doctor_id = request.GET.get("id")

    if not doctor_id:
        messages.error(request, "Doctor ID missing.")
        return redirect("patient_doctors_list")

    doctor = get_object_or_404(Doctor, id=doctor_id)
    availability = Availability.objects.filter(doctor=doctor)

    return render(request, "patient/doctor_profile.html", {
        "doctor": doctor,
        "availability": availability
    })


@patient_required
def patient_history(request):
    patient = Patient.objects.get(user=request.user)
    records = Treatment.objects.filter(appointment__patient=patient)

    return render(request, "patient/history.html", {"records": records})


@patient_required
def patient_profile(request):
    patient = Patient.objects.get(user=request.user)
    return render(request, "patient/profile.html", {"patient": patient})


@patient_required
def patient_profile_edit(request):
    patient = Patient.objects.get(user=request.user)

    if request.method == "POST":
        patient.age = request.POST["age"]
        patient.gender = request.POST["gender"]
        patient.phone_number = request.POST["phone"]
        patient.address = request.POST["address"]
        patient.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("patient_profile")

    return render(request, "patient/profile_edit.html", {"patient": patient})

# API VIEWS

from rest_framework.viewsets import ModelViewSet
from .models import Doctor
from .serializers import DoctorSerializer
from rest_framework.permissions import IsAuthenticated

class DoctorViewSet(ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]
