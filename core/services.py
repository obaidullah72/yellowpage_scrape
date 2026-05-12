import csv
import io
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from .models import Business, Notifier

logger = logging.getLogger(__name__)


def ensure_profile(user):
    from .models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def next_run_for_frequency(frequency, from_time=None):
    base = from_time or timezone.now()
    intervals = {
        Notifier.FREQUENCY_HOURLY: timedelta(hours=1),
        Notifier.FREQUENCY_DAILY: timedelta(days=1),
        Notifier.FREQUENCY_WEEKLY: timedelta(weeks=1),
    }
    return base + intervals.get(frequency, timedelta(hours=1))


def send_whatsapp(to_number, message):
    if not to_number:
        logger.info("Skipping WhatsApp message because recipient is missing")
        return None

    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
        logger.warning("Skipping WhatsApp message because Twilio settings are incomplete")
        return None

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        return client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number,
        )
    except TwilioRestException:
        logger.exception("Twilio WhatsApp delivery failed")
        return None


def notify_user(user, message):
    profile = ensure_profile(user)
    return send_whatsapp(profile.whatsapp_number, message)


def business_export_queryset(request):
    queryset = Business.objects.select_related("notifier")
    keyword = request.GET.get("keyword")
    category = request.GET.get("category")
    location = request.GET.get("location")

    if keyword:
        queryset = queryset.filter(source_keyword__icontains=keyword) | queryset.filter(name__icontains=keyword)
    if category:
        queryset = queryset.filter(category__icontains=category)
    if location:
        queryset = queryset.filter(city__icontains=location) | queryset.filter(state__icontains=location) | queryset.filter(
            full_address__icontains=location
        )
    return queryset.distinct()


EXPORT_FIELDS = [
    "name",
    "category",
    "sub_category",
    "phone_number",
    "email",
    "website",
    "full_address",
    "city",
    "state",
    "zip_code",
    "country",
    "latitude",
    "longitude",
    "rating",
    "review_count",
    "description",
    "yellowpages_url",
    "logo_image",
    "source_keyword",
    "source_location",
]


def serialize_business(business):
    data = {field: getattr(business, field) for field in EXPORT_FIELDS}
    data["working_hours"] = business.working_hours
    data["social_media_links"] = business.social_media_links
    return data


def export_businesses(queryset, export_format):
    filename = f"businesses.{export_format}"
    if export_format == "json":
        payload = [serialize_business(business) for business in queryset]
        response = HttpResponse(json.dumps(payload, default=str, indent=2), content_type="application/json")
    elif export_format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Businesses"
        headers = EXPORT_FIELDS + ["working_hours", "social_media_links"]
        sheet.append(headers)
        for business in queryset:
            row = [getattr(business, field) for field in EXPORT_FIELDS]
            row.extend([json.dumps(business.working_hours), json.dumps(business.social_media_links)])
            sheet.append(row)
        buffer = io.BytesIO()
        workbook.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        export_format = "csv"
        filename = "businesses.csv"
        response = HttpResponse(content_type="text/csv")
        writer = csv.writer(response)
        headers = EXPORT_FIELDS + ["working_hours", "social_media_links"]
        writer.writerow(headers)
        for business in queryset:
            row = [getattr(business, field) for field in EXPORT_FIELDS]
            row.extend([json.dumps(business.working_hours), json.dumps(business.social_media_links)])
            writer.writerow(row)

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
