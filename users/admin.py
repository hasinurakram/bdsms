from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile, AdminProfile, ParentProfile, CommitteeProfile, Task

User = get_user_model()

class BaseProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'school', 'role']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_filter = ['school']
    readonly_fields = []
    fields = ['user', 'school', 'username', 'password', 'first_name', 'last_name', 'email']

    role_value = None  # override in subclasses

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.role_value:
            return qs.filter(role=self.role_value)
        return qs

    def save_model(self, request, obj, form, change):
        # Always upsert by user to avoid OneToOne conflicts
        role = self.role_value or obj.role
        school = obj.school
        user = obj.user
        from .models import Profile
        Profile.objects.update_or_create(
            user=user,
            defaults={'school': school, 'role': role}
        )

class AdminProfileAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    username = forms.CharField(required=False, help_text="Fill to create a new user if 'user' is not selected.")
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = AdminProfile
        fields = ['user', 'school']

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        username = cleaned_data.get('username')
        
        # If no existing user selected and username provided, check uniqueness
        if not user and username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError({
                    'username': f"Username '{username}' is already taken. Please choose another username."
                })
        
        return cleaned_data
    
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
                base = (first_name or 'admin').lower().replace(' ', '') or 'admin'
                suffix = str(User.objects.count() + 1)
                username = f"{base}{suffix}"
                orig = username
                idx = 1
                while User.objects.filter(username=username).exists():
                    idx += 1
                    username = f"{orig}{idx}"
            if not password:
                import secrets, string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )
            except Exception as e:
                raise forms.ValidationError(f"Failed to create user: {str(e)}")
            instance.user = user
        # Do NOT save here; ModelAdmin.save_model will upsert with correct role
        return instance

@admin.register(AdminProfile)
class AdminProfileAdmin(BaseProfileAdmin):
    form = AdminProfileAdminForm
    role_value = 'admin'
    verbose_name = 'Admin'

class ParentProfileAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    username = forms.CharField(required=False, help_text="Fill to create a new user if 'user' is not selected.")
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = ParentProfile
        fields = ['user', 'school']

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        username = cleaned_data.get('username')
        
        # If no existing user selected and username provided, check uniqueness
        if not user and username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError({
                    'username': f"Username '{username}' is already taken. Please choose another username."
                })
        
        return cleaned_data
    
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
                base = (first_name or 'parent').lower().replace(' ', '') or 'parent'
                suffix = str(User.objects.count() + 1)
                username = f"{base}{suffix}"
                orig = username
                idx = 1
                while User.objects.filter(username=username).exists():
                    idx += 1
                    username = f"{orig}{idx}"
            if not password:
                import secrets, string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )
            except Exception as e:
                raise forms.ValidationError(f"Failed to create user: {str(e)}")
            instance.user = user
        # Do NOT save here; ModelAdmin.save_model will upsert with correct role
        return instance

@admin.register(ParentProfile)
class ParentProfileAdmin(BaseProfileAdmin):
    form = ParentProfileAdminForm
    role_value = 'parent'
    verbose_name = 'Parent'

class CommitteeProfileAdminForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    username = forms.CharField(required=False, help_text="Fill to create a new user if 'user' is not selected.")
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = CommitteeProfile
        fields = ['user', 'school']

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        username = cleaned_data.get('username')
        
        # If no existing user selected and username provided, check uniqueness
        if not user and username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError({
                    'username': f"Username '{username}' is already taken. Please choose another username."
                })
        
        return cleaned_data
    
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
                base = (first_name or 'committee').lower().replace(' ', '') or 'committee'
                suffix = str(User.objects.count() + 1)
                username = f"{base}{suffix}"
                orig = username
                idx = 1
                while User.objects.filter(username=username).exists():
                    idx += 1
                    username = f"{orig}{idx}"
            if not password:
                import secrets, string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )
            except Exception as e:
                raise forms.ValidationError(f"Failed to create user: {str(e)}")
            instance.user = user
        # Do NOT save here; ModelAdmin.save_model will upsert with correct role
        return instance

@admin.register(CommitteeProfile)
class CommitteeProfileAdmin(BaseProfileAdmin):
    form = CommitteeProfileAdminForm
    role_value = 'committee'
    verbose_name = 'Committee'

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'assigned_to', 'school', 'status', 'priority', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'school', 'created_at']
    search_fields = ['title', 'description', 'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'status', 'priority', 'due_date')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'school')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
