from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FeeCategory, FeeStructure, StudentFeeAssignment, Payment, FeeCollection


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'name', 'fee_type', 'is_mandatory']
    list_filter = ['school', 'fee_type', 'is_mandatory']
    search_fields = ['name']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'category', 'classroom', 'amount', 'frequency', 'due_day', 'is_active']
    list_filter = ['school', 'classroom', 'frequency', 'is_active']
    search_fields = ['category__name', 'classroom__name']
    list_editable = ['is_active']


@admin.register(StudentFeeAssignment)
class StudentFeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_name', 'fee_structure', 'payable_amount', 'discount_percentage', 'is_waived']
    list_filter = ['fee_structure__category', 'is_waived']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__roll_number']
    
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = 'Student'
    
    def payable_amount(self, obj):
        return obj.get_payable_amount()
    payable_amount.short_description = 'Payable Amount'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'receipt_number', 'student_name', 'amount', 'payment_method', 'payment_status', 'payment_date', 'receipt_link']
    list_filter = ['payment_method', 'payment_status', 'payment_date']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'receipt_number', 'transaction_id']
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = 'Student'
    
    def receipt_link(self, obj):
        if obj.receipt_number:
            return format_html('<a class="button" href="#" onclick="window.print(); return false;">Print Receipt</a>')
        return '-'
    receipt_link.short_description = 'Actions'


@admin.register(FeeCollection)
class FeeCollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'classroom', 'month', 'year', 'total_expected', 'total_collected', 'total_pending', 'collection_percentage']
    list_filter = ['school', 'classroom', 'year', 'month']
    readonly_fields = ['total_expected', 'total_collected', 'total_pending', 'collection_percentage']
