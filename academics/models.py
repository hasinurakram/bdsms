from django.db import models
from django.conf import settings
from schools.models import School

# Use the project's custom user model
User = settings.AUTH_USER_MODEL

class ClassRoom(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classrooms')
    name = models.CharField(max_length=100)  # e.g., Grade 1
    description = models.TextField(blank=True, null=True)
    class Meta:
        unique_together = ('school', 'name')
        ordering = ['name']
        indexes = [
            models.Index(fields=['school', 'name']),
            models.Index(fields=['school']),
        ]

    def __str__(self):
        return f"{self.school.name} - {self.name}"

class Section(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=50)  # e.g., A, B

    class Meta:
        unique_together = ('classroom', 'name')

    def __str__(self):
        return f"{self.classroom.name} - {self.name}"

class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('school', 'name')
        indexes = [
            models.Index(fields=['school', 'name']),
            models.Index(fields=['school']),
        ]

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    roll_number = models.CharField(max_length=50, blank=True, null=True)
    # Parent linkage
    guardian_name = models.CharField(max_length=255, blank=True, null=True)
    guardian = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        # user may be AbstractUser
        try:
            name = self.user.get_full_name() or self.user.username
        except:
            name = str(self.user)
        return f"{name} ({self.school.name})"

    class Meta:
        indexes = [
            models.Index(fields=['school']),
            models.Index(fields=['classroom']),
            models.Index(fields=['section']),
            models.Index(fields=['school', 'classroom']),
        ]

class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='assignments')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')

    class Meta:
        unique_together = ('teacher', 'subject', 'classroom', 'section')

    def __str__(self):
        return f"{self.teacher} - {self.subject.name} - {self.classroom.name}"
