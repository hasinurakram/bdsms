from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from .models import Profile, AdminProfile, ParentProfile, CommitteeProfile, Task
from .serializers import (
    UserSerializer,
    ProfileSerializer,
    UserRegistrationSerializer,
    AdminProfileSerializer,
    ParentProfileSerializer,
    CommitteeProfileSerializer,
    TeacherProfileSerializer,
    TaskSerializer,
)
from .sms_service import send_sms, send_bulk_sms, SMSTemplates

User = get_user_model()

class UsernameAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({"available": False, "error": "No username provided"}, status=status.HTTP_400_BAD_REQUEST)
        exists = User.objects.filter(username=q).exists()
        suggestions = []
        base = q.lower().replace(' ', '')
        # generate up to 5 suggestions
        i = 1
        while len(suggestions) < 5 and i <= 50:
            candidate = f"{base}{i}"
            if not User.objects.filter(username=candidate).exists():
                suggestions.append(candidate)
            i += 1
        return Response({"available": not exists, "suggestions": suggestions})

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create or update profile for the user
        school_id = request.data.get('school')
        role = request.data.get('role', 'student')
        Profile.objects.update_or_create(
            user=user,
            defaults={'school_id': school_id, 'role': role}
        )
        
        return Response({
            "user": UserSerializer(user).data,
            "message": "User registered successfully"
        }, status=status.HTTP_201_CREATED)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return Profile.objects.get(user=self.request.user)

class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
            return Response({
                "user": UserSerializer(user, context={'request': request}).data,
                "profile": ProfileSerializer(profile).data
            })
        except Profile.DoesNotExist:
            return Response({
                "user": UserSerializer(user, context={'request': request}).data,
                "message": "Profile does not exist"
            }, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request):
        """Update user photo"""
        user = request.user
        
        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']
            user.save()
            return Response({
                "message": "Photo uploaded successfully",
                "user": UserSerializer(user, context={'request': request}).data
            })
        
        return Response({"error": "No photo provided"}, status=status.HTTP_400_BAD_REQUEST)
        


class CreateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """Create a profile for the current user"""
        user = request.user
        
        # Check if profile already exists
        if hasattr(user, 'profile'):
            return Response({
                "message": "Profile already exists",
                "user": UserSerializer(user, context={'request': request}).data,
                "profile": ProfileSerializer(user.profile).data
            })
            
        # Create profile with default role
        profile = Profile.objects.create(
            user=user,
            role=request.data.get('role', 'student')
        )
        
        # Update user information
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        user.save()
        
        return Response({
            "message": "Profile created successfully",
            "user": UserSerializer(user, context={'request': request}).data,
            "profile": ProfileSerializer(profile).data
        }, status=status.HTTP_201_CREATED)

# ---- Role ViewSets (dev-open) ----
class AdminProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user', 'school').filter(role='admin')
    serializer_class = AdminProfileSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['school']
    parser_classes = [MultiPartParser, FormParser]

class ParentProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user', 'school').filter(role='parent')
    serializer_class = ParentProfileSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['school']
    parser_classes = [MultiPartParser, FormParser]

class CommitteeProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user', 'school').filter(role='committee')
    serializer_class = CommitteeProfileSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['school']
    parser_classes = [MultiPartParser, FormParser]

class TeacherProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user', 'school').filter(role='teacher')
    serializer_class = TeacherProfileSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['school', 'user']
    parser_classes = [MultiPartParser, FormParser]

class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing committee tasks"""
    queryset = Task.objects.select_related('assigned_to', 'school', 'created_by').all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['school', 'assigned_to', 'status', 'priority']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by school if provided
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        # Filter by assigned user if provided
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        return queryset


# ---- SMS API Views ----
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_sms_view(request):
    """Send SMS to a single recipient"""
    phone_number = request.data.get('phone_number')
    message = request.data.get('message')
    
    if not phone_number or not message:
        return Response(
            {"error": "phone_number and message are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, result_message = send_sms(phone_number, message)
    
    if success:
        return Response({
            "success": True,
            "message": result_message
        })
    else:
        return Response({
            "success": False,
            "error": result_message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_bulk_sms_view(request):
    """Send SMS to multiple recipients"""
    phone_numbers = request.data.get('phone_numbers', [])
    message = request.data.get('message')
    
    if not phone_numbers or not message:
        return Response(
            {"error": "phone_numbers (array) and message are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = send_bulk_sms(phone_numbers, message)
    
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    return Response({
        "success": True,
        "total": len(results),
        "sent": success_count,
        "failed": fail_count,
        "results": results
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_template_sms_view(request):
    """Send SMS using predefined templates"""
    template_name = request.data.get('template')
    template_data = request.data.get('data', {})
    phone_number = request.data.get('phone_number')
    
    if not template_name or not phone_number:
        return Response(
            {"error": "template and phone_number are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get template message
    templates = {
        'admission': SMSTemplates.admission_confirmation,
        'result': SMSTemplates.result_published,
        'fee_reminder': SMSTemplates.fee_reminder,
        'attendance': SMSTemplates.attendance_alert,
        'exam_schedule': SMSTemplates.exam_schedule,
        'meeting': SMSTemplates.meeting_invitation,
    }
    
    template_func = templates.get(template_name)
    if not template_func:
        return Response(
            {"error": f"Template '{template_name}' not found"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        message = template_func(**template_data)
        success, result_message = send_sms(phone_number, message)
        
        if success:
            return Response({
                "success": True,
                "message": result_message,
                "sms_content": message
            })
        else:
            return Response({
                "success": False,
                "error": result_message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except TypeError as e:
        return Response({
            "error": f"Invalid template data: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)

