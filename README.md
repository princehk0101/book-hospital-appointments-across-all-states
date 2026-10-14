# 🏥 MeCare HMS

**MeCare** is a multi-hospital appointment booking platform built with Django. Patients can find a hospital and department, choose a doctor and appointment time, and keep their booking and treatment history in one place. The system also provides separate patient, doctor, and administrator dashboards, downloadable appointment slips, optional Razorpay test payments, and a Hindi/English health information chatbot.

**Live demo:** [django-hospital-management-system.onrender.com](https://django-hospital-management-system.onrender.com)

> ⚠️ **Health information disclaimer:** The chatbot provides general information only. It cannot diagnose conditions, prescribe treatment, or replace a qualified healthcare professional. Do not share personal or sensitive medical details in the chat. Chat messages are sent to Google Gemini when AI replies are enabled. For an emergency, contact local emergency services or go to the nearest emergency department.

> **Sample data notice:** Seeded hospitals and doctor profiles are fictional demo records. Verify hospital and provider information before using this system for real appointments.

---

## ✨ Features

### Patient

- Register and maintain a profile with contact and demographic details.
- Browse doctors and view doctor profiles.
- Book appointments through **District → Hospital → Department → Doctor → Date & Time**.
- Add symptoms, review appointment history, and cancel eligible bookings.
- View treatment history and download appointment slips as PDFs.
- Ask general health questions in Hindi or English through the optional AI chat.

### Doctor

- View today's appointments and assigned patient appointments.
- Review patient treatment history.
- Record diagnoses, prescriptions, and treatment notes.
- Manage availability and update profile details.

### Administrator

- See dashboard totals and appointment statuses.
- Add, edit, and remove doctor and patient records.
- Review and manage appointments.
- Search across records.

### Appointment and payment flow

- The booking form filters hospitals, departments, and doctors based on the selected location.
- Appointments can be booked for tomorrow or a later date.
- A doctor cannot have two active bookings for the same date and time.
- Payment is optional. If `APPOINTMENT_FEE` is blank, the appointment is booked without a payment step.
- If a fee is configured, Razorpay test checkout is used. The server verifies the payment before confirming the appointment.
- A PDF appointment slip is available after booking confirmation.

### AI health information chat

- Accepts Hindi (including Romanized Hindi) and English.
- Uses Google Gemini when `GEMINI_API_KEY` is configured.
- Limits each session to 15 messages per minute.
- Chat content is not saved to the application's database. When Gemini is enabled, messages are sent to Google to generate a reply.

---

## 🧰 Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Django |
| API | Django REST Framework |
| Frontend | Django templates, Bootstrap 5, JavaScript, Font Awesome |
| Local database | SQLite |
| Hosted database | PostgreSQL through `DATABASE_URL` |
| Static files and server | WhiteNoise, Gunicorn |
| Payments | Razorpay test mode |
| Health chat | Google Gemini API (optional) |

---

## 🚀 Getting started

### Requirements

- Python 3.10 or newer
- PowerShell on Windows, or a terminal on macOS/Linux

### 1. Clone the repository

```bash
git clone https://github.com/princehk0101/book-hospital-appointments-across-all-states.git
cd book-hospital-appointments-across-all-states
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the repository root (on Windows, run `notepad .env`). Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add the generated key and admin credentials to `.env`:

```dotenv
SECRET_KEY=<generated-secret-key>
DJANGO_DEBUG=True
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<unique-password-at-least-16-characters>
ADMIN_EMAIL=admin@localhost
```

Keep `.env` private. It is ignored by Git and must never be committed. For Render, configure these values in the service's Environment settings; the `.env` file on your computer is not uploaded to Render.

### 4. Create the database tables and admin account

```bash
python manage.py migrate
python manage.py sync_env_admin
```

`sync_env_admin` creates or updates the admin account using the `ADMIN_*` values. The password must be at least 16 characters. The same account can access the custom dashboard at `/hospital/admin/dashboard/` and Django admin at `/admin/`.

### 5. Load sample hospitals and doctors (optional)

The repository includes a sample Uttar Pradesh hospital directory and fictional doctors. To load it into your local database, run:

```bash
python manage.py seed_up_hospitals --file ./up_hospitals_wise_name.json
```

The command can be safely rerun. Skip it if you do not want demo records.

### 6. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

---

## 🔄 Booking flow

1. A patient registers and signs in.
2. The patient selects a district, hospital, department, and doctor.
3. The patient chooses a date and time and can add symptoms.
4. If payment is disabled, the appointment is confirmed without checkout. If a fee is configured, the patient completes Razorpay test checkout.
5. The server verifies a test payment before marking the appointment as paid and confirmed.
6. The patient can view the appointment and download its PDF slip.

## 💳 Optional Razorpay test checkout

Payments are disabled when `APPOINTMENT_FEE` is blank. To enable test checkout, add your Razorpay **test** credentials to `.env`:

```dotenv
APPOINTMENT_FEE=50
RAZORPAY_KEY_ID=rzp_test_<your-test-key-id>
RAZORPAY_KEY_SECRET=<your-test-key-secret>
```

Restart the server after changing `.env`. The app rejects live Razorpay keys; this repository is not configured to accept live payments. Use Razorpay's test flow, and do not scan a test QR code with a real UPI app. See [Razorpay test payment documentation](https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/gravity-forms/integration-steps//?preferred-country=IN).

## 🤖 Optional Hindi/English health chat

Add a Gemini API key to `.env` to enable AI-generated replies:

```dotenv
GEMINI_API_KEY=<your-gemini-api-key>
```

The model can be overridden with `GEMINI_MODEL`; otherwise, the application uses its configured default. Chat content is sent to Google Gemini to generate answers and is not saved to the application's database. Do not share personally identifying or sensitive health information in the chat.

---

## 🗂️ Project structure

```text
Hospital_Management_System/   Django project settings and URL configuration
accounts/                     Authentication, profiles, and public pages
hospital/                     Hospital workflows, models, views, and APIs
  data/                       Hindi hospital seed data
  management/commands/        Admin sync and sample data commands
  migrations/                 Database schema migrations
  templates/                  Patient, doctor, and admin pages
static/                       CSS and JavaScript assets
up_hospitals_wise_name.json   Hospital seed source data
build.sh                      Render build script
start.sh                      Gunicorn start script
manage.py                     Django management entry point
```

## 🔗 Useful routes

| Page | Path |
| --- | --- |
| Home | `/` |
| Login / registration | `/login/` · `/register/` |
| Patient dashboard | `/hospital/patient/dashboard/` |
| Book appointment | `/hospital/patient/book-appointment/` |
| Doctor dashboard | `/hospital/doctor/dashboard/` |
| Admin dashboard | `/hospital/admin/dashboard/` |
| Django admin | `/admin/` |
| Health chat | `/health-chat/` |
| Doctor API | `/hospital/api/doctors/` |

---

## ☁️ Deploy on Render

The application reads a PostgreSQL connection string from `DATABASE_URL`. Use a persistent PostgreSQL database for hosted data; the local `.env` file is not available to the Render service.

1. Connect this GitHub repository to a Render Web Service and create or select a PostgreSQL database.
2. Set the **Build Command** to `bash build.sh`.
3. Set the **Start Command** to:

   ```bash
   gunicorn Hospital_Management_System.wsgi:application --bind 0.0.0.0:$PORT
   ```

4. Add these environment variables in Render. Use Render's **Generate** option for `SECRET_KEY` and set `DATABASE_URL` to the database's internal URL.

   ```text
   SECRET_KEY=<generated-secret-key>
   DJANGO_DEBUG=False
   DATABASE_URL=<Render PostgreSQL internal URL>
   ADMIN_USERNAME=<admin-username>
   ADMIN_PASSWORD=<unique-password-at-least-16-characters>
   ADMIN_EMAIL=<admin-email>
   ```

   Add `APPOINTMENT_FEE`, Razorpay test keys, or `GEMINI_API_KEY` only if you need those integrations.
5. The build script applies migrations and loads the bundled sample district/hospital directory and fictional demo doctors. It is safe to rerun during later builds. For a custom domain, set its hostname in `ALLOWED_HOSTS` as a comma-separated value.

---

## 🛠️ Troubleshooting

| Problem | What to check |
| --- | --- |
| Admin setup fails | Ensure `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set; password must be at least 16 characters. |
| Chat says the Gemini key is missing | Set `GEMINI_API_KEY` locally or in the Render Environment settings, then restart/redeploy. |
| Chat returns a rate limit response | The session has reached 15 messages in one minute; wait and try again. |
| Payment cannot start | Check that `APPOINTMENT_FEE` is positive and both Razorpay test credentials are set. |
| Payment is no longer pending | Start a new appointment checkout; failed or closed attempts cannot be resumed. |
| Static files are missing on Render | Confirm the build ran `collectstatic` and inspect the deploy logs. |
| Database is empty after deploy | Verify that `DATABASE_URL` points to the intended persistent database. |

## 🔒 Security and data notes

- Keep `.env`, database URLs, passwords, and API keys out of Git.
- State-changing actions use authenticated views and CSRF protection.
- Razorpay payment status is verified server-side; only test keys are accepted.
- The chatbot is rate limited, but its prompts are sent to Google when Gemini is enabled.
- Use fictional records while evaluating the application. Before using real patient information, arrange suitable privacy, access control, backup, and security practices.
- Seeded doctor profiles are fictional and are not verified medical providers.
