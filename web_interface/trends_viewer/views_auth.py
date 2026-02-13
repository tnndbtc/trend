"""
Authentication and user profile management views (Phase 2).

Handles user registration, login, logout, and preference profile management.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    PreferenceProfileForm,
    SaveCurrentPreferencesForm,
    NotificationPreferenceForm,
)
from .models_preferences import (
    UserPreference,
    UserPreferenceHistory,
    UserNotificationPreference,
)
from .preferences import PreferenceManager

logger = logging.getLogger(__name__)


# ============================================================================
# Authentication Views
# ============================================================================

def register_view(request: HttpRequest):
    """
    User registration view.

    Creates new user account and default preference profile.
    """
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('trends_viewer:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in
            login(request, user)

            # Create history entry
            _create_history_entry(
                request,
                user,
                None,
                'created',
                {'message': 'User account created'}
            )

            messages.success(
                request,
                f'Welcome {user.username}! Your account has been created successfully.'
            )
            return redirect('trends_viewer:user_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()

    return render(request, 'trends_viewer/auth/register.html', {'form': form})


def login_view(request: HttpRequest):
    """User login view."""
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('trends_viewer:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)

                # Load user's default preference into session
                _load_default_preference_to_session(request, user)

                messages.success(request, f'Welcome back, {user.username}!')

                # Redirect to next parameter or dashboard
                next_url = request.GET.get('next', 'trends_viewer:dashboard')
                return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'trends_viewer/auth/login.html', {'form': form})


@login_required
def logout_view(request: HttpRequest):
    """User logout view."""
    username = request.user.username
    logout(request)
    messages.success(request, f'Goodbye, {username}! You have been logged out.')
    return redirect('trends_viewer:dashboard')


# ============================================================================
# Profile Management Views
# ============================================================================

@login_required
def user_profile_view(request: HttpRequest):
    """
    User profile dashboard.

    Displays user's saved preference profiles and account settings.
    """
    user = request.user

    # Get all preference profiles for this user
    profiles = UserPreference.objects.filter(user=user)

    # Get notification preferences
    notification_prefs, _ = UserNotificationPreference.objects.get_or_create(user=user)

    # Get recent preference history
    recent_history = UserPreferenceHistory.objects.filter(user=user)[:10]

    context = {
        'profiles': profiles,
        'notification_prefs': notification_prefs,
        'recent_history': recent_history,
    }

    return render(request, 'trends_viewer/profile/dashboard.html', context)


@login_required
def create_preference_profile(request: HttpRequest):
    """Create a new preference profile."""
    if request.method == 'POST':
        form = PreferenceProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            # Create history entry
            _create_history_entry(
                request,
                request.user,
                profile,
                'created',
                profile.to_dict()
            )

            messages.success(
                request,
                f'Preference profile "{profile.name}" created successfully.'
            )
            return redirect('trends_viewer:user_profile')
    else:
        form = PreferenceProfileForm()

    return render(request, 'trends_viewer/profile/create_profile.html', {'form': form})


@login_required
def edit_preference_profile(request: HttpRequest, profile_id: int):
    """Edit an existing preference profile."""
    profile = get_object_or_404(
        UserPreference,
        id=profile_id,
        user=request.user
    )

    if request.method == 'POST':
        form = PreferenceProfileForm(request.POST, instance=profile)
        if form.is_valid():
            old_data = profile.to_dict()
            form.save()

            # Create history entry
            _create_history_entry(
                request,
                request.user,
                profile,
                'updated',
                profile.to_dict()
            )

            messages.success(
                request,
                f'Preference profile "{profile.name}" updated successfully.'
            )
            return redirect('trends_viewer:user_profile')
    else:
        form = PreferenceProfileForm(instance=profile)

    return render(
        request,
        'trends_viewer/profile/edit_profile.html',
        {'form': form, 'profile': profile}
    )


@login_required
def delete_preference_profile(request: HttpRequest, profile_id: int):
    """Delete a preference profile."""
    profile = get_object_or_404(
        UserPreference,
        id=profile_id,
        user=request.user
    )

    # Don't allow deleting the last profile
    if UserPreference.objects.filter(user=request.user).count() == 1:
        messages.error(
            request,
            'Cannot delete your only preference profile. Create another one first.'
        )
        return redirect('trends_viewer:user_profile')

    if request.method == 'POST':
        profile_name = profile.name

        # Create history entry before deletion
        _create_history_entry(
            request,
            request.user,
            None,
            'deleted',
            {'name': profile_name, 'data': profile.to_dict()}
        )

        profile.delete()

        messages.success(
            request,
            f'Preference profile "{profile_name}" deleted successfully.'
        )
        return redirect('trends_viewer:user_profile')

    return render(
        request,
        'trends_viewer/profile/delete_confirm.html',
        {'profile': profile}
    )


@login_required
def activate_preference_profile(request: HttpRequest, profile_id: int):
    """
    Activate a saved preference profile.

    Loads the profile's settings into the session.
    """
    profile = get_object_or_404(
        UserPreference,
        id=profile_id,
        user=request.user
    )

    # Load profile into session
    pref_manager = PreferenceManager(request)
    pref_manager.update_preferences(profile.to_dict())

    # Mark profile as used
    profile.mark_as_used()

    # Create history entry
    _create_history_entry(
        request,
        request.user,
        profile,
        'activated',
        profile.to_dict()
    )

    messages.success(
        request,
        f'Preference profile "{profile.name}" activated.'
    )

    # Redirect to filtered view
    redirect_url = request.GET.get('next', 'trends_viewer:filtered_trends')
    return redirect(redirect_url)


@login_required
def save_current_preferences(request: HttpRequest):
    """
    Save current session preferences as a new profile.

    Allows users to save their current filter settings.
    """
    if request.method == 'POST':
        form = SaveCurrentPreferencesForm(request.POST)
        if form.is_valid():
            # Get current preferences from session
            pref_manager = PreferenceManager(request)
            current_prefs = pref_manager.get_preferences()

            # Create new profile
            profile = UserPreference.from_dict(
                user=request.user,
                name=form.cleaned_data['profile_name'],
                prefs_dict=current_prefs,
                description=form.cleaned_data.get('description', ''),
                is_default=form.cleaned_data.get('set_as_default', False)
            )

            # Create history entry
            _create_history_entry(
                request,
                request.user,
                profile,
                'created',
                profile.to_dict()
            )

            messages.success(
                request,
                f'Current preferences saved as "{profile.name}".'
            )
            return redirect('trends_viewer:user_profile')
    else:
        form = SaveCurrentPreferencesForm()

    # Get current preferences for preview
    pref_manager = PreferenceManager(request)
    current_prefs = pref_manager.get_preferences()

    return render(
        request,
        'trends_viewer/profile/save_current.html',
        {'form': form, 'current_prefs': current_prefs}
    )


@login_required
def set_default_profile(request: HttpRequest, profile_id: int):
    """Set a profile as the default."""
    profile = get_object_or_404(
        UserPreference,
        id=profile_id,
        user=request.user
    )

    # Set as default (model automatically unsets others)
    profile.is_default = True
    profile.save()

    messages.success(
        request,
        f'"{profile.name}" is now your default preference profile.'
    )

    return redirect('trends_viewer:user_profile')


@login_required
def manage_notifications(request: HttpRequest):
    """Manage notification preferences."""
    notification_prefs, _ = UserNotificationPreference.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=notification_prefs)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated.')
            return redirect('trends_viewer:user_profile')
    else:
        form = NotificationPreferenceForm(instance=notification_prefs)

    return render(
        request,
        'trends_viewer/profile/notifications.html',
        {'form': form}
    )


# ============================================================================
# AJAX Endpoints
# ============================================================================

@login_required
@require_http_methods(["POST"])
def quick_save_profile_ajax(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to quickly save current preferences.

    Used for "Save as..." button in filter panel.
    """
    try:
        profile_name = request.POST.get('name')
        if not profile_name:
            return JsonResponse({'error': 'Profile name required'}, status=400)

        # Check if profile name already exists
        if UserPreference.objects.filter(
            user=request.user,
            name=profile_name
        ).exists():
            return JsonResponse(
                {'error': f'Profile "{profile_name}" already exists'},
                status=400
            )

        # Get current preferences from session
        pref_manager = PreferenceManager(request)
        current_prefs = pref_manager.get_preferences()

        # Create profile
        profile = UserPreference.from_dict(
            user=request.user,
            name=profile_name,
            prefs_dict=current_prefs,
            description='Quick-saved from filter panel'
        )

        # Create history entry
        _create_history_entry(
            request,
            request.user,
            profile,
            'created',
            profile.to_dict()
        )

        return JsonResponse({
            'success': True,
            'message': f'Saved as "{profile_name}"',
            'profile_id': profile.id
        })

    except Exception as e:
        logger.error(f'Quick save failed: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_user_profiles_ajax(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to get list of user's profiles.

    Used for profile selector dropdown.
    """
    profiles = UserPreference.objects.filter(user=request.user).values(
        'id', 'name', 'description', 'is_default', 'last_used'
    )

    return JsonResponse({
        'success': True,
        'profiles': list(profiles)
    })


# ============================================================================
# Helper Functions
# ============================================================================

def _create_history_entry(
    request: HttpRequest,
    user,
    profile,
    action: str,
    snapshot: dict
):
    """Create a preference history entry."""
    try:
        # Get IP address
        ip_address = request.META.get('REMOTE_ADDR')

        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        UserPreferenceHistory.objects.create(
            user=user,
            profile=profile,
            action=action,
            preferences_snapshot=snapshot,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f'Failed to create history entry: {e}')


def _load_default_preference_to_session(request: HttpRequest, user):
    """Load user's default preference profile into session."""
    try:
        default_profile = UserPreference.objects.filter(
            user=user,
            is_default=True
        ).first()

        if default_profile:
            pref_manager = PreferenceManager(request)
            pref_manager.update_preferences(default_profile.to_dict())
            logger.info(f'Loaded default profile for {user.username}')
    except Exception as e:
        logger.error(f'Failed to load default preference: {e}')
