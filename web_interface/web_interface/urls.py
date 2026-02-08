"""
URL configuration for web_interface project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('trends_viewer.urls')),
]
