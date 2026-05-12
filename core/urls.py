from django.urls import path

from .views import (
    AppLoginView,
    AppLogoutView,
    BusinessApiView,
    BusinessDetailView,
    BusinessExportView,
    BusinessListView,
    DashboardView,
    NotifierApiView,
    NotifierCreateView,
    NotifierUpdateView,
    ProfileView,
    RegisterView,
    RunNotifierView,
    ScrapeRunApiView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", AppLoginView.as_view(), name="login"),
    path("logout/", AppLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("notifiers/new/", NotifierCreateView.as_view(), name="notifier_create"),
    path("notifiers/<int:pk>/edit/", NotifierUpdateView.as_view(), name="notifier_update"),
    path("notifiers/<int:pk>/run/", RunNotifierView.as_view(), name="notifier_run"),
    path("businesses/", BusinessListView.as_view(), name="business_list"),
    path("businesses/<int:pk>/", BusinessDetailView.as_view(), name="business_detail"),
    path("businesses/export/<str:export_format>/", BusinessExportView.as_view(), name="business_export"),
    path("api/businesses/", BusinessApiView.as_view(), name="api_businesses"),
    path("api/notifiers/", NotifierApiView.as_view(), name="api_notifiers"),
    path("api/scrape/run/", ScrapeRunApiView.as_view(), name="api_scrape_run"),
]
