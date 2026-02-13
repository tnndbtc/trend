"""
Forms for user authentication and preference management (Phase 2).
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models_preferences import UserPreference, UserNotificationPreference


class UserRegistrationForm(UserCreationForm):
    """Extended user registration form with email."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email address'
        })
    )

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name (optional)'
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name (optional)'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm password'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')

        if commit:
            user.save()
            # Create default preference profile
            UserPreference.objects.create(
                user=user,
                name='Default',
                description='Your default preference profile',
                is_default=True
            )
            # Create notification preferences
            UserNotificationPreference.objects.create(user=user)

        return user


class UserLoginForm(AuthenticationForm):
    """Custom login form with styling."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username',
            'autofocus': True
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password'
        })
    )


class PreferenceProfileForm(forms.ModelForm):
    """Form for creating/editing preference profiles."""

    class Meta:
        model = UserPreference
        fields = [
            'name',
            'description',
            'is_default',
            'sources',
            'languages',
            'categories',
            'time_range',
            'custom_start_date',
            'custom_end_date',
            'keywords_include',
            'keywords_exclude',
            'min_upvotes',
            'min_comments',
            'min_score',
            'sort_by',
            'sort_order',
            'items_per_page',
            'view_mode',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Profile name (e.g., "Work", "AI Research")'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Optional description',
                'rows': 3
            }),
            'sources': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'languages': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'time_range': forms.Select(attrs={'class': 'form-select'}),
            'custom_start_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'custom_end_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'keywords_include': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Comma-separated keywords to include'
            }),
            'keywords_exclude': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Comma-separated keywords to exclude'
            }),
            'min_upvotes': forms.NumberInput(attrs={'class': 'form-input'}),
            'min_comments': forms.NumberInput(attrs={'class': 'form-input'}),
            'min_score': forms.NumberInput(attrs={'class': 'form-input'}),
            'sort_by': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.Select(attrs={'class': 'form-select'}),
            'items_per_page': forms.NumberInput(attrs={'class': 'form-input'}),
            'view_mode': forms.Select(attrs={'class': 'form-select'}),
        }


class SaveCurrentPreferencesForm(forms.Form):
    """Form for saving current session preferences as a new profile."""

    profile_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Profile name (e.g., "My AI Feed")'
        })
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'placeholder': 'Optional description',
            'rows': 2
        })
    )

    set_as_default = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )


class NotificationPreferenceForm(forms.ModelForm):
    """Form for managing notification preferences."""

    class Meta:
        model = UserNotificationPreference
        fields = [
            'email_enabled',
            'email_frequency',
            'push_enabled',
            'min_trend_score',
            'min_topic_count',
        ]
        widgets = {
            'email_enabled': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'email_frequency': forms.Select(attrs={'class': 'form-select'}),
            'push_enabled': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'min_trend_score': forms.NumberInput(attrs={'class': 'form-input'}),
            'min_topic_count': forms.NumberInput(attrs={'class': 'form-input'}),
        }
