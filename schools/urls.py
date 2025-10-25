from django.urls import path
from .views import SchoolViewSet, dashboard_stats
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)

urlpatterns = [
    path('dashboard-stats/', dashboard_stats, name='dashboard-stats'),
]

urlpatterns += router.urls
