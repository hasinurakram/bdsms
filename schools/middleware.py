# backend/schools/middleware.py
from django.utils.deprecation import MiddlewareMixin
from .models import School
import threading

_thread_locals = threading.local()

def get_current_school():
    """Returns the current school for this request/thread."""
    return getattr(_thread_locals, 'school', None)

class TenantMiddleware(MiddlewareMixin):
    """Middleware to attach the current school to the request."""
    def process_request(self, request):
        school = None

        # Try to get school from custom header
        school_id = request.META.get('HTTP_X_SCHOOL_ID')
        if school_id:
            try:
                school = School.objects.get(pk=int(school_id))
            except (School.DoesNotExist, ValueError):
                school = None
        else:
            # Try path-based: /school/<id>/...
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) > 1 and path_parts[0] == 'school':
                try:
                    school = School.objects.get(pk=int(path_parts[1]))
                except (School.DoesNotExist, ValueError):
                    school = None

        # Save school in thread-local and request
        _thread_locals.school = school
        request.current_school = school
