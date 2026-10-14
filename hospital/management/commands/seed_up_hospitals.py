import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from accounts.models import Account
from hospital.models import DEPARTMENT_CHOICES, District, Doctor, Hospital


DEPARTMENT_ALIASES = {
    "Orthopaedics": "Orthopedics", "Orthopaedic": "Orthopedics",
    "Obstetrics & Gynaecology": "Gynecology", "Obstetrics and Gynaecology": "Gynecology",
    "Paediatrics": "Pediatrics", "Pediatric": "Pediatrics", "Dental": "Dentistry",
    "Emergency & Trauma": "Emergency Medicine", "Emergency": "Emergency Medicine",
    "Pulmonary Medicine": "Pulmonology", "Chest Medicine": "Pulmonology",
    "Radiodiagnosis": "Radiology", "Medical Oncology": "Oncology",
    "Surgical Oncology": "Oncology", "Radiation Oncology": "Oncology",
    "Haematology": "Oncology", "Hematology": "Oncology", "Neurosurgery": "Neurology",
    "Cardiothoracic & Vascular Surgery": "Cardiology", "GI Surgery": "Gastroenterology",
    "Endocrine Surgery": "Endocrinology", "Clinical Immunology": "General Medicine",
    "Medical Genetics": "General Medicine", "Nuclear Medicine": "Radiology",
    "Anaesthesia": "General Medicine", "Anesthesia": "General Medicine",
    "Plastic Surgery": "General Surgery", "Paediatric Surgery": "Pediatrics",
    "Critical Care": "Emergency Medicine", "Palliative Care": "Oncology",
    "Pathology": "Radiology",
}

DEMO_DOCTOR_NAMES = [
    ("Aarav", "Sharma"), ("Ananya", "Verma"), ("Vivaan", "Mishra"),
    ("Diya", "Singh"), ("Aditya", "Gupta"), ("Meera", "Yadav"),
    ("Arjun", "Saxena"), ("Kavya", "Rao"), ("Ishaan", "Srivastava"),
    ("Saanvi", "Khan"), ("Reyansh", "Tiwari"), ("Aditi", "Joshi"),
    ("Prince", "Chauhan"), ("Nisha", "Patel"), ("Rohan", "Agarwal"),
    ("Pooja", "Chauhan"), ("Karan", "Malhotra"), ("Ira", "Shukla"),
    ("Kabir", "Mehta"), ("Riya", "Choudhary"), ("Dev", "Pandey"),
    ("Tara", "Kapoor"), ("Manav", "Bansal"), ("Simran", "Kaur"),
]


class Command(BaseCommand):
    help = "Load SAMPLE/TEST Uttar Pradesh hospitals and doctors from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="JSON file with districts, hospitals, and departments")

    def handle(self, *args, **options):
        path = Path(options["file"])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Cannot read hospital seed file: {exc}") from exc
        if isinstance(payload, list) and payload and "district" in payload[0]:
            # The project's up_hospitals_wise_name.json is the source dataset. Its
            # Hindi labels live in the reviewed companion data file; match records
            # by their original English source names, then add districts absent from
            # that 60-district source so the full state remains selectable.
            localized_path = Path(__file__).resolve().parents[2] / "data" / "up_hospitals_seed_hi.json"
            try:
                localized = json.loads(localized_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CommandError(f"Cannot read Hindi hospital labels: {exc}") from exc
            localized_by_source = {item.get("source_district"): item for item in localized if item.get("source_district")}
            districts = []
            seen = set()
            for source_district in payload:
                source_name = source_district.get("district")
                target = localized_by_source.get(source_name)
                if not target:
                    raise CommandError(f"Hindi district mapping is missing for {source_name!r}.")
                target_hospitals = {item.get("source_name"): item for item in target["hospitals"] if item.get("source_name")}
                hospitals = []
                for source_hospital in source_district.get("hospitals", []):
                    source_hospital_name = source_hospital.get("name")
                    translated = target_hospitals.get(source_hospital_name)
                    if not translated:
                        raise CommandError(f"Hindi hospital mapping is missing for {source_hospital_name!r} in {source_name}.")
                    hospitals.append({
                        **translated,
                        "departments": list(dict.fromkeys(
                            DEPARTMENT_ALIASES.get(str(dept).strip(), str(dept).strip())
                            for dept in source_hospital.get("departments", [])
                        )),
                    })
                districts.append({"name": target["name"], "slug": target["slug"], "hospitals": hospitals})
                seen.add(target["slug"])
            districts.extend(item for item in localized if item["slug"] not in seen)
        elif isinstance(payload, list):
            districts = payload
        elif isinstance(payload, dict) and isinstance(payload.get("districts"), list):
            districts = payload["districts"]
        else:
            raise CommandError("Expected a district list or JSON shaped as {\"districts\": [{\"name\": ..., \"hospitals\": [...]}]}.")

        allowed_departments = {value for value, _label in DEPARTMENT_CHOICES}
        hospitals_added = doctors_added = 0
        with transaction.atomic():
            for district_data in districts:
                if not isinstance(district_data, dict) or not district_data.get("name"):
                    raise CommandError("Every district needs a name.")
                district_name = str(district_data["name"]).strip()
                district_slug = district_data.get("slug") or slugify(district_name)
                district, _ = District.objects.get_or_create(
                    name=district_name, defaults={"slug": district_slug})
                if not isinstance(district_data.get("hospitals", []), list):
                    raise CommandError(f"Hospitals for {district_name} must be a list.")

                for hospital_data in district_data.get("hospitals", []):
                    if not isinstance(hospital_data, dict) or not hospital_data.get("name"):
                        raise CommandError(f"Every hospital in {district_name} needs a name.")
                    raw_name = str(hospital_data["name"]).strip()
                    hospital_name = raw_name.removeprefix("नमूना — ").strip()
                    legacy_name = f"नमूना — {hospital_name}"
                    # Rename rows created by the previous demo seed in place.
                    Hospital.objects.filter(district=district, name=legacy_name).update(name=hospital_name)
                    hospital, was_created = Hospital.objects.get_or_create(
                        district=district, name=hospital_name,
                        defaults={"address": str(hospital_data.get("address", "Sample address")),
                                  "phone": str(hospital_data.get("phone", "")),
                                  "is_active": True, "is_sample": True},
                    )
                    if was_created:
                        hospitals_added += 1
                    else:
                        changed = False
                        if not hospital.is_sample:
                            hospital.is_sample, changed = True, True
                        if not hospital.is_active:
                            hospital.is_active, changed = True, True
                        if changed:
                            hospital.save(update_fields=["is_sample", "is_active"])

                    departments = hospital_data.get("departments", [])
                    if not isinstance(departments, list):
                        raise CommandError(f"Departments for {raw_name} must be a list.")
                    # This is demo data: make every configured department selectable
                    # at every seeded hospital and create a named demo profile for it.
                    departments = list(dict.fromkeys([
                        *departments,
                        *(value for value, _label in DEPARTMENT_CHOICES),
                    ]))
                    for department_index, department in enumerate(departments):
                        department = str(department).strip()
                        department = DEPARTMENT_ALIASES.get(department, department)
                        if department not in allowed_departments:
                            raise CommandError(f"Unknown department {department!r}; use a DEPARTMENT_CHOICES value.")
                        existing_doctor = Doctor.objects.filter(hospital=hospital, department=department).select_related("user").first()
                        if existing_doctor:
                            if existing_doctor.is_sample:
                                first_name, last_name = DEMO_DOCTOR_NAMES[(hospital.pk + department_index) % len(DEMO_DOCTOR_NAMES)]
                                existing_doctor.user.first_name = first_name
                                existing_doctor.user.last_name = last_name
                                existing_doctor.user.save(update_fields=["first_name", "last_name"])
                            continue
                        username = f"sample_{district_slug}_{hospital.pk}_{slugify(department).replace('-', '_')}"
                        first_name, last_name = DEMO_DOCTOR_NAMES[(hospital.pk + department_index) % len(DEMO_DOCTOR_NAMES)]
                        user, created = User.objects.get_or_create(
                            username=username,
                            defaults={"first_name": first_name, "last_name": last_name},
                        )
                        if created:
                            user.set_unusable_password()
                            user.save(update_fields=["password"])
                        Account.objects.get_or_create(user=user, defaults={"phone": "0000000000", "role": "doctor"})
                        Doctor.objects.get_or_create(
                            user=user,
                            defaults={"hospital": hospital, "specialization": department,
                                      "department": department, "experience": 5,
                                      "language": "English, Hindi", "location": hospital.address,
                                      "is_sample": True},
                        )
                        doctors_added += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. Added {hospitals_added} SAMPLE hospital(s) and {doctors_added} SAMPLE doctor(s)."))
