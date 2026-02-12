from django.urls import path
from . import views

app_name = 'trends_viewer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('trends/', views.TrendListView.as_view(), name='trend_list'),
    path('trends/<int:pk>/', views.TrendDetailView.as_view(), name='trend_detail'),
    path('topics/', views.TopicListView.as_view(), name='topic_list'),
    path('runs/', views.CollectionRunListView.as_view(), name='run_list'),
]
