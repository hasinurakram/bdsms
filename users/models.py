from django.contrib.auth.models import AbstractUser
from django.db import models
from schools.models import School


class User(AbstractUser):
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True, help_text='Phone number with country code (e.g., +8801712345678)')
    educational_qualification = models.CharField(max_length=200, blank=True, null=True, help_text='Educational qualification (e.g., B.A., M.A., B.Ed.)')
    
    def __str__(self):
        return self.username

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('committee', 'Committee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    designation = models.CharField(max_length=100, blank=True, null=True, help_text='Designation/Role for committee members')

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    class Meta:
        indexes = [
            models.Index(fields=['school', 'role']),
            models.Index(fields=['school']),
        ]

class AdminProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = 'Admin'
        verbose_name_plural = 'Admins'

class ParentProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'

class CommitteeProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = 'Committee'
        verbose_name_plural = 'Committees'

class Task(models.Model):
    """Task model for committee members"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200, help_text='Task title')
    description = models.TextField(blank=True, null=True, help_text='Task description')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_tasks',
        help_text='Committee member assigned to this task'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(null=True, blank=True, help_text='Task due date')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        help_text='User who created this task'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'school']),
            models.Index(fields=['school', 'status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.assigned_to.username}"
