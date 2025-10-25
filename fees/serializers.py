from rest_framework import serializers
from schools.models import School
from academics.models import StudentProfile
from .models import FeeStructure, Payment, FeeCategory, StudentFeeAssignment, FeeCollection

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'address']

class FeeStructureSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True)
    category = serializers.PrimaryKeyRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source='category', queryset=FeeCategory.objects.all(), write_only=True, allow_null=True, required=False)

    class Meta:
        model = FeeStructure
        fields = ['id', 'school', 'school_id', 'category', 'category_id', 'classroom', 'amount', 'frequency', 'due_day', 'late_fee_amount', 'late_fee_after_days', 'is_active', 'academic_year']

class PaymentSerializer(serializers.ModelSerializer):
    # Read-only nested references
    student = serializers.PrimaryKeyRelatedField(read_only=True)
    fee_assignment = serializers.PrimaryKeyRelatedField(read_only=True)

    # Write-only ids
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=StudentProfile.objects.all(), write_only=True)
    fee_assignment_id = serializers.PrimaryKeyRelatedField(source='fee_assignment', queryset=StudentFeeAssignment.objects.all(), write_only=True, allow_null=True, required=False)

    class Meta:
        model = Payment
        fields = [
            'id', 'student', 'student_id',
            'fee_assignment', 'fee_assignment_id',
            'amount', 'payment_method', 'payment_status', 'payment_date',
            'reference', 'transaction_id', 'receipt_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'receipt_number', 'created_at', 'updated_at', 'student', 'fee_assignment']


class FeeCategorySerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True)

    class Meta:
        model = FeeCategory
        fields = ['id', 'school', 'school_id', 'name', 'fee_type', 'description', 'is_mandatory']


class StudentFeeAssignmentSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=StudentProfile.objects.all(), write_only=True)
    fee_structure = FeeStructureSerializer(read_only=True)
    fee_structure_id = serializers.PrimaryKeyRelatedField(source='fee_structure', queryset=FeeStructure.objects.all(), write_only=True)

    class Meta:
        model = StudentFeeAssignment
        fields = [
            'id', 'student', 'student_id', 'fee_structure', 'fee_structure_id',
            'custom_amount', 'discount_percentage', 'discount_reason',
            'is_waived', 'waiver_reason', 'assigned_date'
        ]


class FeeCollectionSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True)

    class Meta:
        model = FeeCollection
        fields = [
            'id', 'school', 'school_id', 'classroom', 'month', 'year',
            'total_expected', 'total_collected', 'total_pending', 'collection_percentage'
        ]
