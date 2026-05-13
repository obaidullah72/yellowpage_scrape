from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Notifier, UserProfile, YellowPagesCategory, YellowPagesLocation


class BootstrapFormMixin:
    def _apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    whatsapp_number = forms.CharField(required=False, max_length=32)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "whatsapp_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"whatsapp_number": self.cleaned_data.get("whatsapp_number", "")},
            )
        return user


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ("company_name", "whatsapp_number")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
        self._apply_bootstrap_classes()

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data["first_name"]
            self.user.last_name = self.cleaned_data["last_name"]
            self.user.email = self.cleaned_data["email"]
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class NotifierForm(BootstrapFormMixin, forms.ModelForm):
    category = forms.ChoiceField(
        required=False,
        help_text="Pulled from your seeded Yellow Pages category catalog.",
    )
    location = forms.ChoiceField(
        help_text="Pulled from your seeded US/CA location catalog.",
    )

    class Meta:
        model = Notifier
        fields = ("keyword", "category", "location", "frequency", "max_pages", "is_active")
        widgets = {
            "keyword": forms.TextInput(
                attrs={
                    "placeholder": "e.g. car wash, electricians, pizza…",
                    "autocomplete": "off",
                }
            ),
            "max_pages": forms.NumberInput(attrs={"min": 1, "max": 25}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()
        kw_classes = self.fields["keyword"].widget.attrs.get("class", "")
        self.fields["keyword"].widget.attrs["class"] = f"{kw_classes} form-control-lg lh-nf-keyword".strip()
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
        self.fields["is_active"].widget.attrs.setdefault("role", "switch")

        names = list(YellowPagesCategory.objects.order_by("name").values_list("name", flat=True))
        cat_choices = [("", "— Select category (optional) —")]
        current_cat = (self.instance.pk and self.instance.category) or ""
        if current_cat and current_cat not in names:
            cat_choices.append((current_cat, f"{current_cat} (custom)"))
        cat_choices.extend((n, n) for n in names)
        self.fields["category"].choices = cat_choices

        geos = list(
            YellowPagesLocation.objects.order_by("country", "geo_search").values_list(
                "geo_search", flat=True
            )
        )
        loc_choices = [("", "— Select location —")]
        current_loc = (self.instance.pk and self.instance.location) or ""
        if current_loc and current_loc not in geos:
            loc_choices.append((current_loc, f"{current_loc} (custom)"))
        loc_choices.extend((g, g) for g in geos)
        self.fields["location"].choices = loc_choices
