from django.urls import path
from django.views.generic import RedirectView
from . import views, views_preferences, views_auth

app_name = 'trends_viewer'

urlpatterns = [
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('trends/', views.TrendListView.as_view(), name='trend_list'),
    path('trends/<int:pk>/', views.TrendDetailView.as_view(), name='trend_detail'),
    path('runs/', views.CollectionRunListView.as_view(), name='run_list'),

    # Redirect old /topics/ URL to dashboard (for bookmarked URLs)
    path('topics/', RedirectView.as_view(pattern_name='trends_viewer:dashboard', permanent=True), name='topic_list'),

    # Preference-based filtered views (Phase 1)
    path('filtered/topics/', views_preferences.FilteredTopicListView.as_view(), name='filtered_topics'),
    path('filtered/trends/', views_preferences.FilteredTrendListView.as_view(), name='filtered_trends'),

    # AJAX endpoints for preferences (Phase 1)
    path('api/preferences/update/', views_preferences.update_preferences_ajax, name='update_preferences_ajax'),
    path('api/preferences/reset/', views_preferences.reset_preferences_ajax, name='reset_preferences_ajax'),
    path('api/preferences/preview/', views_preferences.get_filter_preview, name='filter_preview'),

    # Translation provider toggle (Session D)
    path('api/translation/provider/', views.set_translation_provider, name='set_translation_provider'),

    # Authentication (Phase 2)
    path('register/', views_auth.register_view, name='register'),
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),

    # User Profile & Preference Management (Phase 2)
    path('profile/', views_auth.user_profile_view, name='user_profile'),
    path('profile/create/', views_auth.create_preference_profile, name='create_preference_profile'),
    path('profile/edit/<int:profile_id>/', views_auth.edit_preference_profile, name='edit_preference_profile'),
    path('profile/delete/<int:profile_id>/', views_auth.delete_preference_profile, name='delete_preference_profile'),
    path('profile/activate/<int:profile_id>/', views_auth.activate_preference_profile, name='activate_preference_profile'),
    path('profile/set-default/<int:profile_id>/', views_auth.set_default_profile, name='set_default_profile'),
    path('profile/save-current/', views_auth.save_current_preferences, name='save_current_preferences'),
    path('profile/notifications/', views_auth.manage_notifications, name='manage_notifications'),

    # AJAX endpoints for user profiles (Phase 2)
    path('api/profile/quick-save/', views_auth.quick_save_profile_ajax, name='quick_save_profile_ajax'),
    path('api/profile/list/', views_auth.get_user_profiles_ajax, name='get_user_profiles_ajax'),
]
