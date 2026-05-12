# LeadHarvester

LeadHarvester is a single-app Django web application for creating YellowPages lead notifiers, scraping business data, exporting results, and sending WhatsApp alerts through Twilio.

## Tech Stack

- Django with Django Templates
- PostgreSQL
- BeautifulSoup4 and Requests
- APScheduler
- Twilio WhatsApp API
- python-dotenv
- Bootstrap 5

## Project Structure

```text
.
├── core/
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── scraper.py
│   ├── services.py
│   ├── tasks.py
│   ├── urls.py
│   └── views.py
├── leadharvester/
│   ├── settings.py
│   └── urls.py
├── templates/
├── static/
├── media/
├── manage.py
├── requirements.txt
└── .env.example
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv env
source env/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Update `.env` with your local PostgreSQL and Twilio values:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/leadharvester

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## Database

Create the PostgreSQL database:

```bash
createdb leadharvester
```

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

## Run The App

Start the development server:

```bash
python manage.py runserver
```

Open the app at `http://127.0.0.1:8000/`.

## Scheduler

Run the scraper scheduler in a separate terminal:

```bash
python manage.py run_scheduler
```

The scheduler checks for due notifiers every 30 minutes. You can also enable scheduler startup inside Django by setting:

```env
RUN_SCHEDULER=True
```

## Features

- Register, login, logout, and profile management
- Dashboard with notifier and scraped business totals
- YellowPages notifiers by keyword, category, location, frequency, and max pages
- Business list with search, filters, pagination, and detail pages
- CSV, Excel, and JSON exports
- Admin management for notifiers, businesses, logs, and profiles
- WhatsApp alerts for new leads, completed scrapes, and scraper errors
- Simple authenticated JSON endpoints under `/api/`

## Notes

Scraping public websites can trigger rate limits or anti-bot protections. Keep delays conservative, avoid aggressive page counts, and review YellowPages terms before running high-volume jobs.
