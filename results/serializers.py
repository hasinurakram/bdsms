from rest_framework import serializers
from .models import Examination, Result, StudentOverallResult
from academics.serializers import StudentProfileSerializer, SubjectSerializer


class ExaminationSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)
    
    class Meta:
        model = Examination
        fields = ['id', 'school', 'name', 'exam_type', 'classroom', 'classroom_name', 'section', 'section_name', 'exam_date', 'total_marks', 'pass_marks']


class ResultSerializer(serializers.ModelSerializer):
    student = StudentProfileSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    examination = ExaminationSerializer(read_only=True)
    
    class Meta:
        model = Result
        fields = ['id', 'examination', 'student', 'subject', 'written_marks', 'mcq_marks', 'practical_marks', 'total_obtained', 'grade', 'gpa', 'is_passed', 'remarks']


class StudentOverallResultSerializer(serializers.ModelSerializer):
    student = StudentProfileSerializer(read_only=True)
    examination = ExaminationSerializer(read_only=True)
    
    class Meta:
        model = StudentOverallResult
        fields = ['id', 'examination', 'student', 'total_marks_obtained', 'total_marks_possible', 'percentage', 'cgpa', 'grade', 'rank', 'is_passed']
