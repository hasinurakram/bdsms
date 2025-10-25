from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, IntegerField, F
from django.db.models.functions import Cast
from .models import School
from .serializers import SchoolSerializer
from academics.models import ClassRoom, StudentProfile, TeacherAssignment, Subject
from users.models import Profile, User
from attendance.models import AttendanceRecord
from fees.models import Payment, FeeStructure
from datetime import datetime, timedelta

class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.AllowAny]  # TEMP: dev-only open access

@api_view(['GET'])
@permission_classes([permissions.AllowAny])  # TEMP: dev-only open access
def dashboard_stats(request):
    """
    Get statistics for dashboard
    """
    # Determine school id from query param; if missing and user is authenticated, fall back to profile
    school_id = request.query_params.get('school_id')
    if school_id is not None:
        try:
            school_id = int(school_id)
        except ValueError:
            return Response({"error": "Invalid school_id"}, status=400)
    elif request.user and request.user.is_authenticated:
        user_profile = Profile.objects.select_related('school').filter(user=request.user).first()
        if user_profile and user_profile.school:
            school_id = user_profile.school.id
    # If still no school_id, error out
    if not school_id:
        return Response({"error": "No school specified"}, status=400)

    # Validate school exists
    try:
        school_obj = School.objects.get(id=school_id)
    except School.DoesNotExist:
        return Response({"error": "School not found"}, status=404)
    
    # Get counts
    students_count = StudentProfile.objects.filter(school_id=school_id).count()
    teachers_count = Profile.objects.filter(school_id=school_id, role='teacher').count()
    classes_count = ClassRoom.objects.filter(school_id=school_id).count()
    subjects_count = Subject.objects.filter(school_id=school_id).count()
    
    # Recent attendance stats (last 7 days)
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    attendance_data = (
        AttendanceRecord.objects.filter(
            school_id=school_id,
            date__gte=week_ago
        )
        .values('date')
        .annotate(
            present=Sum(Cast('present', IntegerField())),
            total=Count('id'),
        )
        .annotate(
            absent=F('total') - F('present')
        )
        .values('date', 'present', 'absent')
        .order_by('date')
    )
    
    # Recent fee collections (last 30 days)
    month_ago = today - timedelta(days=30)
    fee_data = Payment.objects.filter(
        student__school_id=school_id,
        payment_date__gte=month_ago
    ).values('payment_date').annotate(
        amount=Sum('amount')
    ).order_by('payment_date')
    
    # Class distribution
    class_distribution = StudentProfile.objects.filter(
        school_id=school_id
    ).values('classroom__name').annotate(
        count=Count('id')
    ).order_by('classroom__name')
    
    return Response({
        'school_id': school_id,
        'school_name': school_obj.name,
        'students_count': students_count,
        'teachers_count': teachers_count,
        'classes_count': classes_count,
        'subjects_count': subjects_count,
        'attendance_data': list(attendance_data),
        'fee_data': list(fee_data),
        'class_distribution': list(class_distribution)
    })
