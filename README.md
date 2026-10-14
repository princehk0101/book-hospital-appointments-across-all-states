# MeCare Hospital Management System

**Live demo:** [django-hospital-management-system.onrender.com](https://django-hospital-management-system.onrender.com)

A Django web application for managing hospital appointments, doctors, patients, and treatment records. It includes patient and doctor portals, a custom admin dashboard, bilingual department names, a Hindi/English health chat, downloadable appointment slips, and an optional Razorpay test payment flow.

> Hospital and doctor records loaded by the seed command are demo data. Doctor profiles are fictional and are not verified medical providers.

## Features

- Patient, doctor, and admin login with role based pages.
- Custom admin dashboard at `/hospital/admin/dashboard/` for appointments, doctors, and patients.
- Appointment booking by district, hospital, department, doctor, date, and time.
- Twenty departments shown in English and Hindi, such as **Dermatology — त्वचा रोग**.
- Appointment slip PDF after booking, or after successful payment when a fee is configured.
- Optional Razorpay checkout in test mode. The fee is controlled by `APPOINTMENT_FEE`; this repository does not set a live payment amount or accept live Razorpay keys.
- Hindi and English health chat. AI responses require an optional Gemini API key.

## Requirements

- Python 3.10 or newer
- PowerShell on Windows, or a shell of your choice

The default local database is SQLite (`db.sqlite3`). For deployment, the app supports PostgreSQL through `DATABASE_URL` (including Render PostgreSQL). The PostgreSQL driver and URL parser are included in `requirements.txt`.

## Local setup (Windows PowerShell)

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Only copy `.env.example` if `.env` does not already exist. Keep `.env` private; it is ignored by Git. Edit `.env` and replace all placeholder values before using optional integrations.

Minimum local settings:

```dotenv
SECRET_KEY=generate-a-long-random-django-secret
DJANGO_DEBUG=True
ADMIN_USERNAME=admin
ADMIN_PASSWORD=use-a-unique-password-at-least-16-characters-long
ADMIN_EMAIL=admin@localhost
```

Do not commit `.env`, real API keys, or passwords. `.env.example` contains placeholders only.

## Database and admin account

Apply the migrations and create or sync the custom admin account from `.env`:

```powershell
python manage.py migrate
python manage.py sync_env_admin
```

`ADMIN_PASSWORD` must be at least 16 characters. Running `sync_env_admin` updates the matching database account to the username and password currently in `.env`.

Start Django:

```powershell
python manage.py runserver
```

Open the login page at [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/), choose **Admin**, then enter `ADMIN_USERNAME` and `ADMIN_PASSWORD`. The custom dashboard is at [http://127.0.0.1:8000/hospital/admin/dashboard/](http://127.0.0.1:8000/hospital/admin/dashboard/). The standard Django admin is also available at `/admin/` for a superuser.

After changing `.env`, restart the Django server. If you changed the admin password, run `python manage.py sync_env_admin` again so the database password matches.

## Seed demo hospitals and doctors

The seed command reads the English source file `up_hospitals_wise_name.json` and its Hindi companion `hospital/data/up_hospitals_seed_hi.json`. It loads the district and hospital list, then makes all configured departments available at each seeded hospital with fictional demo doctor profiles.

```powershell
python manage.py seed_up_hospitals --file .\up_hospitals_wise_name.json
```

The command is safe to rerun. Seeded hospital and doctor records are marked as sample data; the names are for demonstration and must not be treated as real provider listings.

## Appointment booking

1. Register and sign in as a patient.
2. Open **Book Appointment** and choose a district, hospital, department, doctor, date, and time.
3. Appointments can be booked for tomorrow or a later date. A doctor cannot be booked twice for the same active time slot.
4. When `APPOINTMENT_FEE` is blank, the appointment is confirmed without payment and the slip PDF opens.
5. When `APPOINTMENT_FEE` is set to a positive amount, booking opens Razorpay checkout and the appointment is confirmed only after server-side payment verification.

## Optional Razorpay test payments

The checkout accepts **test keys only** (`RAZORPAY_KEY_ID` must start with `rzp_test_`). Keep the fee blank to turn payment off. To enable a test checkout, set these in the private `.env`:

```dotenv
APPOINTMENT_FEE=50
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
```

Restart Django after changing these values. Use a fresh appointment for each checkout attempt; closing or failing the payment window cancels that pending booking. In Razorpay test mode, choose Netbanking and use its mock success flow, or use `success@razorpay` if a UPI ID input is offered. Do not scan a QR code with a real UPI app for a test payment. [Razorpay test payment documentation](https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/gravity-forms/integration-steps//?preferred-country=IN)

## Optional health chat

Set `GEMINI_API_KEY` in `.env` to enable AI replies. The project defaults to `gemini-3.5-flash-lite`; `GEMINI_MODEL` can override it. Without an API key, the chat page remains available but explains that setup is required. Keep API keys private and follow the provider's quota and billing settings.

## Deploy on Render

The repository is configured to use Render PostgreSQL when Render provides `DATABASE_URL`. Do not use the default SQLite database for a hosted service: Render's web service filesystem is ephemeral, so SQLite data can disappear after a deploy or restart.

1. Push this repository to GitHub, including `build.sh`, migrations, and `up_hospitals_wise_name.json`. Never commit `.env`.
2. In Render, create a PostgreSQL database and a **Web Service** connected to this repository. Choose a PostgreSQL plan that fits the expected data lifetime; Render's free PostgreSQL database expires after 30 days.
3. Configure the web service:
   - **Build command:** `bash build.sh`
   - **Start command:** `gunicorn Hospital_Management_System.wsgi:application --bind 0.0.0.0:$PORT`
   - **Health check path:** `/login/`
4. Add these web service environment variables in Render. Use **Generate** for `SECRET_KEY`, and use the database's **Internal Database URL** for `DATABASE_URL` when both services are in the same Render region.

   ```text
   SECRET_KEY=<generate a unique secret in Render>
   DJANGO_DEBUG=False
   DATABASE_URL=<Render PostgreSQL Internal Database URL>
   ADMIN_USERNAME=<your admin username>
   ADMIN_PASSWORD=<a unique password of at least 16 characters>
   ADMIN_EMAIL=<your admin email>
   ```

   Set `APPOINTMENT_FEE`, `RAZORPAY_KEY_ID`, and `RAZORPAY_KEY_SECRET` only if you intend to enable checkout. The app currently accepts Razorpay test keys only; a public production site should not be treated as ready for live payments.
5. Deploy. From the Render service's **Shell**, run:

   ```bash
   python manage.py sync_env_admin
   python manage.py seed_up_hospitals --file ./up_hospitals_wise_name.json
   ```

   The first command creates/updates the custom dashboard admin from the service environment. The second inserts the fictional demo hospitals and doctors. Run it only if those demo records are wanted.
6. Open the service's `https://<service-name>.onrender.com/login/` URL and sign in using the admin environment variables. The custom admin dashboard is `/hospital/admin/dashboard/`.

Render assigns an `onrender.com` hostname, which is allowed by the default settings. If you attach a custom domain, add its hostname to the `ALLOWED_HOSTS` environment variable as a comma-separated list. For live patient data, use a persistent paid database and configure backups before launch.

## Useful commands

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py sync_env_admin
python manage.py seed_up_hospitals --file .\up_hospitals_wise_name.json
python manage.py runserver
```

## Notes

- Do not use demo doctor profiles for real patient care or real appointment operations.
- Do not put passwords or API secrets in `README.md`, `.env.example`, or source code.
- For deployment, set `SECRET_KEY`, `DJANGO_DEBUG=False`, database credentials, and allowed hosts appropriately; configure production security before accepting real users or payments.
