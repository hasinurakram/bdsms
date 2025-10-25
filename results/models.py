from django.db import models
from django.conf import settings
from schools.models import School
from academics.models import ClassRoom, Section, Subject, StudentProfile

User = settings.AUTH_USER_MODEL


class Examination(models.Model):
    """Exam/Test definition"""
    EXAM_TYPES = [
        ('half_yearly', 'Half Yearly'),
        ('annual', 'Annual'),
        ('test', 'Class Test'),
        ('terminal', 'Terminal'),
        ('model', 'Model Test'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='examinations')
    name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='test')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='examinations')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='examinations')
    exam_date = models.DateField(null=True, blank=True)
    total_marks = models.IntegerField(default=100)
    pass_marks = models.IntegerField(default=33)
    
    class Meta:
        ordering = ['-exam_date', 'name']
        indexes = [
            models.Index(fields=['school', 'classroom']),
            models.Index(fields=['exam_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.classroom.name}"


class Result(models.Model):
    """Individual student result for a subject in an exam"""
    GRADE_CHOICES = [
        ('A+', 'A+ (80-100)'),
        ('A', 'A (70-79)'),
        ('A-', 'A- (60-69)'),
        ('B', 'B (50-59)'),
        ('C', 'C (40-49)'),
        ('D', 'D (33-39)'),
        ('F', 'F (0-32)'),
    ]
    
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='results')
    
    # Marks breakdown
    written_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mcq_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    practical_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Auto-calculated
    grade = models.CharField(max_length=5, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_passed = models.BooleanField(default=False)
    
    # Optional
    remarks = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('examination', 'student', 'subject')
        ordering = ['examination', 'student', 'subject']
        indexes = [
            models.Index(fields=['examination', 'student']),
            models.Index(fields=['student']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-calculate total
        self.total_obtained = self.written_marks + self.mcq_marks + self.practical_marks
        
        # Auto-calculate grade and GPA
        percentage = (self.total_obtained / self.examination.total_marks) * 100 if self.examination.total_marks > 0 else 0
        
        if percentage >= 80:
            self.grade = 'A+'
            self.gpa = 5.00
        elif percentage >= 70:
            self.grade = 'A'
            self.gpa = 4.00
        elif percentage >= 60:
            self.grade = 'A-'
            self.gpa = 3.50
        elif percentage >= 50:
            self.grade = 'B'
            self.gpa = 3.00
        elif percentage >= 40:
            self.grade = 'C'
            self.gpa = 2.00
        elif percentage >= 33:
            self.grade = 'D'
            self.gpa = 1.00
        else:
            self.grade = 'F'
            self.gpa = 0.00
        
        self.is_passed = self.total_obtained >= self.examination.pass_marks
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name} - {self.grade}"


class StudentOverallResult(models.Model):
    """Overall result summary for a student in an exam"""
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='overall_results')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='overall_results')
    
    total_marks_obtained = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_marks_possible = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgpa = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, blank=True)
    
    rank = models.IntegerField(null=True, blank=True)
    is_passed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('examination', 'student')
        ordering = ['-cgpa', 'student']
        indexes = [
            models.Index(fields=['examination', '-cgpa']),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - CGPA: {self.cgpa}"
