from django.contrib import admin

from .models import Business, Notifier, ScrapeLog, UserProfile, YellowPagesCategory, YellowPagesLocation


@admin.register(YellowPagesCategory)
class YellowPagesCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(YellowPagesLocation)
class YellowPagesLocationAdmin(admin.ModelAdmin):
    list_display = ("geo_search", "country", "region_code")
    list_filter = ("country", "region_code")
    search_fields = ("geo_search", "region_code")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "whatsapp_number", "company_name", "created_at")
    search_fields = ("user__username", "user__email", "whatsapp_number", "company_name")


@admin.register(Notifier)
class NotifierAdmin(admin.ModelAdmin):
    list_display = ("keyword", "category", "location", "frequency", "max_pages", "is_active", "user", "last_run_at")
    list_filter = ("frequency", "is_active", "created_at")
    search_fields = ("keyword", "category", "location", "user__username")
    date_hierarchy = "created_at"


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "state", "phone_number", "email", "rating", "first_seen_at")
    list_filter = ("category", "state", "country", "first_seen_at")
    search_fields = ("name", "phone_number", "email", "website", "full_address", "yellowpages_url")
    readonly_fields = ("first_seen_at", "updated_at")
    date_hierarchy = "first_seen_at"


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ("notifier", "status", "pages_scraped", "businesses_found", "new_businesses", "started_at", "completed_at")
    list_filter = ("status", "started_at")
    search_fields = ("notifier__keyword", "notifier__location", "message", "error_details")
    readonly_fields = ("started_at", "completed_at")
