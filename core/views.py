from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from .forms import NotifierForm, ProfileForm, RegisterForm
from .models import Business, Notifier, ScrapeLog
from .scraper import run_notifier_scrape
from .services import business_export_queryset, ensure_profile, export_businesses, next_run_for_frequency


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "register.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to LeadHarvester.")
        return response


class AppLoginView(LoginView):
    template_name = "login.html"


class AppLogoutView(LogoutView):
    pass


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_notifiers = Notifier.objects.filter(user=self.request.user)
        businesses = Business.objects.filter(Q(notifier__user=self.request.user) | Q(notifier__isnull=True)).distinct()
        context.update(
            {
                "total_notifiers": user_notifiers.count(),
                "total_businesses": businesses.count(),
                "recent_businesses": businesses[:8],
                "recent_logs": ScrapeLog.objects.filter(notifier__user=self.request.user)[:5],
                "notifiers": user_notifiers.annotate(business_count=Count("businesses"))[:8],
            }
        )
        return context


class ProfileView(LoginRequiredMixin, FormView):
    template_name = "profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = ensure_profile(self.request.user)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class NotifierCreateView(LoginRequiredMixin, CreateView):
    model = Notifier
    form_class = NotifierForm
    template_name = "notifier_form.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.next_run_at = next_run_for_frequency(form.instance.frequency)
        messages.success(self.request, "Notifier created.")
        return super().form_valid(form)


class NotifierUpdateView(LoginRequiredMixin, UpdateView):
    model = Notifier
    form_class = NotifierForm
    template_name = "notifier_form.html"
    success_url = reverse_lazy("dashboard")

    def get_queryset(self):
        return Notifier.objects.filter(user=self.request.user)

    def form_valid(self, form):
        form.instance.next_run_at = next_run_for_frequency(form.instance.frequency)
        messages.success(self.request, "Notifier updated.")
        return super().form_valid(form)


class RunNotifierView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notifier = get_object_or_404(Notifier, pk=pk, user=request.user)
        log = run_notifier_scrape(notifier)
        if log.status == ScrapeLog.STATUS_SUCCESS:
            messages.success(request, f"Scrape completed: {log.new_businesses} new businesses found.")
        else:
            messages.error(request, f"Scrape failed: {log.error_details}")
        return redirect("dashboard")


class BusinessListView(LoginRequiredMixin, ListView):
    model = Business
    template_name = "businesses.html"
    context_object_name = "businesses"
    paginate_by = 20

    def get_queryset(self):
        queryset = Business.objects.select_related("notifier").filter(Q(notifier__user=self.request.user) | Q(notifier__isnull=True))
        search = self.request.GET.get("q")
        keyword = self.request.GET.get("keyword")
        category = self.request.GET.get("category")
        location = self.request.GET.get("location")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(email__icontains=search)
                | Q(website__icontains=search)
            )
        if keyword:
            queryset = queryset.filter(source_keyword__icontains=keyword)
        if category:
            queryset = queryset.filter(Q(category__icontains=category) | Q(sub_category__icontains=category))
        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) | Q(state__icontains=location) | Q(full_address__icontains=location)
            )
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filters"] = self.request.GET
        return context


class BusinessDetailView(LoginRequiredMixin, DetailView):
    model = Business
    template_name = "business_detail.html"
    context_object_name = "business"

    def get_queryset(self):
        return Business.objects.filter(Q(notifier__user=self.request.user) | Q(notifier__isnull=True)).distinct()


class BusinessExportView(LoginRequiredMixin, View):
    def get(self, request, export_format):
        queryset = business_export_queryset(request).filter(Q(notifier__user=request.user) | Q(notifier__isnull=True)).distinct()
        return export_businesses(queryset, export_format)


class BusinessApiView(LoginRequiredMixin, View):
    def get(self, request):
        businesses = Business.objects.filter(Q(notifier__user=request.user) | Q(notifier__isnull=True)).order_by("-first_seen_at")[:100]
        return JsonResponse(
            {
                "results": [
                    {
                        "id": business.id,
                        "name": business.name,
                        "phone_number": business.phone_number,
                        "email": business.email,
                        "website": business.website,
                        "city": business.city,
                        "state": business.state,
                        "yellowpages_url": business.yellowpages_url,
                    }
                    for business in businesses
                ]
            }
        )


class NotifierApiView(LoginRequiredMixin, View):
    def get(self, request):
        notifiers = Notifier.objects.filter(user=request.user)
        return JsonResponse(
            {
                "results": [
                    {
                        "id": notifier.id,
                        "keyword": notifier.keyword,
                        "category": notifier.category,
                        "location": notifier.location,
                        "frequency": notifier.frequency,
                        "max_pages": notifier.max_pages,
                        "is_active": notifier.is_active,
                    }
                    for notifier in notifiers
                ]
            }
        )


class ScrapeRunApiView(LoginRequiredMixin, View):
    def post(self, request):
        notifier_id = request.POST.get("notifier_id")
        notifier = get_object_or_404(Notifier, pk=notifier_id, user=request.user)
        log = run_notifier_scrape(notifier)
        return JsonResponse(
            {
                "status": log.status,
                "pages_scraped": log.pages_scraped,
                "businesses_found": log.businesses_found,
                "new_businesses": log.new_businesses,
                "error_details": log.error_details,
            }
        )
