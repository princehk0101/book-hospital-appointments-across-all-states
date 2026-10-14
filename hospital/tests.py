from datetime import timedelta, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Appointment, District, Doctor, Hospital, Patient


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user("patient", password="test-password")
        self.patient = Patient.objects.create(user=self.patient_user, age=30, gender="Other", address="Test", phone_number="0000000000")
        self.district = District.objects.create(name="Test District", slug="test-district")
        self.hospital = Hospital.objects.create(name="Sample Hospital", district=self.district, address="Test", is_sample=True)
        self.other_hospital = Hospital.objects.create(name="Other Hospital", district=self.district, address="Test", is_sample=True)
        self.doctor_user = User.objects.create_user("doctor", first_name="Sample", last_name="Doctor")
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital,
            specialization="Heart", department="Cardiology", experience=5,
            language="English", location="Test", is_sample=True)

    def make_appointment(self, day, doctor=None, at=None, status="Waiting"):
        return Appointment(patient=self.patient, doctor=doctor or self.doctor,
            date=day, time=at or time(10, 0), status=status)

    def test_past_and_today_dates_are_rejected_but_tomorrow_is_allowed(self):
        today = timezone.localdate()
        for day in (today - timedelta(days=1), today):
            with self.subTest(day=day), self.assertRaises(ValidationError):
                self.make_appointment(day).full_clean()
        tomorrow = self.make_appointment(today + timedelta(days=1))
        tomorrow.full_clean()

    def test_booking_rejects_doctor_from_another_hospital_or_department(self):
        self.client.force_login(self.patient_user)
        response = self.client.post(reverse("patient_book_appointment"), {
            "district": self.district.pk,
            "hospital": self.other_hospital.pk,
            "department": "Cardiology",
            "doctor": self.doctor.pk,
            "date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "time": "10:00",
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Appointment.objects.count(), 0)

        response = self.client.post(reverse("patient_book_appointment"), {
            "district": self.district.pk,
            "hospital": self.hospital.pk,
            "department": "Neurology",
            "doctor": self.doctor.pk,
            "date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "time": "10:00",
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_cascading_lists_return_hospitals_departments_and_doctors(self):
        self.client.force_login(self.patient_user)
        hospitals = self.client.get(reverse("api_hospitals"), {"district": self.district.pk}).json()["results"]
        self.assertEqual({item["id"] for item in hospitals}, {self.hospital.pk, self.other_hospital.pk})
        departments = self.client.get(reverse("api_departments"), {"hospital": self.hospital.pk}).json()["results"]
        self.assertEqual(departments, [{"id": "Cardiology", "name": "Cardiology"}])
        doctors = self.client.get(reverse("api_hospital_doctors"), {
            "hospital": self.hospital.pk, "department": "Cardiology",
        }).json()["results"]
        self.assertEqual([item["id"] for item in doctors], [self.doctor.pk])

    def test_same_doctor_date_time_cannot_be_double_booked_except_after_cancel(self):
        day = timezone.localdate() + timedelta(days=1)
        self.make_appointment(day).save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_appointment(day).save()

        Appointment.objects.filter(doctor=self.doctor, date=day).update(status="Cancelled")
        self.make_appointment(day).save()

