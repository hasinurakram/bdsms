from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from users.models import Profile
from .models import ClassRoom, Section, Subject, StudentProfile, TeacherAssignment
import uuid
import secrets, string

User = get_user_model()


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'name']
    search_fields = ['name']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'classroom', 'name']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'name', 'code']
    search_fields = ['name', 'code']


class StudentProfileAdminForm(forms.ModelForm):
    # Optional inline user creation
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    username = forms.CharField(required=False, help_text="Fill to create a new user if 'user' is not selected.")
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    guardian = forms.ModelChoiceField(queryset=User.objects.all(), required=False,
                                      help_text="Existing parent user (optional)")
    guardian_name = forms.CharField(required=False, help_text="Parent name (if creating/linking automatically)")

    class Meta:
        model = StudentProfile
        fields = ['user', 'username', 'password', 'first_name', 'last_name', 'email', 'school', 'classroom', 'section',
                  'roll_number', 'guardian', 'guardian_name']

    def clean(self):
        return super().clean()

    def save(self, commit=True):
        instance = super().save(commit=False)
        user = self.cleaned_data.get('user')
        if not user:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            first_name = self.cleaned_data.get('first_name') or ''
            last_name = self.cleaned_data.get('last_name') or ''
            email = self.cleaned_data.get('email') or ''

            if not username:
                base = (first_name or 'student').lower().replace(' ', '') or 'student'
                # UUID ব্যবহার করে ইউনিক username
                username = f"{base}.{last_name.lower().replace(' ', '')}.{uuid.uuid4().hex[:6]}"

            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            Profile.objects.update_or_create(user=user,
                                             defaults={'school': self.cleaned_data.get('school'), 'role': 'student'})
            instance.user = user
        if commit:
            instance.save()
        return instance


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    form = StudentProfileAdminForm
    list_display = ['id', 'user', 'school', 'classroom', 'section', 'roll_number', 'guardian_name', 'guardian']
    search_fields = ['user__username', 'user__first_name', 'roll_number']


class TeacherAssignmentAdminForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(queryset=User.objects.all(), required=False,
                                     help_text="Select existing teacher or create new below")
    username = forms.CharField(required=False, help_text="Fill to create a new teacher if 'teacher' is not selected.")
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False, help_text="Phone number with country code")

    class Meta:
        model = TeacherAssignment
        fields = ['teacher', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'subject',
                  'classroom', 'section']

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        username = cleaned_data.get('username')
        if not teacher and not username:
            raise forms.ValidationError(
                "Please select an existing teacher or provide username to create a new teacher.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        teacher = self.cleaned_data.get('teacher')
        if not teacher:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            first_name = self.cleaned_data.get('first_name') or ''
            last_name = self.cleaned_data.get('last_name') or ''
            email = self.cleaned_data.get('email') or ''
            phone_number = self.cleaned_data.get('phone_number') or ''

            if not username:
                base = (first_name or 'teacher').lower().replace(' ', '') or 'teacher'
                username = f"{base}.{last_name.lower().replace(' ', '')}.{uuid.uuid4().hex[:6]}"

            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))

            teacher = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            if phone_number:
                teacher.phone_number = phone_number
                teacher.save()

            school = instance.classroom.school if instance.classroom else None
            Profile.objects.update_or_create(user=teacher, defaults={'school': school, 'role': 'teacher'})
            instance.teacher = teacher

        if commit:
            instance.save()
        return instance


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    form = TeacherAssignmentAdminForm
    list_display = ['id', 'teacher', 'subject', 'classroom', 'section']
    search_fields = ['teacher__username', 'teacher__first_name', 'subject__name']

    fieldsets = (
        ('Select Existing Teacher', {
            'fields': ('teacher',),
            'description': 'Select an existing teacher from the dropdown, OR create a new teacher below.'
        }),
        ('Create New Teacher', {
            'fields': ('username', 'password', 'first_name', 'last_name', 'email', 'phone_number'),
            'description': 'Fill these fields to create a new teacher account. Leave blank if selecting existing teacher above.',
            'classes': ('collapse',)
        }),
        ('Assignment Details', {
            'fields': ('subject', 'classroom', 'section'),
        }),
    )
