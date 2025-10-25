from django.db import models
from django.utils import timezone
from academics.models import StudentProfile, ClassRoom
from schools.models import School
from decimal import Decimal


class FeeCategory(models.Model):
    """Fee categories like Tuition, Admission, Exam, etc."""
    FEE_TYPES = [
        ('tuition', 'Tuition Fee'),
        ('admission', 'Admission Fee'),
        ('exam', 'Examination Fee'),
        ('transport', 'Transport Fee'),
        ('library', 'Library Fee'),
        ('sports', 'Sports Fee'),
        ('lab', 'Laboratory Fee'),
        ('other', 'Other'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_categories')
    name = models.CharField(max_length=100)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPES, default='other')
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Fee Categories'
        unique_together = ('school', 'name')
    
    def __str__(self):
        return f"{self.name} ({self.school.name})"


class FeeStructure(models.Model):
    """Fee structure for a class/grade"""
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('one_time', 'One Time'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_structures')
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='structures', null=True, blank=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='fee_structures', null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Due date settings
    due_day = models.PositiveIntegerField(default=10, help_text="Day of month for payment")
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_after_days = models.PositiveIntegerField(default=7, help_text="Days after due date")
    
    is_active = models.BooleanField(default=True)
    academic_year = models.CharField(max_length=20, blank=True, help_text="e.g., 2024-2025")

    def __str__(self):
        category_name = self.category.name if self.category else 'No Category'
        classroom_name = self.classroom.name if self.classroom else 'No Class'
        return f"{category_name} - {classroom_name} - {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=['school', 'classroom']),
            models.Index(fields=['is_active']),
        ]


class StudentFeeAssignment(models.Model):
    """Assign fees to individual students with custom amounts if needed"""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fee_assignments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='assignments')
    
    # Override amount if student has discount/scholarship
    custom_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True)
    
    is_waived = models.BooleanField(default=False)
    waiver_reason = models.TextField(blank=True)
    
    assigned_date = models.DateField(auto_now_add=True)
    
    def get_payable_amount(self):
        if self.is_waived:
            return Decimal('0.00')
        if self.custom_amount:
            return self.custom_amount
        base = self.fee_structure.amount
        if self.discount_percentage > 0:
            discount = base * (self.discount_percentage / 100)
            return base - discount
        return base
    
    class Meta:
        unique_together = ('student', 'fee_structure')
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.fee_structure.category.name}"


class Payment(models.Model):
    """Payment records"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
        ('mobile_banking', 'Mobile Banking (bKash/Nagad/Rocket)'),
        ('card', 'Credit/Debit Card'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='payments')
    fee_assignment = models.ForeignKey(StudentFeeAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='completed')
    
    payment_date = models.DateField(default=timezone.now)
    transaction_id = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=200, blank=True, help_text="Cheque number, receipt number, etc.")
    
    # For installments
    installment_number = models.PositiveIntegerField(default=1)
    remarks = models.TextField(blank=True)
    
    # Receipt
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Auto-generate receipt number
            import datetime
            today = datetime.date.today()
            count = Payment.objects.filter(payment_date=today).count() + 1
            self.receipt_number = f"RCP-{today.strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.amount} - {self.receipt_number}"

    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['receipt_number']),
            models.Index(fields=['payment_status']),
        ]


class FeeCollection(models.Model):
    """Monthly/periodic fee collection summary"""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_collections')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='fee_collections', null=True, blank=True)
    
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    
    total_expected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_pending = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    collection_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ('school', 'classroom', 'month', 'year')
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.school.name} - {self.month}/{self.year}"
