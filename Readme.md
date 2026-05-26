# Hostify  
### End-to-End Event Management & Ticketing Platform

Hostify is a Django-based event management platform where organizers can create and manage events, attendees can book tickets, and communities can interact seamlessly.

---

# Features

- User Authentication & Role Management
- Event Creation & Management
- Ticket Booking System
- Dashboard for Organizers
- AI Services Integration (Groq)
- Razorpay Payment Integration
- Cloudinary Media Storage
- Tailwind CSS UI
- PostgreSQL Database Support (Neon)
- Production Deployment on Render

---

# Tech Stack

## Backend
- Django
- PostgreSQL (Neon)
- Gunicorn

## Frontend
- HTML
- Tailwind CSS
- Crispy Forms
- Crispy Tailwind

## Cloud & APIs
- Render
- Neon PostgreSQL
- Cloudinary
- Razorpay
- Groq AI

---

# 📁 Project Structure

```bash
Hostify/
│
├── Hostify/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│
├── accounts/
├── events/
├── tickets/
├── dashboard/
├── community/
├── payments/
├── ai_services/
│
├── templates/
├── static/
├── staticfiles/
│
├── manage.py
├── requirements.txt
├── build.sh
└── .env
```

---

# ⚙️ Local Development Setup

## 1️⃣ Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Hostify.git

cd Hostify
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=your-secret-key

DEBUG=True

ALLOWED_HOSTS=127.0.0.1,localhost

DATABASE_URL=your-neon-postgres-url

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Razorpay
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

# Groq
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Email
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@hostify.com
```

---

# 🐘 Neon PostgreSQL Setup

## 1️⃣ Create Neon Database

Go to:

```text
https://neon.tech
```

Create a project and copy the PostgreSQL connection URL.

Example:

```env
DATABASE_URL=postgresql://username:password@host.neon.tech/neondb?sslmode=require
```

---

## 2️⃣ Install PostgreSQL Packages

```bash
pip install psycopg2-binary dj-database-url
```

---

## 3️⃣ Update `settings.py`

```python
import dj_database_url

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True
    )
}
```

---

# 🧱 Database Migration

Run:

```bash
python manage.py migrate
```

Create superuser:

```bash
python manage.py createsuperuser
```

---

# ▶️ Run Development Server

```bash
python manage.py runserver
```

Visit:

```text
http://127.0.0.1:8000
```

---

# ☁️ Deploying on Render

---

## 1️⃣ Install Gunicorn

```bash
pip install gunicorn
```

Update requirements:

```bash
pip freeze > requirements.txt
```

---

## 2️⃣ Production Settings

Update `settings.py`

### DEBUG

```python
DEBUG = env.bool("DEBUG", default=False)
```

### ALLOWED_HOSTS

```python
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["127.0.0.1"]
)
```

### CSRF Trusted Origins

```python
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[]
)
```

### WhiteNoise Middleware

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

---

## 3️⃣ Create `build.sh`

Create `build.sh`

```bash
#!/usr/bin/env bash

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate
```

---

## 4️⃣ Push to GitHub

```bash
git init

git add .

git commit -m "Initial deployment"

git remote add origin YOUR_GITHUB_REPO

git push -u origin main
```

---

## 5️⃣ Create Render Web Service

Go to:

```text
https://render.com
```

Create:

```text
New → Web Service
```

Connect GitHub repository.

---

## 6️⃣ Render Configuration

### Build Command

```bash
chmod +x build.sh && ./build.sh
```

### Start Command

```bash
gunicorn Hostify.wsgi:application
```

---

## 7️⃣ Add Environment Variables in Render

Render Dashboard → Environment

Add:

```env
SECRET_KEY=
DEBUG=False

DATABASE_URL=

ALLOWED_HOSTS=your-render-url.onrender.com

CSRF_TRUSTED_ORIGINS=https://your-render-url.onrender.com

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Razorpay
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

# Groq
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Email
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
```

---

# 🌐 Deployment URL

After deployment:

```text
https://your-project.onrender.com
```

---

# 🧾 Useful Commands

## Collect Static Files

```bash
python manage.py collectstatic
```

## Create Migrations

```bash
python manage.py makemigrations
```

## Apply Migrations

```bash
python manage.py migrate
```

## Create Admin User

```bash
python manage.py createsuperuser
```

---

# 🐛 Common Deployment Errors

## Bad Request (400)

Fix:

```env
ALLOWED_HOSTS=your-render-url.onrender.com

CSRF_TRUSTED_ORIGINS=https://your-render-url.onrender.com
```

---

## Static Files Not Loading

Ensure:

```python
STATIC_ROOT = BASE_DIR / "staticfiles"
```

---

## ModuleNotFoundError

Run:

```bash
pip freeze > requirements.txt
```

Commit and redeploy.

---

# 📜 License

This project is licensed under the MIT License.

---

# ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.