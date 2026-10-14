from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import uuid

DEPARTMENT_CHOICES = [
    ("Cardiology", "Cardiology — हृदय रोग"),
    ("Dermatology", "Dermatology — त्वचा रोग"),
    ("Dentistry", "Dentistry — दंत रोग"),
    ("Emergency Medicine", "Emergency Medicine — आपात चिकित्सा"),
    ("Endocrinology", "Endocrinology — हार्मोन रोग"),
    ("ENT", "ENT — कान, नाक और गला"),
    ("Gastroenterology", "Gastroenterology — पेट और पाचन रोग"),
    ("General Medicine", "General Medicine — सामान्य चिकित्सा"),
    ("General Surgery", "General Surgery — सामान्य शल्य चिकित्सा"),
    ("Gynecology", "Gynecology & Obstetrics — स्त्री एवं प्रसूति रोग"),
    ("Nephrology", "Nephrology — गुर्दा रोग"),
    ("Neurology", "Neurology — तंत्रिका रोग"),
    ("Oncology", "Oncology — कैंसर रोग"),
    ("Ophthalmology", "Ophthalmology — नेत्र रोग"),
    ("Orthopedics", "Orthopedics — हड्डी एवं जोड़ रोग"),
    ("Pediatrics", "Pediatrics — बाल रोग"),
    ("Psychiatry", "Psychiatry — मानसिक स्वास्थ्य"),
    ("Pulmonology", "Pulmonology — फेफड़े एवं श्वसन रोग"),
    ("Radiology", "Radiology — रेडियोलॉजी / इमेजिंग"),
    ("Urology", "Urology — मूत्र रोग"),
]


class District(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Hospital(models.Model):
    name = models.CharField(max_length=180)
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="hospitals")
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["district", "name"], name="unique_hospital_name_per_district")]

    def __str__(self):
        return f"{self.name} ({self.district})"


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital, null=True, blank=True, on_delete=models.SET_NULL, related_name="doctors")
    profile_photo = models.ImageField(upload_to="doctor_profiles/", blank=True, null=True)
    specialization = models.CharField(max_length=100)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES)
    experience = models.IntegerField()
    language = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    is_sample = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return self.user.get_full_name()

class Appointment(models.Model):

    STATUS_CHOICES = (
        ("Pending Payment", "Pending Payment"),
        ("Waiting", "Waiting"),
        ("In Process", "In Process"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    booking_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_status = models.CharField(max_length=12, choices=(("Pending", "Pending"), ("Paid", "Paid"), ("Failed", "Failed"), ("Legacy", "No payment required")), default="Legacy")
    payment_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    razorpay_order_id = models.CharField(max_length=80, unique=True, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=80, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    time = models.TimeField()

    symptoms = models.TextField(blank=True, null=True)   

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Waiting")

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["doctor", "date", "time"],
            condition=~Q(status="Cancelled"),
            name="unique_active_doctor_appointment_slot",
        )]

    def clean(self):
        super().clean()
        if self.date and self.date < timezone.localdate() + timedelta(days=1):
            raise ValidationError({"date": "Appointments must be booked for tomorrow or later."})

    def __str__(self):
        return f"{self.date} - {self.patient.user.get_full_name()}"



class Treatment(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    diagnosis = models.TextField()
    prescription = models.TextField()
    notes = models.TextField()

    def __str__(self):
        return f"Treatment for {self.appointment.patient.user.get_full_name()}"


class Availability(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    time_range = models.CharField(max_length=100)   

    def __str__(self):
        return f"{self.doctor} - {self.day}"

