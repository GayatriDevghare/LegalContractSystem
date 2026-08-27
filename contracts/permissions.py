from rest_framework.permissions import BasePermission


class RoleBasedPermission(BasePermission):

    def has_permission(self, request, view):

        # User must be logged in
        if not request.user or not request.user.is_authenticated:
            return False

        # Django superuser has full access
        if request.user.is_superuser:
            return True

        # Get user's role
        role = request.user.role

        if role is None:
            return False

        role_name = role.name.lower()

        # Admin - full access
        if role_name == "admin":
            return True

        # Manager - CRUD except DELETE
        if role_name == "manager":
            return request.method in [
                "GET",
                "POST",
                "PUT",
                "PATCH",
            ]

        # Employee - read only
        if role_name == "employee":
            return request.method == "GET"

        # Viewer - read only
        if role_name == "viewer":
            return request.method == "GET"

        return False