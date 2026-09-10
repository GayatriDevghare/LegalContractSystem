from rest_framework.permissions import BasePermission

class RoleBasedPermission(BasePermission):


    def has_permission(self, request, view):

        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Django superuser has full access
        if request.user.is_superuser:
            return True

        role = getattr(request.user, "role", None)

        if not role:
            return False

        role_name = role.name.strip().lower()

        # ==========================================
        # ADMIN
        # ==========================================

        if role_name == "admin":
            return True

        # ==========================================
        # CONTRACT MANAGER
        # ==========================================

        if role_name == "contract manager":
            return request.method in [
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            ]

        # ==========================================
        # APPROVER
        # ==========================================

        if role_name == "approver":
            return request.method in [
                "GET",
                "POST",
                "PUT",
                "PATCH",
            ]

        # ==========================================
        # USER
        # ==========================================

        if role_name == "user":
            return request.method == "GET"

        return False


class IsAdministrator(BasePermission):


    def has_permission(self, request, view):

        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Django superuser
        if request.user.is_superuser:
            return True

        role = getattr(request.user, "role", None)

        if not role:
            return False

        # Only Admin
        return role.name.strip().lower() == "admin"

