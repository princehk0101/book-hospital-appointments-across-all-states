# MeCare Hospital Management System

MeCare HMS is a Django web application for organizing the day-to-day workflows of a small hospital. It brings patient registration, appointment scheduling, doctor worklists, treatment records, and administrative management into one role-based portal.

**Live demo:** [django-hospital-management-system.onrender.com](https://django-hospital-management-system.onrender.com)

> **Demo notice:** Seeded hospital records and doctor profiles are fictional sample data. This project is for learning and demonstration; it is not a verified provider directory or a clinical system for real patient care.

## What this project helps solve

Hospitals often manage appointments and patient information across separate records and manual processes. MeCare HMS provides a shared application where:

- Patients can find a hospital and department, request an appointment, and keep their booking details together.
- Doctors can review their appointments and related patient history, record treatment notes, and manage availability.
- Administrators can maintain doctor, patient, and appointment records from one dashboard.

The application supports a district and hospital directory, 20 departments with English and Hindi labels, appointment PDFs, optional test-mode payments, and an optional Hindi/English health chat.

## Features

### Patient portal

- Register and manage a patient profile.
- Browse doctors and view doctor profiles.
- Book an appointment by district, hospital, department, doctor, date, and time.
- Add symptoms to a booking, review appointment history, and cancel eligible appointments.
- Download an appointment slip as a PDF.
- Use the Hindi/English health chat. AI-generated replies require a Gemini API key.

### Doctor portal

- View assigned appointments and patient history.
- Record diagnoses, prescriptions, and treatment notes.
- Manage availability and update a doctor profile.

### Admin portal

- View dashboard summaries and search records.
- Add, edit, and remove doctor and patient records.
- Review and manage appointments.
- Use the custom dashboard at `/hospital/admin/dashboard/`.

### Appointment and payment workflow

- Appointments are scheduled for tomorrow or a later date.
- A doctor cannot have two active appointments in the same time slot.
- If `APPOINTMENT_FEE` is blank, booking does not require payment.
- If a positive fee is configured, checkout uses Razorpay test keys and verifies the payment on the server before confirming the appointment.
- Successful appointments can be downloaded as a PDF slip.

The payment integration in this repository only accepts Razorpay test keys (`rzp_test_...`). It is not configured for live payments.

## Technology

- Python and Django
- Django REST Framework
- SQLite for local development; PostgreSQL through `DATABASE_URL` for hosting
- WhiteNoise and Gunicorn for static files and application serving
- Razorpay test checkout and optional Gemini-powered chat

## Getting started

### Requirements

- Python 3.10 or newer
- PowerShell on Windows, or a terminal on macOS/Linux

### Install dependencies

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS/Linux, activate the virtual environment with `source .venv/bin/activate`.

### Configure local environment

Create a `.env` file in the repository root (on Windows, run `notepad .env`). Generate a Django secret with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add the generated value and your chosen admin credentials to `.env`:

```dotenv
SECRET_KEY=<generated-secret>
DJANGO_DEBUG=True
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<unique-password-at-least-16-characters>
ADMIN_EMAIL=admin@localhost
```

Keep `.env` private. It is ignored by Git. Do not put secrets in source code or commit them to the repository.

### Initialize the database and start the app

```powershell
python manage.py migrate
python manage.py sync_env_admin
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser. Sign in at `/login/`. The custom admin dashboard is at `/hospital/admin/dashboard/`; Django's built-in admin is at `/admin/`.

`sync_env_admin` creates or updates a Django superuser using `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL`. The password must contain at least 16 characters. Run the command again after changing the admin credentials.

## Load sample hospitals and doctors

The repository includes a sample directory for Uttar Pradesh and a seed command that creates sample hospitals and fictional doctor profiles across the configured departments. Run this only if you want demo records in the database:

```powershell
python manage.py seed_up_hospitals --file .\up_hospitals_wise_name.json
```

The command can be rerun safely. Do not present the generated sample profiles as real doctors or use them to book real care.

## Optional integrations

### Razorpay test checkout

Payment is disabled when `APPOINTMENT_FEE` is blank. To enable a test checkout, add your Razorpay test credentials to `.env`:

```dotenv
APPOINTMENT_FEE=50
RAZORPAY_KEY_ID=rzp_test_<your-test-key-id>
RAZORPAY_KEY_SECRET=<your-test-key-secret>
```

Restart the development server after changing environment variables. Use Razorpay's test payment flow; do not scan a test QR code with a real UPI app. See [Razorpay test mode documentation](https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/gravity-forms/integration-steps//?preferred-country=IN).

### Hindi/English health chat

Add `GEMINI_API_KEY` to `.env` to enable AI-generated replies. The app defaults to the configured Gemini model in `hospital/views.py`; `GEMINI_MODEL` can override it. Without a key, the chat page remains available but cannot generate AI responses.

## Useful routes

| Page or endpoint | Path |
| --- | --- |
| Home | `/` |
| Login and registration | `/login/`, `/register/` |
| Patient dashboard | `/hospital/patient/dashboard/` |
| Book an appointment | `/hospital/patient/book-appointment/` |
| Patient appointments | `/hospital/patient/appointments/` |
| Doctor dashboard | `/hospital/doctor/dashboard/` |
| Admin dashboard | `/hospital/admin/dashboard/` |
| Django admin | `/admin/` |
| Doctor API | `/hospital/api/doctors/` |
| Health chat | `/health-chat/` |

## Deploy on Render

The project supports Render PostgreSQL through `DATABASE_URL`. Use a persistent PostgreSQL database for hosted data; files stored on a web service's local filesystem may not survive a redeploy. The local `.env` file is not uploaded to Render: configure environment variables in the Render service settings.

1. Push the repository to GitHub and create a Render PostgreSQL database and a Web Service connected to the repository.
2. Set the Render build command to `bash build.sh`.
3. Set the start command to:

   ```bash
   gunicorn Hospital_Management_System.wsgi:application --bind 0.0.0.0:$PORT
   ```

4. Configure these environment variables in the Render dashboard. Use Render's **Generate** option for `SECRET_KEY` and connect the web service to the database's internal URL as `DATABASE_URL`.

   ```text
   SECRET_KEY=<generated-secret>
   DJANGO_DEBUG=False
   DATABASE_URL=<Render PostgreSQL internal database URL>
   ADMIN_USERNAME=<admin-username>
   ADMIN_PASSWORD=<unique-password-at-least-16-characters>
   ADMIN_EMAIL=<admin-email>
   ```

   Add `APPOINTMENT_FEE`, `RAZORPAY_KEY_ID`, and `RAZORPAY_KEY_SECRET` only when test checkout is needed. Add `GEMINI_API_KEY` only when enabling the AI chat.
5. After the first successful deploy, use the service Shell to initialize the admin and, optionally, sample directory data:

   ```bash
   python manage.py sync_env_admin
   python manage.py seed_up_hospitals --file ./up_hospitals_wise_name.json
   ```

   Skip the seed command if you do not want fictional demo records. If using a custom domain, add its hostname to the `ALLOWED_HOSTS` environment variable as a comma-separated list.

## Project commands

```powershell
python manage.py check
python manage.py migrate
python manage.py sync_env_admin
python manage.py seed_up_hospitals --file .\up_hospitals_wise_name.json
python manage.py runserver
```

## Data and production note

This application handles patient-related information. Use fictional data while evaluating it. Before using it with real patients, arrange appropriate security, access controls, backups, privacy practices, and operational review for your organization. The included demo doctor records are not verified medical providers.
