from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClassRoomViewSet, SectionViewSet, SubjectViewSet,
    StudentProfileViewSet, TeacherAssignmentViewSet, SchoolListAPI, ImportStudentsAPI
)

router = DefaultRouter()
router.register('classrooms', ClassRoomViewSet)
router.register('sections', SectionViewSet)
router.register('subjects', SubjectViewSet)
router.register('students', StudentProfileViewSet)
router.register('assignments', TeacherAssignmentViewSet)

urlpatterns = [
    path('schools/', SchoolListAPI.as_view(), name='school-list'),  # ❌ api/ বাদ দিয়ে শুধু schools/
    path('imports/students/', ImportStudentsAPI.as_view(), name='import-students'),
    path('', include(router.urls)),
]
