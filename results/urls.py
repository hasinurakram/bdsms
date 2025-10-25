from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExaminationViewSet, ResultViewSet, StudentOverallResultViewSet

router = DefaultRouter()
router.register('examinations', ExaminationViewSet)
router.register('results', ResultViewSet)
router.register('overall', StudentOverallResultViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
