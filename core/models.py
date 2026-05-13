from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    whatsapp_number = models.CharField(max_length=32, blank=True)
    company_name = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} profile"


class Notifier(models.Model):
    FREQUENCY_HOURLY = "hourly"
    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_CHOICES = (
        (FREQUENCY_HOURLY, "Hourly"),
        (FREQUENCY_DAILY, "Daily"),
        (FREQUENCY_WEEKLY, "Weekly"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifiers")
    keyword = models.CharField(max_length=120)
    category = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=180)
    frequency = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, default=FREQUENCY_DAILY)
    max_pages = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["is_active", "next_run_at"]),
            models.Index(fields=["keyword", "location"]),
        ]

    def __str__(self):
        return f"{self.keyword} in {self.location}"


class Business(models.Model):
    notifier = models.ForeignKey(Notifier, on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=150, blank=True)
    sub_category = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=64, null=True, blank=True, unique=True)
    email = models.EmailField(null=True, blank=True, unique=True)
    website = models.URLField(max_length=500, blank=True)
    full_address = models.TextField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=80, blank=True)
    zip_code = models.CharField(max_length=32, blank=True)
    country = models.CharField(max_length=80, default="USA", blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    working_hours = models.JSONField(default=dict, blank=True)
    social_media_links = models.JSONField(default=list, blank=True)
    yellowpages_url = models.URLField(max_length=500, unique=True)
    logo_image = models.URLField(max_length=500, blank=True)
    source_keyword = models.CharField(max_length=120, blank=True)
    source_location = models.CharField(max_length=180, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-first_seen_at",)
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["city", "state"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(yellowpages_url__isnull=False) & ~Q(yellowpages_url=""),
                name="business_requires_yellowpages_url",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def google_maps_url(self):
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return f"https://www.google.com/maps/search/?api=1&query={self.full_address}"


class ScrapeLog(models.Model):
    STATUS_STARTED = "started"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_STARTED, "Started"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
    )

    notifier = models.ForeignKey(Notifier, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_STARTED)
    message = models.TextField(blank=True)
    pages_scraped = models.PositiveSmallIntegerField(default=0)
    businesses_found = models.PositiveIntegerField(default=0)
    new_businesses = models.PositiveIntegerField(default=0)
    error_details = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        return f"{self.get_status_display()} scrape at {self.started_at:%Y-%m-%d %H:%M}"


class YellowPagesCategory(models.Model):
    """Common Yellow Pages–style business categories (US & Canada)."""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class YellowPagesLocation(models.Model):
    """Geographic search strings suitable for YellowPages.com ``geo_location_terms`` (US & CA)."""

    class Country(models.TextChoices):
        US = "us", "United States"
        CA = "ca", "Canada"

    country = models.CharField(max_length=2, choices=Country.choices)
    geo_search = models.CharField(max_length=180)
    region_code = models.CharField(max_length=8, blank=True)

    class Meta:
        ordering = ("country", "geo_search")
        constraints = [
            models.UniqueConstraint(
                fields=("country", "geo_search"),
                name="uniq_yp_location_country_geo",
            ),
        ]
        indexes = [
            models.Index(fields=["country", "geo_search"]),
        ]

    def __str__(self):
        return self.geo_search
