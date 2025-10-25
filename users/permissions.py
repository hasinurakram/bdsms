from rest_framework import permissions

class RolePermission(permissions.BasePermission):
    """
    Simple role based permission.
    - ReadOnly allowed to everyone (IsAuthenticatedOrReadOnly globally covers it)
    - Create/Update/Delete allowed based on role mapping
    """

    role_map = {
        'student': ['view'],
        'parent': ['view'],
        'teacher': ['view', 'change'],
        'committee': ['view', 'change'],
        'admin': ['view', 'change', 'create', 'delete'],
    }

    def has_permission(self, request, view):
        # Allow safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # if unauthenticated, deny for write
        if not request.user or not request.user.is_authenticated:
            return False

        # get role
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        role = profile.role

        # map method to action
        if request.method == 'POST':
            action = 'create'
        elif request.method in ('PUT','PATCH'):
            action = 'change'
        elif request.method == 'DELETE':
            action = 'delete'
        else:
            action = 'view'

        allowed = self.role_map.get(role, [])
        return action in allowed
