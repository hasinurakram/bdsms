from rest_framework import serializers
from .models import AttendanceRecord
from academics.models import StudentProfile
from django.db.models import Count, Q

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    classroom_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceRecord
        fields = ['id','school','student','student_name','classroom_name','section_name','date','present','note']
    
    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}".strip() or obj.student.user.username
    
    def get_classroom_name(self, obj):
        return obj.student.classroom.name if obj.student.classroom else 'N/A'
    
    def get_section_name(self, obj):
        return obj.student.section.name if obj.student.section else 'N/A'

class AttendanceSummarySerializer(serializers.Serializer):
    """Serializer for attendance summary/report"""
    date = serializers.DateField()
    classroom = serializers.CharField()
    section = serializers.CharField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()

class MonthlyAttendanceSerializer(serializers.Serializer):
    """Serializer for monthly attendance report"""
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    classroom = serializers.CharField()
    section = serializers.CharField()
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
