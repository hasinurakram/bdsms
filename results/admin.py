from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from .models import Examination, Result, StudentOverallResult
import csv
import io


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'exam_type', 'school', 'classroom', 'section', 'exam_date', 'total_marks', 'pass_marks', 'action_links']
    list_filter = ['school', 'exam_type', 'classroom', 'exam_date']
    search_fields = ['name']
    date_hierarchy = 'exam_date'
    
    def action_links(self, obj):
        import_url = reverse('admin:results_examination_import_results', args=[obj.id])
        return format_html(
            '<a class="button" href="{}">Import Results</a>',
            import_url
        )
    action_links.short_description = 'Actions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:exam_id>/import-results/', self.admin_site.admin_view(self.import_results_view), name='results_examination_import_results'),
        ]
        return custom + urls
    
    def import_results_view(self, request, exam_id):
        exam = get_object_or_404(Examination, pk=exam_id)
        
        if request.method == 'POST':
            file = request.FILES.get('file')
            if not file:
                messages.error(request, 'No file uploaded')
                return HttpResponseRedirect(request.path)
            
            try:
                # Read CSV
                content = file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(content))
                
                created_count = 0
                updated_count = 0
                errors = []
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Expected columns: roll_number, subject_name, written_marks, mcq_marks, practical_marks
                        roll = row.get('roll_number', '').strip()
                        subject_name = row.get('subject_name', '').strip()
                        written = float(row.get('written_marks', 0) or 0)
                        mcq = float(row.get('mcq_marks', 0) or 0)
                        practical = float(row.get('practical_marks', 0) or 0)
                        
                        if not roll or not subject_name:
                            errors.append(f"Row {row_num}: Missing roll_number or subject_name")
                            continue
                        
                        # Find student
                        from academics.models import StudentProfile, Subject
                        student = StudentProfile.objects.filter(
                            school=exam.school,
                            classroom=exam.classroom,
                            roll_number=roll
                        ).first()
                        
                        if not student:
                            errors.append(f"Row {row_num}: Student with roll {roll} not found")
                            continue
                        
                        # Find subject
                        subject = Subject.objects.filter(school=exam.school, name=subject_name).first()
                        if not subject:
                            errors.append(f"Row {row_num}: Subject '{subject_name}' not found")
                            continue
                        
                        # Create or update result
                        result, created = Result.objects.update_or_create(
                            examination=exam,
                            student=student,
                            subject=subject,
                            defaults={
                                'written_marks': written,
                                'mcq_marks': mcq,
                                'practical_marks': practical,
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                # Show summary
                messages.success(request, f"Import complete! Created: {created_count}, Updated: {updated_count}")
                if errors:
                    for err in errors[:10]:  # Show first 10 errors
                        messages.warning(request, err)
                
                return HttpResponseRedirect(reverse('admin:results_examination_change', args=[exam_id]))
            
            except Exception as e:
                messages.error(request, f"Import failed: {str(e)}")
                return HttpResponseRedirect(request.path)
        
        # GET: Show upload form
        from django.middleware.csrf import get_token
        csrf = get_token(request)
        
        template_csv = "roll_number,subject_name,written_marks,mcq_marks,practical_marks\n1,Mathematics,75,18,0\n2,English,68,15,0"
        
        html = f"""
        <html>
        <head><title>Import Results</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>Import Results for: {exam.name}</h1>
            <p><strong>Class:</strong> {exam.classroom.name} | <strong>Section:</strong> {exam.section.name if exam.section else 'All'}</p>
            
            <h3>CSV Format Required:</h3>
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{template_csv}</pre>
            
            <form method="post" enctype="multipart/form-data" style="margin: 20px 0;">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}" />
                <input type="file" name="file" accept=".csv" required style="margin: 10px 0;" />
                <br>
                <button type="submit" style="padding: 10px 20px; background: #417690; color: white; border: none; border-radius: 5px; cursor: pointer;">Upload & Import</button>
            </form>
            
            <p><a href="{reverse('admin:results_examination_change', args=[exam_id])}">← Back to Examination</a></p>
        </body>
        </html>
        """
        return HttpResponse(html)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'examination', 'student_name', 'subject', 'written_marks', 'mcq_marks', 'practical_marks', 'total_obtained', 'grade', 'gpa', 'is_passed']
    list_filter = ['examination', 'subject', 'grade', 'is_passed']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__roll_number']
    readonly_fields = ['total_obtained', 'grade', 'gpa', 'is_passed']
    
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = 'Student'


@admin.register(StudentOverallResult)
class StudentOverallResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'examination', 'student_name', 'total_marks_obtained', 'total_marks_possible', 'percentage', 'cgpa', 'grade', 'rank', 'is_passed']
    list_filter = ['examination', 'is_passed', 'grade']
    search_fields = ['student__user__first_name', 'student__user__last_name']
    readonly_fields = ['total_marks_obtained', 'total_marks_possible', 'percentage', 'cgpa', 'grade', 'rank']
    
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = 'Student'
