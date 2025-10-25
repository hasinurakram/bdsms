from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from .models import Examination, Result, StudentOverallResult
from .serializers import ExaminationSerializer, ResultSerializer, StudentOverallResultSerializer
import csv


class ExaminationViewSet(viewsets.ModelViewSet):
    queryset = Examination.objects.select_related('school', 'classroom', 'section').all()
    serializer_class = ExaminationSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school', 'classroom', 'section', 'exam_type']
    search_fields = ['name']
    
    @action(detail=True, methods=['post'])
    def bulk_results(self, request, pk=None):
        """Create or update results in bulk for an examination"""
        examination = self.get_object()
        results_data = request.data.get('results', [])
        
        if not results_data:
            return Response(
                {"detail": "No results data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created = 0
        updated = 0
        errors = []
        
        from academics.models import StudentProfile, Subject
        from django.db import transaction
        
        with transaction.atomic():
            for idx, result_item in enumerate(results_data):
                try:
                    student_id = result_item.get('student_id')
                    subject_id = result_item.get('subject_id')
                    
                    if not student_id or not subject_id:
                        errors.append({
                            'index': idx,
                            'error': 'student_id and subject_id are required'
                        })
                        continue
                    
                    # Validate student belongs to exam class
                    try:
                        student = StudentProfile.objects.get(id=student_id)
                        if student.classroom_id != examination.classroom_id:
                            errors.append({
                                'index': idx,
                                'error': f'Student does not belong to class {examination.classroom.name}'
                            })
                            continue
                    except StudentProfile.DoesNotExist:
                        errors.append({
                            'index': idx,
                            'error': f'Student with id {student_id} not found'
                        })
                        continue
                    
                    # Get subject
                    try:
                        subject = Subject.objects.get(id=subject_id)
                    except Subject.DoesNotExist:
                        errors.append({
                            'index': idx,
                            'error': f'Subject with id {subject_id} not found'
                        })
                        continue
                    
                    # Create or update result
                    result, is_created = Result.objects.update_or_create(
                        examination=examination,
                        student=student,
                        subject=subject,
                        defaults={
                            'written_marks': result_item.get('written_marks', 0),
                            'mcq_marks': result_item.get('mcq_marks', 0),
                            'practical_marks': result_item.get('practical_marks', 0),
                            'remarks': result_item.get('remarks', '')
                        }
                    )
                    
                    if is_created:
                        created += 1
                    else:
                        updated += 1
                        
                except Exception as e:
                    errors.append({
                        'index': idx,
                        'error': str(e)
                    })
            
            # After saving results, calculate overall results for affected students
            affected_students = set()
            for result_item in results_data:
                student_id = result_item.get('student_id')
                if student_id:
                    affected_students.add(student_id)
            
            # Calculate overall results for each affected student
            for student_id in affected_students:
                try:
                    student = StudentProfile.objects.get(id=student_id)
                    self._calculate_overall_result(examination, student)
                except Exception as e:
                    errors.append({
                        'student_id': student_id,
                        'error': f'Failed to calculate overall result: {str(e)}'
                    })
        
        return Response({
            'message': 'Bulk result creation completed',
            'created': created,
            'updated': updated,
            'errors': errors
        })
    
    def _calculate_overall_result(self, examination, student):
        """Calculate and save overall result for a student in an examination"""
        # Get all results for this student in this examination
        student_results = Result.objects.filter(
            examination=examination,
            student=student
        )
        
        if not student_results.exists():
            return
        
        # Calculate totals
        total_obtained = sum(r.total_obtained for r in student_results)
        total_possible = examination.total_marks * student_results.count()
        percentage = (total_obtained / total_possible * 100) if total_possible > 0 else 0
        
        # Calculate CGPA (average of all subject GPAs)
        cgpa = sum(r.gpa for r in student_results) / student_results.count()
        
        # Determine overall grade based on CGPA
        if cgpa >= 5.0:
            grade = 'A+'
        elif cgpa >= 4.0:
            grade = 'A'
        elif cgpa >= 3.5:
            grade = 'A-'
        elif cgpa >= 3.0:
            grade = 'B'
        elif cgpa >= 2.0:
            grade = 'C'
        elif cgpa >= 1.0:
            grade = 'D'
        else:
            grade = 'F'
        
        # Check if passed (all subjects must be passed)
        is_passed = all(r.is_passed for r in student_results)
        
        # Create or update overall result
        overall_result, created = StudentOverallResult.objects.update_or_create(
            examination=examination,
            student=student,
            defaults={
                'total_marks_obtained': total_obtained,
                'total_marks_possible': total_possible,
                'percentage': percentage,
                'cgpa': cgpa,
                'grade': grade,
                'is_passed': is_passed
            }
        )
        
        # Calculate ranks for all students in this examination
        self._calculate_ranks(examination)
    
    def _calculate_ranks(self, examination):
        """Calculate and assign ranks to all students in an examination"""
        # Get all overall results for this examination, ordered by CGPA
        overall_results = StudentOverallResult.objects.filter(
            examination=examination
        ).order_by('-cgpa', '-percentage')
        
        # Assign ranks
        for rank, result in enumerate(overall_results, start=1):
            result.rank = rank
            result.save(update_fields=['rank'])


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.select_related('examination', 'student__user', 'subject').all()
    serializer_class = ResultSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['examination', 'student', 'subject', 'grade', 'is_passed']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__roll_number']
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export results to CSV"""
        exam_id = request.query_params.get('examination')
        
        qs = self.filter_queryset(self.get_queryset())
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="results_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Serial', 'Roll Number', 'Student Name', 'Subject', 'Written', 'MCQ', 'Practical', 'Total', 'Grade', 'GPA', 'Status'])
        
        for idx, result in enumerate(qs, start=1):
            student = result.student
            student_name = f"{student.user.first_name} {student.user.last_name}".strip() or student.user.username
            status_text = 'Passed' if result.is_passed else 'Failed'
            
            writer.writerow([
                idx,
                student.roll_number or '',
                student_name,
                result.subject.name,
                result.written_marks,
                result.mcq_marks,
                result.practical_marks,
                result.total_obtained,
                result.grade,
                result.gpa,
                status_text
            ])
        
        return response


class StudentOverallResultViewSet(viewsets.ModelViewSet):
    queryset = StudentOverallResult.objects.select_related('examination', 'student__user').all()
    serializer_class = StudentOverallResultSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['examination', 'student', 'is_passed']
    search_fields = ['student__user__first_name', 'student__user__last_name']
    ordering_fields = ['cgpa', 'rank', 'percentage']
    ordering = ['-cgpa']
    
    @action(detail=False, methods=['get'])
    def combined_by_exam_type(self, request):
        """Get combined overall result for a student across all examinations of a specific type"""
        student_id = request.query_params.get('student')
        exam_type = request.query_params.get('exam_type')
        classroom_id = request.query_params.get('classroom')
        
        if not student_id or not exam_type or not classroom_id:
            return Response(
                {"detail": "student, exam_type, and classroom parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from academics.models import StudentProfile
        
        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {"detail": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all examinations of this type for this classroom
        examinations = Examination.objects.filter(
            exam_type=exam_type,
            classroom_id=classroom_id
        )
        
        if not examinations.exists():
            return Response(
                {"detail": "No examinations found for this type and classroom"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all results for this student across all these examinations
        results = Result.objects.filter(
            examination__in=examinations,
            student=student
        ).select_related('examination', 'subject')
        
        if not results.exists():
            return Response(
                {"detail": "No results found for this student"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate combined totals
        total_obtained = sum(float(r.total_obtained) for r in results)
        total_possible = sum(r.examination.total_marks for r in results)
        avg_gpa = sum(float(r.gpa) for r in results) / results.count()
        percentage = (total_obtained / total_possible * 100) if total_possible > 0 else 0
        is_passed = all(r.is_passed for r in results)
        
        # Determine grade based on CGPA
        if avg_gpa >= 5.0:
            grade = 'A+'
        elif avg_gpa >= 4.0:
            grade = 'A'
        elif avg_gpa >= 3.5:
            grade = 'A-'
        elif avg_gpa >= 3.0:
            grade = 'B'
        elif avg_gpa >= 2.0:
            grade = 'C'
        elif avg_gpa >= 1.0:
            grade = 'D'
        else:
            grade = 'F'
        
        # Calculate rank by comparing with other students in the same classroom
        # Get all students in this classroom
        from academics.models import StudentProfile
        all_students = StudentProfile.objects.filter(classroom_id=classroom_id)
        
        student_results = []
        for s in all_students:
            s_results = Result.objects.filter(
                examination__in=examinations,
                student=s
            )
            if s_results.exists():
                s_total_obtained = sum(float(r.total_obtained) for r in s_results)
                s_total_possible = sum(r.examination.total_marks for r in s_results)
                s_avg_gpa = sum(float(r.gpa) for r in s_results) / s_results.count()
                s_percentage = (s_total_obtained / s_total_possible * 100) if s_total_possible > 0 else 0
                
                student_results.append({
                    'student_id': s.id,
                    'cgpa': s_avg_gpa,
                    'percentage': s_percentage
                })
        
        # Sort by CGPA descending, then percentage descending
        student_results.sort(key=lambda x: (-x['cgpa'], -x['percentage']))
        
        # Find rank
        rank = None
        for idx, sr in enumerate(student_results, start=1):
            if sr['student_id'] == student.id:
                rank = idx
                break
        
        return Response({
            'student': student.id,
            'exam_type': exam_type,
            'classroom': classroom_id,
            'total_marks_obtained': round(total_obtained, 2),
            'total_marks_possible': round(total_possible, 2),
            'percentage': round(percentage, 2),
            'cgpa': round(avg_gpa, 2),
            'grade': grade,
            'is_passed': is_passed,
            'rank': rank,
            'total_students': len(student_results)
        })
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export overall results to CSV"""
        qs = self.filter_queryset(self.get_queryset())
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="overall_results_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Rank', 'Roll Number', 'Student Name', 'Total Obtained', 'Total Possible', 'Percentage', 'CGPA', 'Grade', 'Status'])
        
        for result in qs:
            student = result.student
            student_name = f"{student.user.first_name} {student.user.last_name}".strip() or student.user.username
            status_text = 'Passed' if result.is_passed else 'Failed'
            
            writer.writerow([
                result.rank or '',
                student.roll_number or '',
                student_name,
                result.total_marks_obtained,
                result.total_marks_possible,
                result.percentage,
                result.cgpa,
                result.grade,
                status_text
            ])
        
        return response
