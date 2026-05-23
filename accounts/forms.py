from django import forms
from django.contrib.auth import get_user_model
from .models import AttendeeProfile, OrganizerProfile

User = get_user_model()


class RegisterForm(forms.ModelForm):
    
    password  = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model  = User
        fields = ["first_name", "last_name", "email", "photo", "role"]

    def clean(self):
        cd = super().clean()
        if cd.get("password") != cd.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cd

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ["first_name", "last_name", "email", "bio", "photo", "role"]


class AttendeeProfileForm(forms.ModelForm):
    class Meta:
        model  = AttendeeProfile
        fields = ["interests", "expertise", "linkedin", "twitter", "github", "website"]


class OrganizerProfileForm(forms.ModelForm):
    class Meta:
        model  = OrganizerProfile
        fields = ["display_name", "org_type", "description",
                  "contact_phone", "contact_email", "website", "logo"]