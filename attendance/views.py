from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, AttendanceSummarySerializer, MonthlyAttendanceSerializer
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from academics.models import StudentProfile, ClassRoom, Section
from datetime import datetime, timedelta
from collections import defaultdict

class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related('student__user','student__classroom','student__section','school').all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [AllowAny]  # TEMP: dev-only open access
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school','student','date']
    
    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """Bulk save or update attendance records"""
        records_data = request.data.get('records', [])
        
        if not records_data:
            return Response({'error': 'No records provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        saved_records = []
        errors = []
        
        for record_data in records_data:
            try:
                # Try to get existing record
                existing = AttendanceRecord.objects.filter(
                    student_id=record_data['student'],
                    date=record_data['date']
                ).first()
                
                if existing:
                    # Update existing record
                    existing.present = record_data['present']
                    existing.note = record_data.get('note', '')
                    existing.save()
                    saved_records.append(existing)
                else:
                    # Create new record - use _id suffix for foreign keys
                    record = AttendanceRecord.objects.create(
                        school_id=record_data['school'],
                        student_id=record_data['student'],
                        date=record_data['date'],
                        present=record_data['present'],
                        note=record_data.get('note', '')
                    )
                    saved_records.append(record)
            except Exception as e:
                errors.append({
                    'student': record_data.get('student'),
                    'error': str(e)
                })
        
        return Response({
            'success': True,
            'saved': len(saved_records),
            'errors': errors
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get attendance summary by date, classroom, and section"""
        school_id = request.query_params.get('school')
        date = request.query_params.get('date')
        
        if not school_id or not date:
            return Response({'error': 'school and date parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all students grouped by classroom and section
        students = StudentProfile.objects.filter(
            classroom__school_id=school_id
        ).select_related('classroom', 'section')
        
        # Get attendance records for the date
        attendance_records = AttendanceRecord.objects.filter(
            school_id=school_id,
            date=date
        ).select_related('student__classroom', 'student__section')
        
        # Create a map of student attendance
        attendance_map = {record.student_id: record.present for record in attendance_records}
        
        # Group by classroom and section
        summary_data = defaultdict(lambda: {'total': 0, 'present': 0, 'absent': 0})
        
        for student in students:
            classroom_name = student.classroom.name if student.classroom else 'No Class'
            section_name = student.section.name if student.section else 'No Section'
            key = (classroom_name, section_name)
            
            summary_data[key]['total'] += 1
            if student.id in attendance_map:
                if attendance_map[student.id]:
                    summary_data[key]['present'] += 1
                else:
                    summary_data[key]['absent'] += 1
            # If no record, count as absent
            else:
                summary_data[key]['absent'] += 1
        
        # Format the response
        summaries = []
        for (classroom, section), data in summary_data.items():
            percentage = (data['present'] / data['total'] * 100) if data['total'] > 0 else 0
            summaries.append({
                'date': date,
                'classroom': classroom,
                'section': section,
                'total_students': data['total'],
                'present_count': data['present'],
                'absent_count': data['absent'],
                'attendance_percentage': round(percentage, 2)
            })
        
        serializer = AttendanceSummarySerializer(summaries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get monthly attendance report for students"""
        school_id = request.query_params.get('school')
        month = request.query_params.get('month')  # Format: YYYY-MM
        classroom_id = request.query_params.get('classroom')
        section_id = request.query_params.get('section')
        
        if not school_id or not month:
            return Response({'error': 'school and month parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year, month_num = map(int, month.split('-'))
            start_date = datetime(year, month_num, 1).date()
            if month_num == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month_num + 1, 1).date()
        except ValueError:
            return Response({'error': 'Invalid month format. Use YYYY-MM'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter students
        students_query = StudentProfile.objects.filter(classroom__school_id=school_id)
        if classroom_id:
            students_query = students_query.filter(classroom_id=classroom_id)
        if section_id:
            students_query = students_query.filter(section_id=section_id)
        
        students = students_query.select_related('user', 'classroom', 'section')
        
        # Get student IDs for filtering attendance records
        student_ids = list(students.values_list('id', flat=True))
        
        # Get attendance records for the month
        attendance_records = AttendanceRecord.objects.filter(
            school_id=school_id,
            student_id__in=student_ids,
            date__gte=start_date,
            date__lt=end_date
        )
        
        # Create attendance map
        attendance_map = defaultdict(lambda: {'present': 0, 'absent': 0})
        for record in attendance_records:
            student_id = record.student_id
            if record.present:
                attendance_map[student_id]['present'] += 1
            else:
                attendance_map[student_id]['absent'] += 1
        
        # Calculate total working days (you might want to exclude weekends/holidays)
        total_days = (end_date - start_date).days
        
        # Format response
        reports = []
        for student in students:
            present = attendance_map[student.id]['present']
            absent = attendance_map[student.id]['absent']
            total_marked = present + absent
            percentage = (present / total_marked * 100) if total_marked > 0 else 0
            
            reports.append({
                'student_id': student.id,
                'student_name': f"{student.user.first_name} {student.user.last_name}".strip() or student.user.username,
                'classroom': student.classroom.name if student.classroom else 'N/A',
                'section': student.section.name if student.section else 'N/A',
                'total_days': total_marked,
                'present_days': present,
                'absent_days': absent,
                'attendance_percentage': round(percentage, 2)
            })
        
        serializer = MonthlyAttendanceSerializer(reports, many=True)
        return Response(serializer.data)
