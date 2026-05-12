from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Notifier, UserProfile


class BootstrapFormMixin:
    def _apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
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
    class Meta:
        model = Notifier
        fields = ("keyword", "category", "location", "frequency", "max_pages", "is_active")
        widgets = {
            "max_pages": forms.NumberInput(attrs={"min": 1, "max": 25}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
