from rest_framework import viewsets
from .models import FeeStructure, Payment, FeeCategory, StudentFeeAssignment, FeeCollection
from .serializers import (
    FeeStructureSerializer, PaymentSerializer,
    FeeCategorySerializer, StudentFeeAssignmentSerializer, FeeCollectionSerializer
)
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.select_related('school').all()
    serializer_class = FeeStructureSerializer
    permission_classes = [AllowAny]  # TEMP: dev-only open access
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school']

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('student__user','fee_assignment').all()
    serializer_class = PaymentSerializer
    permission_classes = [AllowAny]  # TEMP: dev-only open access
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student','fee_assignment']


class FeeCategoryViewSet(viewsets.ModelViewSet):
    queryset = FeeCategory.objects.select_related('school').all()
    serializer_class = FeeCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school']


class StudentFeeAssignmentViewSet(viewsets.ModelViewSet):
    queryset = StudentFeeAssignment.objects.select_related('student__user','fee_structure__category').all()
    serializer_class = StudentFeeAssignmentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fee_structure__category', 'is_waived']


class FeeCollectionViewSet(viewsets.ModelViewSet):
    queryset = FeeCollection.objects.select_related('school','classroom').all()
    serializer_class = FeeCollectionSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school','classroom','month','year']
