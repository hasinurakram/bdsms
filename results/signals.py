from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Result, StudentOverallResult


@receiver(post_save, sender=Result)
def calculate_overall_result_on_save(sender, instance, created, **kwargs):
    """
    Automatically calculate overall result when a Result is saved.
    This ensures GPA is always up-to-date when results are added or updated.
    """
    calculate_student_overall_result(instance.examination, instance.student)


@receiver(post_delete, sender=Result)
def calculate_overall_result_on_delete(sender, instance, **kwargs):
    """
    Recalculate overall result when a Result is deleted.
    """
    calculate_student_overall_result(instance.examination, instance.student)


def calculate_student_overall_result(examination, student):
    """
    Calculate and save overall result for a student in an examination.
    This combines all subject results to calculate CGPA and overall grade.
    """
    # Get all results for this student in this examination
    student_results = Result.objects.filter(
        examination=examination,
        student=student
    )
    
    if not student_results.exists():
        # If no results exist, delete the overall result if it exists
        StudentOverallResult.objects.filter(
            examination=examination,
            student=student
        ).delete()
        return
    
    # Calculate totals
    total_obtained = sum(float(r.total_obtained) for r in student_results)
    total_possible = float(examination.total_marks) * student_results.count()
    percentage = (total_obtained / total_possible * 100) if total_possible > 0 else 0
    
    # Calculate CGPA (average of all subject GPAs)
    cgpa = sum(float(r.gpa) for r in student_results) / student_results.count()
    
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
    calculate_ranks(examination)


def calculate_ranks(examination):
    """
    Calculate and assign ranks to all students in an examination.
    Ranks are based on CGPA (higher is better).
    """
    # Get all overall results for this examination, ordered by CGPA
    overall_results = StudentOverallResult.objects.filter(
        examination=examination
    ).order_by('-cgpa', '-percentage')
    
    # Assign ranks
    for rank, result in enumerate(overall_results, start=1):
        if result.rank != rank:
            result.rank = rank
            result.save(update_fields=['rank'])
