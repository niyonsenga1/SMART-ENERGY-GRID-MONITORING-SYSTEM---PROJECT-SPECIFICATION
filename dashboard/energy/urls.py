# dashboard/energy/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # API Endpoints for charts
    path('api/realtime/', views.api_realtime, name='api_realtime'),
    path('api/daily/', views.api_daily, name='api_daily'),
    path('api/weekly/', views.api_weekly, name='api_weekly'),
    path('api/monthly_region/', views.api_monthly_region, name='api_monthly_region'),
    path('api/performance/', views.api_performance, name='api_performance'),
    path('api/chunk_strategies/', views.api_chunk_strategies, name='chunk_strategies'),
    path('api/storage_efficiency/', views.api_storage_efficiency, name='storage_efficiency'),
]
