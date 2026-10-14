from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from hospital.models import DEPARTMENT_CHOICES, Doctor, Hospital, Patient
from hospital.utils import validate_profile_photo
from django.contrib import messages
from django.db import transaction
from django.db.models import Q



#   USER REGISTER

from accounts.models import Account
def _registration_context(error=None, role=""):
    return {
        "error": error,
        "selected_role": role,
        "departments": DEPARTMENT_CHOICES,
        "hospitals": Hospital.objects.filter(is_active=True).select_related("district").order_by("district__name", "name"),
    }

def register(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password")
        role = request.POST.get("role", "").strip().lower()
        age_value = request.POST.get("age", "").strip()
        gender = request.POST.get("gender", "").strip()
        address = request.POST.get("address", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        department = request.POST.get("department", "").strip()
        experience_value = request.POST.get("experience", "").strip()
        language = request.POST.get("language", "").strip()
        hospital_id = request.POST.get("hospital", "").strip()

        if not name or not email or not password or role not in ("patient", "doctor"):
            return render(request, "register.html", _registration_context(
                "Please enter your name, email, password, and select Patient or Doctor.", role))
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            return render(request, "register.html", _registration_context("Email already registered! Please log in.", role))

        patient_age = 0
        if role == "patient":
            try:
                patient_age = int(age_value)
                if not 0 <= patient_age <= 120:
                    raise ValueError
            except ValueError:
                return render(request, "register.html", _registration_context("Enter a valid age between 0 and 120.", role))
            if not gender or not address or not phone:
                return render(request, "register.html", _registration_context("Patient registration requires age, gender, phone, and address.", role))

        doctor_hospital = None
        doctor_experience = 0
        profile_photo = request.FILES.get("profile_photo") if role == "doctor" else None
        if role == "doctor":
            try:
                doctor_experience = int(experience_value)
                if not 0 <= doctor_experience <= 80:
                    raise ValueError
            except ValueError:
                return render(request, "register.html", _registration_context("Enter a valid number of experience years.", role))
            try:
                doctor_hospital_id = int(hospital_id)
            except (TypeError, ValueError):
                doctor_hospital_id = None
            doctor_hospital = Hospital.objects.filter(pk=doctor_hospital_id, is_active=True).first()
            valid_departments = {value for value, _label in DEPARTMENT_CHOICES}
            if not doctor_hospital or department not in valid_departments or not specialization or not language or not phone:
                return render(request, "register.html", _registration_context(
                    "Doctor registration requires phone, hospital, specialization, department, experience, and languages.", role))
            photo_error = validate_profile_photo(profile_photo)
            if photo_error:
                return render(request, "register.html", _registration_context(photo_error, role))

        name_parts = name.split()
        fname = name_parts[0]
        lname = " ".join(name_parts[1:])

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=fname,
                last_name=lname,
                password=password
            )

            Account.objects.create(user=user, phone=phone, role=role)

            if role == "doctor":
                Doctor.objects.create(
                    user=user,
                    hospital=doctor_hospital,
                    specialization=specialization,
                    department=department,
                    experience=doctor_experience,
                    language=language,
                    location=doctor_hospital.address,
                    profile_photo=profile_photo,
                )
            else:
                Patient.objects.create(
                    user=user,
                    age=patient_age,
                    gender=gender,
                    address=address,
                    phone_number=phone
                )

        auth_login(request, user)
        return redirect("doctor_profile" if role == "doctor" else "patient_profile")

    return render(request, "register.html", _registration_context())






# LOGIN

def login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "").strip().lower()
        if not email or not password or role not in ("admin", "doctor", "patient"):
            return render(request, "login.html", {"error": "Enter your email, password, and account type."})

        # Try authenticate using username directly
        user = authenticate(username=email, password=password)

        if not user:
            try:
                u = User.objects.get(email__iexact=email)
                user = authenticate(username=u.username, password=password)
            except:
                user = None

        if not user:
            return render(request, "login.html", {"error": "Invalid email or password!"})

        #  ADMIN LOGIN — skip Account model
        if role == "admin":
            if not user.is_superuser:
                return render(request, "login.html", {"error": "You are not an admin!"})

            auth_login(request, user)
            return redirect("/hospital/admin/dashboard/")

        #  DOCTOR & PATIENT LOGIN — must exist in Account model
        profile_exists = (
            Patient.objects.filter(user=user).exists()
            if role == "patient"
            else Doctor.objects.filter(user=user).exists()
        )
        account = Account.objects.filter(user=user).first()
        if account and account.role.strip().lower() != role:
            return render(request, "login.html", {"error": "Role does not match!"})
        if not profile_exists:
            return render(request, "login.html", {
                "error": f"No {role} profile is linked to this account. Please register or contact admin."
            })

        auth_login(request, user)

        if role == "doctor":
            return redirect("doctor_profile")
        elif role == "patient":
            return redirect("patient_profile")

    return render(request, "login.html")


def logout(request):
    auth_logout(request)
    return redirect("login")








def _department_cards():
    department_icons = {
        "Cardiology": "fa-heart-pulse",
        "Dermatology": "fa-hand-sparkles",
        "Dentistry": "fa-tooth",
        "Emergency Medicine": "fa-kit-medical",
        "Endocrinology": "fa-vial",
        "ENT": "fa-ear-listen",
        "Gastroenterology": "fa-stomach",
        "General Medicine": "fa-stethoscope",
        "General Surgery": "fa-user-doctor",
        "Gynecology": "fa-person-pregnant",
        "Nephrology": "fa-kidneys",
        "Neurology": "fa-brain",
        "Oncology": "fa-ribbon",
        "Ophthalmology": "fa-eye",
        "Orthopedics": "fa-bone",
        "Pediatrics": "fa-child",
        "Psychiatry": "fa-head-side-virus",
        "Pulmonology": "fa-lungs",
        "Radiology": "fa-x-ray",
        "Urology": "fa-droplet",
    }
    return [
        {"name": label, "icon": department_icons.get(value, "fa-hospital")}
        for value, label in DEPARTMENT_CHOICES
    ]


def home(request):
    return render(request, 'index.html', {"departments": _department_cards()})

def contact(request):
    return render(request, 'contact.html')



def about(request):
    return render(request, 'about.html', {"departments": _department_cards()})
