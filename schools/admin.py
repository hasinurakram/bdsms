from django.contrib import admin
from .models import School
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from rest_framework.test import APIRequestFactory
from academics.views import ImportStudentsAPI
from django.middleware.csrf import get_token

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'logo', 'import_link')
    
    def import_link(self, obj):
        url = reverse('admin:schools_school_import_students', args=[obj.id])
        return format_html('<a class="button" href="{}">Import Students</a>', url)
    import_link.short_description = 'Actions'
    import_link.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:school_id>/import-students/', self.admin_site.admin_view(self.import_students_view), name='schools_school_import_students'),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        school = get_object_or_404(School, pk=object_id)
        import_url = reverse('admin:schools_school_import_students', args=[school.id])
        extra = extra_context or {}
        extra['additional_button'] = format_html('<a class="button" href="{}">Import Students</a>', import_url)
        return super().change_view(request, object_id, form_url, extra_context=extra)

    def import_students_view(self, request, school_id):
        if request.method == 'POST':
            f = request.FILES.get('file')
            if not f:
                return HttpResponse('No file uploaded. <a href="">Back</a>')
            # Proxy to DRF ImportStudentsAPI
            factory = APIRequestFactory()
            drf_request = factory.post(f'/api/academics/imports/students/?school={school_id}', {
                'school': school_id,
            }, format='multipart')
            drf_request.FILES['file'] = f
            drf_request._force_auth_user = request.user  # Pass auth context
            response = ImportStudentsAPI.as_view()(drf_request)
            
            # Check response status
            status_code = response.status_code
            try:
                data = response.data
            except Exception as e:
                data = {'detail': f'Failed to parse response: {e}'}
            
            # Build detailed HTML
            if status_code != 200:
                error_detail = data.get('detail', 'Unknown error')
                html = f"""
                <h1>Import Failed</h1>
                <p style="color: red;">Error: {error_detail}</p>
                <p>Status Code: {status_code}</p>
                <p><a href="{reverse('admin:schools_school_import_students', args=[school_id])}">Try again</a> | 
                   <a href="{reverse('admin:schools_school_change', args=[school_id])}">Back to school</a></p>
                """
                return HttpResponse(html)
            
            # Success response
            created = data.get('created', 0)
            updated = data.get('updated', 0)
            errors = data.get('errors', [])
            error_details = '<br>'.join([f"Row {e.get('row')}: {e.get('error')}" for e in errors[:20]])
            if len(errors) > 20:
                error_details += f'<br>... and {len(errors) - 20} more errors'
            
            html = f"""
            <h1>Import Result</h1>
            <p><strong>Created:</strong> {created}</p>
            <p><strong>Updated:</strong> {updated}</p>
            <p><strong>Errors:</strong> {len(errors)}</p>
            {f'<div style="background: #fff3cd; padding: 10px; margin: 10px 0;"><strong>Error Details:</strong><br>{error_details}</div>' if errors else ''}
            <p><a href="{reverse('admin:schools_school_import_students', args=[school_id])}">Import more</a> | 
               <a href="{reverse('admin:schools_school_change', args=[school_id])}">Back to school</a></p>
            """
            return HttpResponse(html)

        # GET: Simple upload form
        upload_action = reverse('admin:schools_school_import_students', args=[school_id])
        csrf = get_token(request)
        html = f"""
        <h1>Import Students for School ID {school_id}</h1>
        <form method="post" enctype="multipart/form-data">
          <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}" />
          <input type="file" name="file" accept=".csv,.xlsx,.xlsm,.docx,.pdf,image/*" required />
          <button type="submit">Upload & Import</button>
        </form>
        <p><a href="{reverse('admin:schools_school_change', args=[school_id])}">Cancel</a></p>
        """
        return HttpResponse(html)
