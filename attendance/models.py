from django.db import models
from schools.models import School
from academics.models import StudentProfile

class AttendanceRecord(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    present = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['school', 'date']),
            models.Index(fields=['school']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.student.user.username} - {self.date} - {'P' if self.present else 'A'}"
