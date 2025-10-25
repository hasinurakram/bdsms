from django.urls import path, include
from .views import TeacherProfileViewSet
from django.contrib.auth.models import Group
from rest_framework import viewsets, permissions
from rest_framework.serializers import ModelSerializer

from rest_framework.routers import DefaultRouter
from .views import (
    UserRegistrationView,
    UserProfileView,
    CurrentUserView,
    AdminProfileViewSet,
    ParentProfileViewSet,
    CommitteeProfileViewSet,
    TaskViewSet,
    send_sms_view,
    send_bulk_sms_view,
    send_template_sms_view,
    UsernameAvailabilityView,
    CreateProfileView,
)

router = DefaultRouter()
router.register(r'admins', AdminProfileViewSet, basename='admins')
router.register(r'parents', ParentProfileViewSet, basename='parents')
router.register(r'committees', CommitteeProfileViewSet, basename='committees')
router.register(r'teachers', TeacherProfileViewSet, basename='teachers')
router.register(r'tasks', TaskViewSet, basename='tasks')

# Expose Groups CRUD
class GroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]

router.register(r'groups', GroupViewSet, basename='groups')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('me/create_profile/', CreateProfileView.as_view(), name='create-profile'),
    path('username-availability/', UsernameAvailabilityView.as_view(), name='username-availability'),
    # SMS endpoints
    path('sms/send/', send_sms_view, name='send-sms'),
    path('sms/bulk/', send_bulk_sms_view, name='send-bulk-sms'),
    path('sms/template/', send_template_sms_view, name='send-template-sms'),
]
