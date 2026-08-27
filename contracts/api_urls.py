from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    register,
    login,
    logout,
    RoleViewSet,
    UserViewSet,
    ContractViewSet,
    DocumentViewSet,
    ClauseViewSet,
    ModificationViewSet,
    VersionViewSet,
    ApprovalViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()

router.register("roles", RoleViewSet)
router.register("users", UserViewSet)
router.register("contracts", ContractViewSet)
router.register("documents", DocumentViewSet)
router.register("clauses", ClauseViewSet)
router.register("modifications", ModificationViewSet)
router.register("versions", VersionViewSet)
router.register("approvals", ApprovalViewSet)
router.register("audit-logs", AuditLogViewSet)

urlpatterns = [
    path("auth/register/", register, name="register"),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),

]

urlpatterns += router.urls