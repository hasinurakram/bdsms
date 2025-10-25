from rest_framework import serializers
from schools.models import School
from .models import ClassRoom, Section, Subject, StudentProfile, TeacherAssignment
from django.contrib.auth import get_user_model
from users.models import Profile

User = get_user_model()

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'address']

class SimpleUserSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'photo', 'photo_url', 'mobile_number', 'educational_qualification']
    
    def get_photo_url(self, obj):
        try:
            if getattr(obj, 'photo', None):
                request = self.context.get('request')
                if request:
                    absolute_url = request.build_absolute_uri(obj.photo.url)
                    print(f"Building photo URL for {obj.username}: {absolute_url}")  # Debug
                    return absolute_url
                # Fallback if no request context
                photo_url = obj.photo.url
                print(f"No request context for {obj.username}, using relative: {photo_url}")  # Debug
                return photo_url
        except Exception as e:
            print(f"Error getting photo URL for {obj.username}: {e}")  # Debug
            pass
        return None
    
    def get_mobile_number(self, obj):
        """Return phone_number as mobile_number for consistency"""
        return getattr(obj, 'phone_number', None)

class ClassRoomSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True)
    student_count = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    
    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_sections(self, obj):
        """Get sections for this classroom"""
        return [{'id': s.id, 'name': s.name} for s in obj.sections.all()]
        
    class Meta:
        model = ClassRoom
        fields = ['id', 'school', 'school_id', 'name', 'description', 'student_count', 'sections']

class SectionSerializer(serializers.ModelSerializer):
    classroom = ClassRoomSerializer(read_only=True)
    classroom_id = serializers.PrimaryKeyRelatedField(source='classroom', queryset=ClassRoom.objects.all(), write_only=True)
    class Meta:
        model = Section
        fields = ['id', 'classroom', 'classroom_id', 'name']

class SubjectSerializer(serializers.ModelSerializer):
    assigned_teachers = serializers.SerializerMethodField()
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True, required=True)
    
    class Meta:
        model = Subject
        fields = ['id', 'school', 'school_id', 'name', 'code', 'assigned_teachers']
        read_only_fields = ['school']
    
    def get_assigned_teachers(self, obj):
        """Get all teachers assigned to this subject"""
        assignments = obj.assignments.select_related('teacher').all()
        teachers_data = []
        for assignment in assignments:
            teacher = assignment.teacher
            teachers_data.append({
                'id': teacher.id,
                'username': teacher.username,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'email': teacher.email,
                'phone_number': getattr(teacher, 'phone_number', ''),
                'photo_url': self._get_photo_url(teacher)
            })
        return teachers_data
    
    def _get_photo_url(self, user):
        """Helper to get photo URL"""
        try:
            if getattr(user, 'photo', None):
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(user.photo.url)
                return user.photo.url
        except Exception:
            pass
        return None

class StudentProfileSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all(), write_only=True, required=False, allow_null=True)
    # Allow setting school via school_id in writes
    school_id = serializers.PrimaryKeyRelatedField(source='school', queryset=School.objects.all(), write_only=True, required=False)
    classroom = ClassRoomSerializer(read_only=True)
    classroom_id = serializers.PrimaryKeyRelatedField(source='classroom', queryset=ClassRoom.objects.all(), write_only=True, allow_null=True, required=False)
    section = SectionSerializer(read_only=True)
    section_id = serializers.PrimaryKeyRelatedField(source='section', queryset=Section.objects.all(), write_only=True, allow_null=True, required=False)
    guardian = SimpleUserSerializer(read_only=True)
    guardian_id = serializers.PrimaryKeyRelatedField(source='guardian', queryset=User.objects.all(), write_only=True, allow_null=True, required=False)
    # Optional write-only fields to create a user on the fly when user_id is not provided
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_name = serializers.CharField(required=False, allow_blank=True)
    photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = StudentProfile
        fields = ['id', 'user', 'user_id', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'photo', 'school', 'school_id', 'classroom', 'classroom_id', 'section', 'section_id', 'roll_number', 'guardian', 'guardian_id', 'guardian_name']
        read_only_fields = ['school']

    def validate(self, data):
        errors = {}
        # If no user provided, ensure we have enough info to create
        if not data.get('user'):
            username = data.get('username') or ''
            first_name = (data.get('first_name') or '').strip()
            if not username and not first_name:
                errors['first_name'] = 'Provide at least a username or a first name'
            # Username uniqueness when provided
            if username and User.objects.filter(username=username).exists():
                errors['username'] = 'This username is already taken.'

        if errors:
            raise serializers.ValidationError(errors)
        return data

    def create(self, validated_data):
        # Ensure school is present (accept from initial_data fallback)
        school = validated_data.get('school')
        if not school:
            sid = (self.initial_data.get('school')
                   if isinstance(self.initial_data, dict) else None) or \
                  (self.initial_data.get('school_id') if isinstance(self.initial_data, dict) else None)
            if not sid:
                raise serializers.ValidationError({'school': 'This field is required.'})
            try:
                school = School.objects.get(pk=sid)
            except School.DoesNotExist:
                raise serializers.ValidationError({'school': 'Invalid school.'})
            validated_data['school'] = school

        # Delegate to original create logic (duplicated from below to insert school early)
        user = validated_data.pop('user', None)
        classroom = validated_data.pop('classroom', None)
        section = validated_data.pop('section', None)
        guardian = validated_data.pop('guardian', None)
        photo = validated_data.pop('photo', None)

        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')
        phone_number = validated_data.pop('phone_number', '')

        if not user:
            if not username:
                base = (first_name or 'student').lower().replace(' ', '')
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
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
                email=email or ''
            )
        # Assign phone number and photo if provided
        if 'phone_number' in locals():
            try:
                if phone_number:
                    setattr(user, 'phone_number', phone_number)
            except Exception:
                pass
        if photo is not None and hasattr(user, 'photo'):
            try:
                user.photo = photo
            except Exception:
                pass
        try:
            user.save()
        except Exception:
            pass
        if phone_number:
            try:
                setattr(user, 'phone_number', phone_number)
                user.save(update_fields=['phone_number'])
            except Exception:
                pass

        Profile.objects.update_or_create(user=user, defaults={'school': validated_data.get('school'), 'role': 'student'})

        sp = StudentProfile.objects.create(user=user, classroom=classroom, section=section, guardian=guardian, **validated_data)
        return sp

    def create(self, validated_data):
        # Extract related objects
        user = validated_data.pop('user', None)
        classroom = validated_data.pop('classroom', None)
        section = validated_data.pop('section', None)
        guardian = validated_data.pop('guardian', None)
        photo = validated_data.pop('photo', None)

        # Extract potential user creation fields
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')
        phone_number = validated_data.pop('phone_number', '')

        # If no user provided, create one (auto-generate username/password if missing)
        if not user:
            if not username:
                base = (first_name or 'student').lower().replace(' ', '')
                suffix = str(User.objects.count() + 1)
                username = f"{base}{suffix}"
                # ensure unique
                idx = 1
                orig = username
                while User.objects.filter(username=username).exists():
                    idx += 1
                    username = f"{orig}{idx}"
            if not password:
                import secrets, string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(10))
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
                email=email or ''
            )
        # Assign phone number and photo if provided
        if 'phone_number' in locals():
            try:
                if phone_number:
                    setattr(user, 'phone_number', phone_number)
            except Exception:
                pass
        if photo is not None and hasattr(user, 'photo'):
            try:
                user.photo = photo
            except Exception:
                pass
        # Save user if any changes
        try:
            user.save()
        except Exception:
            pass
        # Set phone number if provided
        if phone_number:
            try:
                setattr(user, 'phone_number', phone_number)
                user.save(update_fields=['phone_number'])
            except Exception:
                # Silently ignore if user model has no phone_number
                pass

        # Ensure a Profile exists and set school/role
        school = validated_data.get('school')
        Profile.objects.update_or_create(user=user, defaults={'school': school, 'role': 'student'})

        # Create the StudentProfile
        sp = StudentProfile.objects.create(user=user, classroom=classroom, section=section, guardian=guardian, **validated_data)
        return sp
    
    def update(self, instance, validated_data):
        """Update student profile and optionally update user fields"""
        # Extract related objects
        classroom = validated_data.pop('classroom', None)
        section = validated_data.pop('section', None)
        guardian = validated_data.pop('guardian', None)
        
        # Extract user fields if provided
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        phone_number = validated_data.pop('phone_number', None)
        
        # Update user fields if provided
        if instance.user:
            user_updated = False
            if first_name is not None:
                instance.user.first_name = first_name
                user_updated = True
            if last_name is not None:
                instance.user.last_name = last_name
                user_updated = True
            if email is not None:
                instance.user.email = email
                user_updated = True
            if phone_number is not None:
                try:
                    instance.user.phone_number = phone_number
                    user_updated = True
                except AttributeError:
                    pass
            
            if user_updated:
                instance.user.save()
        
        # Update student profile fields
        if classroom is not None:
            instance.classroom = classroom
        if section is not None:
            instance.section = section
        if guardian is not None:
            instance.guardian = guardian
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class TeacherAssignmentSerializer(serializers.ModelSerializer):
    teacher = SimpleUserSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(source='teacher', queryset=User.objects.all(), write_only=True)
    classroom = ClassRoomSerializer(read_only=True)
    classroom_id = serializers.PrimaryKeyRelatedField(source='classroom', queryset=ClassRoom.objects.all(), write_only=True)
    section = SectionSerializer(read_only=True)
    section_id = serializers.PrimaryKeyRelatedField(source='section', queryset=Section.objects.all(), write_only=True, allow_null=True, required=False)
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(source='subject', queryset=Subject.objects.all(), write_only=True, allow_null=True)

    class Meta:
        model = TeacherAssignment
        fields = ['id', 'teacher', 'teacher_id', 'subject', 'subject_id', 'classroom', 'classroom_id', 'section', 'section_id']
    
    def to_representation(self, instance):
        """Override to ensure context is passed to nested serializers"""
        ret = super().to_representation(instance)
        # Ensure teacher serializer gets the request context for photo URLs
        if instance.teacher:
            teacher_serializer = SimpleUserSerializer(instance.teacher, context=self.context)
            ret['teacher'] = teacher_serializer.data
        return ret
