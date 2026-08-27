from django.contrib import admin
from .models import (
    Role,
    User,
    Contract,
    Document,
    Clause,
    Modification,
    Version,
    Approval,
    AuditLog,
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract_number",
        "title",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("contract_number", "title")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "contract",
        "document_type",
        "uploaded_by",
        "uploaded_at",
    )
    list_filter = ("document_type",)
    search_fields = ("name",)


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "clause_number",
        "title",
        "contract",
    )
    search_fields = ("clause_number", "title")


@admin.register(Modification)
class ModificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "clause",
        "modified_by",
        "modified_at",
    )


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract",
        "version_number",
        "created_by",
        "created_at",
    )


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract",
        "version",
        "approver",
        "status",
        "approved_at",
    )
    list_filter = ("status",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "action",
        "entity",
        "entity_id",
        "timestamp",
    )
    list_filter = ("action", "entity")
    search_fields = ("entity", "user__username")
