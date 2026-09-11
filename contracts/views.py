from django.db import transaction
from django.db.models import Q

from django.http import HttpResponse, FileResponse, HttpResponseForbidden
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy

from .models import (
    User,
    Role,
    Contract,
    Document,
    Clause,
    Modification,
    Version,
    Approval,
    AuditLog,
)
from .forms import (
    UserCreateForm,
    UserUpdateForm,
    RoleForm,
    ContractForm,
    DocumentForm,
    UserProfileForm,
    PasswordChangeForm,
    ClauseForm,
    ModificationForm,
    RegistrationForm,
    ChangePasswordForm,
)


User = get_user_model()


# =========================================================
# AUTHENTICATION + AUDIT LOG
# =========================================================

class UserLoginView(LoginView):

    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)

        create_audit_log(
            self.request,
            action="LOGIN",
            entity="User",
            entity_id=self.request.user.id,
            details={
                "username": self.request.user.username,
                "message": "User logged in successfully",
            },
        )

        return response


class UserLogoutView(LogoutView):

    next_page = reverse_lazy("web_login")

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:

            create_audit_log(
                request,
                action="LOGOUT",
                entity="User",
                entity_id=request.user.id,
                details={
                    "username": request.user.username,
                    "message": "User logged out",
                },
            )

        return super().dispatch(request, *args, **kwargs)


def create_audit_log(
    request,
    action,
    entity,
    entity_id=None,
    details=None
):

    AuditLog.objects.create(
        user=(
            request.user
            if request.user.is_authenticated
            else None
        ),
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details or {},
        ip_address=request.META.get("REMOTE_ADDR"),
    )


@login_required
def audit_log_list(request):
    if not is_administrator(request.user):
        return HttpResponseForbidden("You are not authorized to view audit logs.")

    logs = AuditLog.objects.select_related("user").all().order_by("-timestamp")

    return render(
        request,
        "contracts/audit_log_list.html",
        {"logs": logs}
    )
# =========================================================
# ROLE HELPERS
# =========================================================

def get_user_role(user):

    """
    Returns the logged-in user's role name in lowercase.
    """

    if not user.is_authenticated:
        return ""

    if user.is_superuser:
        return "admin"

    role = getattr(user, "role", None)

    if not role:
        return ""

    return role.name.strip().lower()


def is_administrator(user):

    """
    Returns True for Superuser and Admin.
    """

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return get_user_role(user) == "admin"


def can_view_all_data(user):

    """
    Admin, Contract Manager and Approver can
    view all contracts, documents, clauses
    and modification requests.
    """

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return get_user_role(user) in [
        "admin",
        "contract manager",
        "approver",
    ]


def can_manage_contracts(user):
    """
    Admin and Contract Manager can manage all contracts.

    User can manage only their own contracts.
    """

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return get_user_role(user) in [
        "admin",
        "contract manager",
        "user",
    ]


def can_approve_modifications(user):
    if not user.is_authenticated:
        return False

# Only the Approver role can approve/reject.
    if user.is_superuser:
        return False

    return get_user_role(user) == "approver"





def register(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        form = RegistrationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Registration successful. Please login."
            )

            return redirect("web_login")

    else:
        form = RegistrationForm()

    return render(
        request,
        "contracts/register.html",
        {
            "form": form,
        }
    )



# =========================================================
# DASHBOARD
# =========================================================

@login_required
def dashboard(request):

    role = get_user_role(request.user)

    # =========================================================
    # CONTRACTS
    # =========================================================

    if role == "user":

        # Normal User sees only their own contracts
        user_contracts = Contract.objects.filter(
            created_by=request.user
        ).prefetch_related(
            "clauses",
            "documents"
        ).order_by("-id")

    else:

        # Admin, Contract Manager and Approver
        # can see all contracts
        user_contracts = Contract.objects.all().prefetch_related(
            "clauses",
            "documents"
        ).order_by("-id")

    total_contracts = user_contracts.count()


    # =========================================================
    # USERS / ROLES
    # =========================================================

    total_users = User.objects.count()

    active_users = User.objects.filter(
        is_active=True
    ).count()

    total_roles = Role.objects.count()


    # =========================================================
    # MODIFICATION ACTIVITY
    # =========================================================

    if role == "user":

        # User sees ONLY their own modification requests
        modification_queryset = Modification.objects.filter(
            modified_by=request.user
        )

    elif role == "contract manager":

        # Contract Manager sees requests related
        # to contracts created by them
        modification_queryset = Modification.objects.filter(
            contract__created_by=request.user
        )

    elif role in ["admin", "approver"] or request.user.is_superuser:

        # Admin and Approver see all requests
        modification_queryset = Modification.objects.all()

    else:

        # Any other role sees nothing
        modification_queryset = Modification.objects.none()


    total_modifications = modification_queryset.count()

    pending_modifications = modification_queryset.filter(
        status="PENDING"
    ).count()

    approved_modifications = modification_queryset.filter(
        status="APPROVED"
    ).count()

    rejected_modifications = modification_queryset.filter(
        status="REJECTED"
    ).count()


    # =========================================================
    # RECENT USERS
    # =========================================================

    today = timezone.localdate()

    recent_users = User.objects.filter(
        date_joined__date=today
    ).order_by(
        "-date_joined"
    )

    recent_users_count = recent_users.count()


    # =========================================================
    # RECENT MODIFICATIONS
    # =========================================================

    if role == "user":

        # Only this user's requests
        recent_modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).filter(
            modified_by=request.user
        ).order_by(
            "-modified_at"
        )[:5]

    elif role == "contract manager":

        # Requests related to this manager's contracts
        recent_modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).filter(
            contract__created_by=request.user
        ).order_by(
            "-modified_at"
        )[:5]

    elif role in ["admin", "approver"] or request.user.is_superuser:

        # All requests
        recent_modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).order_by(
            "-modified_at"
        )[:5]

    else:

        recent_modifications = Modification.objects.none()


    # =========================================================
    # DASHBOARD CONTEXT
    # =========================================================

    context = {

        "total_users": total_users,

        "active_users": active_users,

        "total_roles": total_roles,

        "total_contracts": total_contracts,

        "user_contracts": user_contracts,

        "recent_users": recent_users,

        "recent_users_count": recent_users_count,

        "total_modifications": total_modifications,

        "pending_modifications": pending_modifications,

        "approved_modifications": approved_modifications,

        "rejected_modifications": rejected_modifications,

        "recent_modifications": recent_modifications,

    }


    # =========================================================
    # RETURN DASHBOARD
    # =========================================================

    return render(
        request,
        "contracts/dashboard.html",
        context
    )



# =========================================================
# PROFILE
# =========================================================

@login_required
def profile(request):

    return render(
        request,
        "contracts/profile.html"
    )


@login_required
def profile_edit(request):

    if request.method == "POST":

        form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if form.is_valid():

            new_photo = request.FILES.get(
                "profile_photo"
            )

            user = form.save(
                commit=False
            )

            if new_photo and request.user.profile_photo:

                request.user.profile_photo.delete(
                    save=False
                )

            user.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="User Profile",
                entity_id=request.user.id,
                details={
                    "username": request.user.username,
                    "message": "User profile updated successfully",
                },
            )

            messages.success(
                request,
                "Profile updated successfully."
            )

            return redirect("profile")

    else:

        form = UserProfileForm(
            instance=request.user
        )

    return render(
        request,
        "contracts/profile_edit.html",
        {
            "form": form
        }
    )


@login_required
def password_change(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            new_password = form.cleaned_data[
                "new_password"
            ]

            request.user.set_password(
                new_password
            )

            request.user.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="User Password",
                entity_id=request.user.id,
                details={
                    "username": request.user.username,
                    "message": "User password changed successfully",
                },
            )

            messages.success(
                request,
                "Password updated successfully."
            )

            return redirect("login")

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "contracts/password_change.html",
        {
            "form": form
        }
    )


@login_required
def profile_remove_photo(request):

    if request.method == "POST":

        if request.user.profile_photo:

            request.user.profile_photo.delete(
                save=False
            )

            request.user.profile_photo = None

            request.user.save(
            update_fields=["profile_photo"]
            )

            create_audit_log(
                request,
                action="UPDATE",
                entity="User Profile Photo",
                entity_id=request.user.id,
                details={
                    "username": request.user.username,
                    "message": "Profile photo removed",
                },
            )

            messages.success(
                request,
                "Profile photo removed successfully."
            )

        else:

            messages.info(
                request,
                "No profile photo to remove."
            )

    return redirect("profile")


# =========================================================
# USER MANAGEMENT
# =========================================================

@login_required
def user_list(request):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to access User Management."
        )

        return redirect("dashboard")

    users = User.objects.select_related(
        "role"
    ).all()

    return render(
        request,
        "contracts/user_list.html",
        {
            "users": users
        }
    )



@login_required
def user_create(request):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to create users."
        )

        return redirect("dashboard")

    if request.method == "POST":

        form = UserCreateForm(
            request.POST
        )

        if form.is_valid():

            new_user = form.save()

            create_audit_log(
                request,
                action="CREATE",
                entity="User",
                entity_id=new_user.id,
                details={
                    "username": new_user.username,
                    "role": (
                        new_user.role.name
                        if new_user.role
                        else None
                    ),
                    "message": "User created successfully",
                },
            )

            messages.success(
                request,
                "User created successfully."
            )

            return redirect("user_list")

    else:

        form = UserCreateForm()

    return render(
        request,
        "contracts/user_form.html",
        {
            "form": form,
            "title": "Add New User"
        }
    )





@login_required
def user_update(request, user_id):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to update users."
        )

        return redirect("dashboard")

    user = get_object_or_404(
        User,
        id=user_id
    )

    if request.method == "POST":

        form = UserUpdateForm(
            request.POST,
            instance=user
        )

        if form.is_valid():

            form.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="User",
                entity_id=user.id,
                details={
                    "username": user.username,
                    "role": (
                        user.role.name
                        if user.role
                        else None
                    ),
                    "message": "User updated successfully",
                },
            )

            messages.success(
                request,
                "User updated successfully."
            )

            return redirect("user_list")

    else:

        form = UserUpdateForm(
            instance=user
        )

    return render(
        request,
        "contracts/user_form.html",
        {
            "form": form,
            "title": "Edit User",
            "user_obj": user
        }
    )




@login_required
def user_delete(request, user_id):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to delete users."
        )

        return redirect("dashboard")

    user = get_object_or_404(
        User,
        id=user_id
    )

    # Prevent Admin from deleting their own account
    if user == request.user:

        messages.error(
            request,
            "You cannot delete your own account."
        )

        return redirect("user_list")

    if request.method == "POST":

        username = user.username
        deleted_user_id = user.id

        # Create audit log BEFORE deleting the user
        create_audit_log(
            request,
            action="DELETE",
            entity="User",
            entity_id=deleted_user_id,
            details={
                "username": username,
                "message": "User deleted successfully",
            },
        )

        user.delete()

        messages.success(
            request,
            f"User '{username}' was permanently deleted."
        )

        return redirect("user_list")

    return render(
        request,
        "contracts/user_confirm_delete.html",
        {
            "user_obj": user
        }
    )



# =========================================================
# ROLE MANAGEMENT
# =========================================================

@login_required
def role_list(request):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to access Role Management."
        )

        return redirect("dashboard")

    roles = Role.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "contracts/role_list.html",
        {
            "roles": roles
        }
    )


@login_required
def role_create(request):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to create roles."
        )

        return redirect("dashboard")

    if request.method == "POST":

        form = RoleForm(
            request.POST
        )

        if form.is_valid():
    
            role = form.save()

            create_audit_log(
                request,
                action="CREATE",
                entity="Role",
                entity_id=role.id,
                details={
                    "role_name": role.name,
                    "message": "Role created successfully",
                },
            )

            messages.success(
                request,
                "Role created successfully."
            )

            return redirect("role_list")

    else:

        form = RoleForm()

    return render(
        request,
        "contracts/role_form.html",
        {
            "form": form,
            "title": "Add New Role"
        }
    )



@login_required
def role_update(request, role_id):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to update roles."
        )

        return redirect("dashboard")

    role = get_object_or_404(
        Role,
        id=role_id
    )

    if request.method == "POST":

        form = RoleForm(
            request.POST,
            instance=role
        )

        if form.is_valid():

            updated_role = form.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="Role",
                entity_id=updated_role.id,
                details={
                    "role_name": updated_role.name,
                    "message": "Role updated successfully",
                },
            )

            messages.success(
                request,
                "Role updated successfully."
            )

            return redirect("role_list")

    else:

        form = RoleForm(
            instance=role
        )

    return render(
        request,
        "contracts/role_form.html",
        {
            "form": form,
            "title": "Edit Role",
            "role": role
        }
    )




@login_required
def role_delete(request, role_id):

    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to delete roles."
        )

        return redirect("dashboard")

    role = get_object_or_404(
        Role,
        id=role_id
    )

    if User.objects.filter(
        role=role
    ).exists():

        messages.error(
            request,
            f"Role '{role.name}' cannot be deleted because "
            "it is assigned to one or more users."
        )

        return redirect("role_list")

    if request.method == "POST":
    
        role_name = role.name
        deleted_role_id = role.id

        create_audit_log(
            request,
            action="DELETE",
            entity="Role",
            entity_id=deleted_role_id,
            details={
                "role_name": role_name,
                "message": "Role deleted successfully",
            },
        )

        role.delete()

        messages.success(
            request,
            f"Role '{role_name}' deleted successfully."
        )

        return redirect("role_list")

    return render(
        request,
        "contracts/role_confirm_delete.html",
        {
            "role": role
        }
    )


# =========================================================
# DOCUMENT MANAGEMENT
# =========================================================

@login_required
def document_create(request):

    contracts = Contract.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():

            document = form.save(commit=False)

            document.uploaded_by = request.user
            document.save()

            create_audit_log(
                request,
                action="UPLOAD",
                entity="Document",
                entity_id=document.id,
                details={
                    "contract_id": document.contract.id,
                    "contract_number": document.contract.contract_number,
                    "file_name": document.file.name,
                    "message": "Document uploaded successfully",
                },
            )

            messages.success(
                request,
                "Document created successfully."
            )

            return redirect("document_list")

    else:

        form = DocumentForm(
            user=request.user
        )

    return render(
        request,
        "contracts/document_form.html",
        {
            "form": form,
            "contracts": contracts,
            "title": "Create Document",
        }
    )

@login_required
def document_list(request):

    if can_view_all_data(request.user):

        documents = Document.objects.select_related(
            "contract",
            "uploaded_by"
        ).all()

    else:

        documents = Document.objects.select_related(
            "contract",
            "uploaded_by"
        ).filter(
            contract__created_by=request.user
        )

    return render(
        request,
        "contracts/document_list.html",
        {
            "documents": documents
        }
    )


@login_required
def document_view(request, document_id):

    if can_view_all_data(request.user):

        document = get_object_or_404(
            Document.objects.select_related(
                "contract"
            ),
            id=document_id
        )

    else:

        document = get_object_or_404(
            Document.objects.select_related(
                "contract"
            ),
            id=document_id,
            contract__created_by=request.user
        )

    return render(
        request,
        "contracts/document_view.html",
        {
            "document": document
        }
    )

@login_required
def document_download(request, document_id):

    if can_view_all_data(request.user):

        document = get_object_or_404(
            Document,
            id=document_id
        )

    else:

        document = get_object_or_404(
            Document,
            id=document_id,
            contract__created_by=request.user
        )

    if not document.file:

        return HttpResponse(
            "File not found.",
            status=404
        )

    create_audit_log(
        request,
        action="DOWNLOAD",
        entity="Document",
        entity_id=document.id,
        details={
            "contract_id": document.contract.id,
            "contract_number": document.contract.contract_number,
            "file_name": document.file.name,
            "message": "Document downloaded",
        },
    )

    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1]
    )

    return response




@login_required
def document_update(request, document_id):
    document = get_object_or_404(
        Document,
        id=document_id
    )

    role = get_user_role(request.user)

    # Approver cannot edit documents
    if role == "approver":
        messages.error(
            request,
            "Approvers are not authorized to edit documents."
        )
        return redirect("document_list")

    # Admin can edit all documents
    is_admin = (
        request.user.is_superuser
        or role == "admin"
    )

    # Contract Manager can edit all documents
    is_manager = role == "contract manager"

    # User can edit only documents belonging to their own contracts
    is_contract_owner = (
        role == "user"
        and document.contract.created_by_id == request.user.id
    )

    # User who uploaded the document can also edit it
    is_document_uploader = (
        role == "user"
        and document.uploaded_by_id == request.user.id
    )

    # Permission check
    if not (
        is_admin
        or is_manager
        or is_contract_owner
        or is_document_uploader
    ):
        messages.error(
            request,
            "You do not have permission to edit this document."
        )
        return redirect("document_list")

    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES,
            instance=document,
            user=request.user
        )

        if form.is_valid():

            updated_document = form.save(commit=False)

            # Keep original uploader
            updated_document.uploaded_by = document.uploaded_by

            updated_document.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="Document",
                entity_id=document.id,
                details={
                    "contract_id": document.contract.id,
                    "contract_number": document.contract.contract_number,
                    "file_name": (
                        document.file.name
                        if document.file
                        else None
                    ),
                    "message": "Document updated successfully",
                },
            )

            messages.success(
                request,
                "Document updated successfully."
            )

            return redirect("document_list")

    else:
        form = DocumentForm(
            instance=document,
            user=request.user
        )

    return render(
        request,
        "contracts/document_form.html",
        {
            "form": form,
            "title": "Edit Document",
            "document": document,
        }
    )







@login_required
def document_delete(request, document_id):
    document = get_object_or_404(
        Document,
        id=document_id
    )

    role = get_user_role(request.user)

    # Approver cannot delete documents
    if role == "approver":
        messages.error(
            request,
            "Approvers are not authorized to delete documents."
        )
        return redirect("document_list")

    # Admin can delete any document
    is_admin = (
        request.user.is_superuser
        or role == "admin"
    )

    # Contract Manager can delete any document
    is_manager = role == "contract manager"

    # User can delete only documents from their own contracts
    is_contract_owner = (
        role == "user"
        and document.contract.created_by_id == request.user.id
    )

    # Permission check
    if not (
        is_admin
        or is_manager
        or is_contract_owner
    ):
        messages.error(
            request,
            "You do not have permission to delete this document."
        )
        return redirect("document_list")

    # Save details before deleting
    contract_id = document.contract.id
    contract_number = document.contract.contract_number
    file_name = document.file.name if document.file else None

    # Create audit log BEFORE deleting the document
    create_audit_log(
        request,
        action="DELETE",
        entity="Document",
        entity_id=document.id,
        details={
            "contract_id": contract_id,
            "contract_number": contract_number,
            "file_name": file_name,
            "message": "Document deleted successfully",
        },
    )

    document.delete()

    messages.success(
        request,
        "Document deleted successfully."
    )

    return redirect("document_list")


# =========================================================
# CONTRACT MANAGEMENT
# =========================================================
@login_required
def contract_list(request):
    role = get_user_role(request.user)

    if role in ["admin", "contract manager"] or request.user.is_superuser:
        # Admin and Contract Manager can see all contracts
        contracts = Contract.objects.all().order_by("-created_at")

    elif role == "user":
        # User can see ONLY their own contracts
        contracts = Contract.objects.filter(
            created_by=request.user
        ).order_by("-created_at")

    else:
        # Approver
        contracts = Contract.objects.all().order_by("-created_at")

    return render(
        request,
        "contracts/contract_list.html",
        {
            "contracts": contracts,
        }
    )




@login_required
def contract_detail(request, contract_id):
    role = get_user_role(request.user)
    # Admin, Contract Manager, and Approver
    # can view all contracts.
    if role in ["admin", "contract manager", "approver"]:
        contract = get_object_or_404(
            Contract,
            id=contract_id
        )

    # Normal User can view only contracts created by themselves.
    elif role == "user":
        contract = get_object_or_404(
            Contract,
            id=contract_id,
            created_by=request.user
        )

    # No role assigned
    else:
        return HttpResponseForbidden(
            "You are not authorized to view this contract."
        )

    return render(
        request,
        "contracts/contract_detail.html",
        {
            "contract": contract
        }
    )




@login_required
def contract_create(request):

    role = get_user_role(request.user)

    if (
        role not in [
            "admin",
            "contract manager",
            "user"
        ]
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            "You are not authorized to create contracts."
        )

        return redirect("dashboard")

    if request.method == "POST":

        contract_form = ContractForm(
            request.POST
        )

        if contract_form.is_valid():

            contract = contract_form.save(
                commit=False
            )

            contract.created_by = request.user
            contract.save()

            # -----------------------------------------
            # CREATE INITIAL VERSION
            # -----------------------------------------

            initial_version = Version.objects.create(
                contract=contract,
                version_number=1,
                created_by=request.user,
                snapshot=create_contract_snapshot(contract),
                change_summary="Initial contract version"
            )

            create_audit_log(
                request,
                action="CREATE",
                entity="Version",
                entity_id=initial_version.id,
                details={
                    "contract_id": contract.id,
                    "contract_number": contract.contract_number,
                    "version_number": initial_version.version_number,
                    "message": "Initial contract version created",
                },
            )
                # -----------------------------------------
            # OPTIONAL DOCUMENT
            # -----------------------------------------

            if request.FILES.get("file"):

                document_form = DocumentForm(
                    request.POST,
                    request.FILES
                )

                document_form.fields[
                    "contract"
                ].required = False

                if document_form.is_valid():

                    document = document_form.save(
                        commit=False
                    )

                    document.contract = contract
                    document.uploaded_by = request.user
                    document.save()

                    # ---------------------------------
                    # AUDIT LOG - DOCUMENT UPLOAD
                    # ---------------------------------

                    create_audit_log(
                        request,
                        action="UPLOAD",
                        entity="Document",
                        entity_id=document.id,
                        details={
                            "contract_id":
                                contract.id,
                            "contract_number":
                                contract.contract_number,
                            "file_name":
                                document.file.name,
                            "message":
                                "Document uploaded with contract",
                        },
                    )

                else:

                    contract.delete()

                    messages.error(
                        request,
                        "Document upload failed. Please check the document details."
                    )

                    return render(
                        request,
                        "contracts/contract_form.html",
                        {
                            "contract_form":
                                contract_form,
                            "document_form":
                                document_form,
                            "title":
                                "Create Contract",
                        },
                    )

            messages.success(
                request,
                "Contract created successfully."
            )

            return redirect(
                "contract_list"
            )

        document_form = DocumentForm(
            request.POST,
            request.FILES
        )

    else:

        contract_form = ContractForm()
        document_form = DocumentForm()

    return render(
        request,
        "contracts/contract_form.html",
        {
            "contract_form":
                contract_form,
            "document_form":
                document_form,
            "title":
                "Create Contract",
        },
    )


@login_required
def contract_update(request, contract_id):
    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    role = get_user_role(request.user)

    # Admin and Contract Manager can edit any contract
    if role in ["admin", "contract manager"] or request.user.is_superuser:
        pass

    # User can edit ONLY their own contract
    elif role == "user":
        if contract.created_by_id != request.user.id:
            messages.error(
                request,
                "You can only edit your own contracts."
            )
            return redirect("contract_list")

    # Approver cannot edit
    else:
        messages.error(
            request,
            "You are not authorized to edit this contract."
        )
        return redirect("contract_list")

    if request.method == "POST":
        form = ContractForm(
            request.POST,
            request.FILES,
            instance=contract
        )

        if form.is_valid():
    
            form.save()

            create_audit_log(
                request,
                action="UPDATE",
                entity="Contract",
                entity_id=contract.id,
                details={
                    "contract_number":
                        contract.contract_number,
                    "title":
                        contract.title,
                    "status":
                        contract.status,
                    "message":
                        "Contract updated successfully",
                },
            )

            messages.success(
                request,
                "Contract updated successfully."
            )

            return redirect(
                "contract_detail",
                contract_id=contract.id
            )

    else:
        form = ContractForm(
            instance=contract
        )

    return render(
        request,
        "contracts/contract_form.html",
        {
            "contract_form": form,
            "title": "Edit Contract",
            "contract": contract,
        },
    )



@login_required
def contract_delete(request, contract_id):
    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    role = get_user_role(request.user)

    # Admin and Contract Manager can delete any contract
    if role in ["admin", "contract manager"] or request.user.is_superuser:
        pass

    # User can delete ONLY their own contract
    elif role == "user":
        if contract.created_by_id != request.user.id:
            messages.error(
                request,
                "You can only delete your own contracts."
            )
            return redirect("contract_list")

    # Approver cannot delete
    else:
        messages.error(
            request,
            "You are not authorized to delete this contract."
        )
        return redirect("contract_list")

    if request.method == "POST":
        
        contract_number = contract.contract_number
        contract_title = contract.title
        contract_id = contract.id

        create_audit_log(
            request,
            action="DELETE",
            entity="Contract",
            entity_id=contract_id,
            details={
                "contract_number":
                    contract_number,
                "title":
                    contract_title,
                "message":
                    "Contract deleted",
            },
        )

        contract.delete()

        messages.success(
            request,
            "Contract deleted successfully."
        )

        return redirect(
            "contract_list"
        )


# =========================================================
# CLAUSE MANAGEMENT
# =========================================================

@login_required
def clause_list(request, contract_id=None):
    role = get_user_role(request.user)

    if contract_id:
        contract = get_object_or_404(Contract, id=contract_id)

        # Admin, Approver, and Contract Manager can view all clauses
        if role in ["admin", "approver", "contract manager"] or request.user.is_superuser:
            pass

        # User can view only their own contract clauses
        elif role == "user":
            if contract.created_by_id != request.user.id:
                return HttpResponseForbidden(
                    "You are not authorized to view these clauses."
                )

        else:
            return HttpResponseForbidden(
                "You are not authorized to view these clauses."
            )

        clauses = contract.clauses.all()

        return render(
            request,
            "contracts/clause_list.html",
            {
                "contract": contract,
                "clauses": clauses,
            },
        )

    # Clause list without a specific contract
    if role in ["admin", "approver", "contract manager"] or request.user.is_superuser:
        clauses = Clause.objects.select_related("contract").all()

    elif role == "user":
        clauses = Clause.objects.select_related("contract").filter(
            contract__created_by=request.user
        )

    else:
        return HttpResponseForbidden(
            "You are not authorized to view clauses."
        )

    return render(
        request,
        "contracts/clause_list.html",
        {
            "clauses": clauses,
        },
    )





@login_required
def clause_create(request, contract_id):

    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    role = get_user_role(request.user)

    # -----------------------------------------
    # PERMISSION CHECK
    # -----------------------------------------
    # Approver is NOT allowed to create clauses.
    # Only Admin, Contract Manager and User can create.
    if role not in [
        "admin",
        "contract manager",
        "user",
    ] and not request.user.is_superuser:

        messages.error(
            request,
            "You are not authorized to add a clause."
        )

        return redirect(
            "contract_detail",
            contract_id=contract.id
        )

    # -----------------------------------------
    # USER CAN ONLY ADD CLAUSES TO OWN CONTRACT
    # -----------------------------------------
    if role == "user":

        if contract.created_by_id != request.user.id:

            messages.error(
                request,
                "You can only add clauses to your own contracts."
            )

            return redirect("contract_list")

    # -----------------------------------------
    # POST
    # -----------------------------------------
    if request.method == "POST":

        clause_number = request.POST.get(
            "clause_number",
            ""
        ).strip()

        title = request.POST.get(
            "title",
            ""
        ).strip()

        content = request.POST.get(
            "content",
            ""
        ).strip()

        order = request.POST.get(
            "order",
            "1"
        ).strip()

        # -----------------------------------------
        # VALIDATION
        # -----------------------------------------
        if not clause_number:

            messages.error(
                request,
                "Clause number is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": contract,
                    "clause_number": clause_number,
                    "title": title,
                    "content": content,
                    "order": order,
                }
            )

        if not title:

            messages.error(
                request,
                "Clause title is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": contract,
                    "clause_number": clause_number,
                    "title": title,
                    "content": content,
                    "order": order,
                }
            )

        if not content:

            messages.error(
                request,
                "Clause content is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": contract,
                    "clause_number": clause_number,
                    "title": title,
                    "content": content,
                    "order": order,
                }
            )

        # -----------------------------------------
        # VALIDATE ORDER
        # -----------------------------------------
        try:

            clause_order = int(order or 1)

            if clause_order < 1:
                raise ValueError

        except (ValueError, TypeError):

            messages.error(
                request,
                "Clause order must be a positive number."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": contract,
                    "clause_number": clause_number,
                    "title": title,
                    "content": content,
                    "order": order,
                }
            )

        # -----------------------------------------
        # CREATE CLAUSE
        # -----------------------------------------
        clause = Clause.objects.create(
            contract=contract,
            clause_number=clause_number,
            title=title,
            content=content,
            order=clause_order,
        )

        # -----------------------------------------
        # AUDIT LOG
        # -----------------------------------------
        create_audit_log(
            request,
            action="CREATE",
            entity="Clause",
            entity_id=clause.id,
            details={
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "clause_number": clause.clause_number,
                "title": clause.title,
                "message": "Clause created successfully",
            },
        )

        messages.success(
            request,
            "Clause created successfully."
        )

        return redirect(
            "contract_detail",
            contract_id=contract.id
        )

    # -----------------------------------------
    # GET
    # -----------------------------------------
    return render(
    request,
    "contracts/clause_form.html",
    {
        "contract": contract,
        "page_title": "Add New Clause",
        "is_edit": False,
    }
)


@login_required
def clause_update(request, clause_id):

    role = get_user_role(request.user)

    # Approver cannot edit clauses
    if role == "approver":
        messages.error(
            request,
            "Approvers are only authorized to view clauses."
        )
        return redirect("clause_list")

    # Get clause according to role
    if request.user.is_superuser or role in ["admin", "contract manager"]:

        clause = get_object_or_404(
            Clause.objects.select_related("contract"),
            id=clause_id
        )

    elif role == "user":

        clause = get_object_or_404(
            Clause.objects.select_related("contract"),
            id=clause_id,
            contract__created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to edit clauses."
        )
        return redirect("dashboard")


    # POST - UPDATE CLAUSE
    if request.method == "POST":

        clause_number = request.POST.get(
            "clause_number",
            ""
        ).strip()

        clause_title = request.POST.get(
            "title",
            ""
        ).strip()

        content = request.POST.get(
            "content",
            ""
        ).strip()

        order = request.POST.get(
            "order",
            "1"
        ).strip()


        # Validation

        if not clause_number:

            messages.error(
                request,
                "Clause number is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": clause.contract,
                    "clause": clause,
                    "page_title": "Edit Clause",
                    "is_edit": True,
                }
            )


        if not clause_title:

            messages.error(
                request,
                "Clause title is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": clause.contract,
                    "clause": clause,
                    "page_title": "Edit Clause",
                    "is_edit": True,
                }
            )


        if not content:

            messages.error(
                request,
                "Clause content is required."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": clause.contract,
                    "clause": clause,
                    "page_title": "Edit Clause",
                    "is_edit": True,
                }
            )


        try:

            clause_order = int(order or 1)

            if clause_order < 1:
                raise ValueError

        except (ValueError, TypeError):

            messages.error(
                request,
                "Clause order must be a positive number."
            )

            return render(
                request,
                "contracts/clause_form.html",
                {
                    "contract": clause.contract,
                    "clause": clause,
                    "page_title": "Edit Clause",
                    "is_edit": True,
                }
            )


        # Save changes

        clause.clause_number = clause_number
        clause.title = clause_title
        clause.content = content
        clause.order = clause_order

        clause.save()


        # Audit log

        create_audit_log(
            request,
            action="UPDATE",
            entity="Clause",
            entity_id=clause.id,
            details={
                "contract_id": clause.contract.id,
                "contract_number": clause.contract.contract_number,
                "clause_number": clause.clause_number,
                "title": clause.title,
                "message": "Clause updated successfully",
            },
        )


        messages.success(
            request,
            "Clause updated successfully."
        )


        return redirect(
            "contract_clause_list",
            contract_id=clause.contract.id
        )


    # GET - OPEN EDIT FORM

    return render(
        request,
        "contracts/clause_form.html",
        {
            "contract": clause.contract,
            "clause": clause,
            "page_title": "Edit Clause",
            "is_edit": True,
        }
    )


@login_required
def clause_detail(request, clause_id):

    clause = get_object_or_404(
        Clause.objects.select_related("contract"),
        id=clause_id,
    )

    role = get_user_role(request.user)

    # -----------------------------------------
    # ADMIN / APPROVER / CONTRACT MANAGER
    # CAN VIEW ALL CLAUSES
    # -----------------------------------------
    if (
        role in [
            "admin",
            "approver",
            "contract manager",
        ]
        or request.user.is_superuser
    ):

        pass

    # -----------------------------------------
    # USER CAN VIEW ONLY OWN CONTRACT CLAUSES
    # -----------------------------------------
    elif role == "user":

        if clause.contract.created_by_id != request.user.id:

            return HttpResponseForbidden(
                "You are not authorized to view this clause."
            )

    else:

        return HttpResponseForbidden(
            "You are not authorized to view this clause."
        )

    return render(
        request,
        "contracts/clause_detail.html",
        {
            "clause": clause,
            "contract": clause.contract,
        },
    )


@login_required
def clause_delete(request, clause_id):

    role = get_user_role(request.user)

    # -----------------------------------------
    # APPROVER CANNOT DELETE CLAUSES
    # -----------------------------------------
    if role == "approver":

        messages.error(
            request,
            "Approvers are only authorized to view clauses."
        )

        return redirect("clause_list")

    # -----------------------------------------
    # GET CLAUSE BASED ON ROLE
    # -----------------------------------------
    if (
        role in ["admin", "contract manager"]
        or request.user.is_superuser
    ):

        clause = get_object_or_404(
            Clause.objects.select_related("contract"),
            id=clause_id
        )

    elif role == "user":

        clause = get_object_or_404(
            Clause.objects.select_related("contract"),
            id=clause_id,
            contract__created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to delete clauses."
        )

        return redirect("dashboard")

    # -----------------------------------------
    # DELETE ONLY ON POST
    # -----------------------------------------
    if request.method == "POST":

        contract_id = clause.contract.id
        contract_number = clause.contract.contract_number
        clause_number = clause.clause_number
        clause_title = clause.title

        # -----------------------------------------
        # AUDIT LOG BEFORE DELETE
        # -----------------------------------------
        create_audit_log(
            request,
            action="DELETE",
            entity="Clause",
            entity_id=clause.id,
            details={
                "contract_id": contract_id,
                "contract_number": contract_number,
                "clause_number": clause_number,
                "title": clause_title,
                "message": "Clause deleted",
            },
        )

        clause.delete()

        messages.success(
            request,
            "Clause deleted successfully."
        )

        return redirect(
            "contract_clause_list",
            contract_id=contract_id
        )

    # -----------------------------------------
    # GET → CONFIRMATION PAGE
    # -----------------------------------------
    return render(
        request,
        "contracts/clause_confirm_delete.html",
        {
            "clause": clause,
            "contract": clause.contract,
        }
    )





@login_required
def clause_create_select(request):

    role = get_user_role(request.user)

    # Approver cannot create clauses
    if role == "approver":
        messages.error(
            request,
            "Approvers are only authorized to view clauses."
        )
        return redirect("clause_list")

    # Only Admin, Contract Manager and User can create clauses
    if not (
        request.user.is_superuser
        or role in ["admin", "contract manager", "user"]
    ):
        messages.error(
            request,
            "You are not authorized to create a clause."
        )
        return redirect("dashboard")

    # Admin and Contract Manager → all contracts
    if request.user.is_superuser or role in ["admin", "contract manager"]:

        contracts = Contract.objects.all().order_by("-created_at")

    # User → only their own contracts
    elif role == "user":

        contracts = Contract.objects.filter(
            created_by=request.user
        ).order_by("-created_at")

    else:

        contracts = Contract.objects.none()

    return render(
        request,
        "contracts/clause_select_contract.html",
        {
            "contracts": contracts,
        }
    )



# =========================================================
# DASHBOARD USER / ROLE DETAILS
# =========================================================

@login_required
def dashboard_users(request):

    users = User.objects.all().order_by(
        "-date_joined"
    )

    return render(
        request,
        "contracts/dashboard_user_list.html",
        {
            "users": users,
            "page_title": "All Users",
            "page_description":
                "All registered users in the system",
        }
    )


@login_required
def dashboard_active_users(request):

    users = User.objects.filter(
        is_active=True
    ).order_by(
        "-date_joined"
    )

    return render(
        request,
        "contracts/dashboard_user_list.html",
        {
            "users": users,
            "page_title": "Active Users",
            "page_description":
                "Users who are currently active",
        }
    )


@login_required
def dashboard_today_users(request):

    today = timezone.localdate()

    users = User.objects.filter(
        date_joined__date=today
    ).order_by(
        "-date_joined"
    )

    return render(
        request,
        "contracts/dashboard_user_list.html",
        {
            "users": users,
            "page_title": "Users Added Today",
            "page_description":
                "Users registered today",
        }
    )


@login_required
def dashboard_roles(request):

    roles = Role.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "contracts/dashboard_role_list.html",
        {
            "roles": roles,
            "page_title": "All Roles",
            "page_description":
                "All roles available in the system",
        }
    )


# =========================================================
# MODIFICATION MANAGEMENT
# =========================================================
@login_required
def modification_detail(request, modification_id):
    modification = get_object_or_404(
        Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by",
        ),
        id=modification_id,
    )

    role = get_user_role(request.user)

    # Admin and Approver can view all modifications
    if role in ["admin", "approver"] or request.user.is_superuser:
        pass

    # Contract Manager can view modifications for their own contracts
    elif role == "contract manager":
        if modification.contract.created_by_id != request.user.id:
            return HttpResponseForbidden(
                "You are not authorized to view this modification."
            )

    # User can view only their own modification requests
    elif role == "user":
        if modification.modified_by_id != request.user.id:
            return HttpResponseForbidden(
                "You are not authorized to view this modification."
            )

    else:
        return HttpResponseForbidden(
            "You are not authorized to view this modification."
        )

    can_approve = can_approve_modifications(request.user)

    return render(
        request,
        "contracts/modification_detail.html",
        {
            "modification": modification,
            "can_approve": can_approve,
        },
    )


@login_required
def modification_list(request):

    role = get_user_role(request.user)

    modifications = Modification.objects.select_related(
        "contract",
        "clause",
        "modified_by"
    ).all()

    # ---------------------------------------------------------
    # ROLE BASED ACCESS
    # ---------------------------------------------------------

    if role == "user":

        modifications = modifications.filter(
            modified_by=request.user
        )

    elif role == "contract manager":

        modifications = modifications.filter(
            contract__created_by=request.user
        )

    elif role == "approver":

        # Approver can review all requests
        pass

    elif role == "admin" or request.user.is_superuser:

        # Admin can see all
        pass

    else:

        modifications = modifications.none()


    # ---------------------------------------------------------
    # STATUS FILTER
    # ---------------------------------------------------------

    status = request.GET.get("status", "").strip().upper()

    if status in ["PENDING", "APPROVED", "REJECTED"]:
        modifications = modifications.filter(
            status=status
        )


    modifications = modifications.order_by("-modified_at")


    return render(
        request,
        "contracts/modification_list.html",
        {
            "modifications": modifications,
            "selected_status": status,
        }
    )


@login_required
def modification_create(request, contract_id=None):
    role = get_user_role(request.user)

    # ---------------------------------------------------------
    # CHECK PERMISSION
    # ---------------------------------------------------------
    allowed_roles = [
        "admin",
        "contract manager",
        "user",
        # "approver",   # Approver should not create requests
    ]

    if not (request.user.is_superuser or role in allowed_roles):
        messages.error(
            request,
            "You are not authorized to create a modification request."
        )
        return redirect("contract_list")

    # ---------------------------------------------------------
    # GET CONTRACT ID
    # ---------------------------------------------------------
    if contract_id is None:
        contract_id = request.GET.get("contract")

    if not contract_id:
        messages.error(
            request,
            "No contract was selected for modification."
        )
        return redirect("contract_list")

    # ---------------------------------------------------------
    # GET CONTRACT
    # ---------------------------------------------------------
    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    # ---------------------------------------------------------
    # USER CAN MODIFY ONLY THEIR OWN CONTRACT
    # ---------------------------------------------------------
    if role == "user" and contract.created_by_id != request.user.id:
        messages.error(
            request,
            "You can only create modifications for your own contracts."
        )
        return redirect("contract_list")

    # ---------------------------------------------------------
    # CLAUSES FOR THIS CONTRACT
    # ---------------------------------------------------------
    clauses = Clause.objects.filter(
        contract=contract
    ).order_by("order", "id")

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
    if request.method == "POST":

        clause_id = request.POST.get("clause")
        old_content = request.POST.get("old_content", "").strip()
        new_content = request.POST.get("new_content", "").strip()
        reason = request.POST.get("reason", "").strip()

        # -----------------------------------------------------
        # VALIDATE CLAUSE
        # -----------------------------------------------------
        clause = None

        if clause_id:
            clause = get_object_or_404(
                Clause,
                id=clause_id,
                contract=contract
            )

        # -----------------------------------------------------
        # VALIDATE OLD CONTENT
        # -----------------------------------------------------
        if not old_content:
            messages.error(
                request,
                "Original content is required."
            )

            return render(
                request,
                "contracts/modification_form.html",
                {
                    "contract": contract,
                    "clauses": clauses,
                    "selected_clause_id": clause_id,
                    "old_content": old_content,
                    "new_content": new_content,
                    "reason": reason,
                }
            )

        # -----------------------------------------------------
        # VALIDATE NEW CONTENT
        # -----------------------------------------------------
        if not new_content:
            messages.error(
                request,
                "Modified content is required."
            )

            return render(
                request,
                "contracts/modification_form.html",
                {
                    "contract": contract,
                    "clauses": clauses,
                    "selected_clause_id": clause_id,
                    "old_content": old_content,
                    "new_content": new_content,
                    "reason": reason,
                }
            )

        # -----------------------------------------------------
        # CREATE MODIFICATION
        # -----------------------------------------------------
        modification = Modification.objects.create(
            contract=contract,
            clause=clause,
            modified_by=request.user,
            old_content=old_content,
            new_content=new_content,
            reason=reason,
            status="PENDING",
        )

        # -----------------------------------------------------
        # AUDIT LOG
        # -----------------------------------------------------
        create_audit_log(
            request,
            action="CREATE",
            entity="Modification",
            entity_id=modification.id,
            details={
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "clause_id": clause.id if clause else None,
                "clause_title": clause.title if clause else None,
                "status": "PENDING",
                "message": "Modification request created",
            },
        )

        messages.success(
            request,
            "Modification request submitted successfully."
        )

        return redirect("modification_list")

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
    return render(
        request,
        "contracts/modification_form.html",
        {
            "contract": contract,
            "clauses": clauses,
        }
    )





@login_required
def modification_approve(request, modification_id):


    # -----------------------------------------
    # APPROVER PERMISSION
    # ONLY APPROVER CAN APPROVE
    # -----------------------------------------
    if not can_approve_modifications(request.user):
        messages.error(
            request,
            "Only an Approver can approve modification requests."
        )
        return redirect("modification_list")

    # -----------------------------------------
    # GET MODIFICATION
    # -----------------------------------------
    modification = get_object_or_404(
        Modification,
        id=modification_id
    )

    # -----------------------------------------
    # ONLY PENDING REQUESTS
    # -----------------------------------------
    if modification.status != "PENDING":
        messages.error(
            request,
            "Only pending modification requests can be approved."
        )
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    # -----------------------------------------
    # POST ONLY
    # -----------------------------------------
    if request.method != "POST":
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    approval_comment = request.POST.get(
        "approval_comment",
        ""
    ).strip()

    with transaction.atomic():

        contract = modification.contract

        if not contract:
            messages.error(
                request,
                "This modification is not associated with a contract."
            )
            return redirect("modification_list")

        clause = modification.clause

        if not clause:
            messages.error(
                request,
                "This modification is not associated with a clause."
            )
            return redirect(
                "modification_detail",
                modification_id=modification.id
            )

        # -----------------------------------------
        # FIND LATEST VERSION
        # -----------------------------------------
        latest_version = (
            Version.objects
            .filter(contract=contract)
            .order_by("-version_number")
            .first()
        )

        if latest_version:
            next_version_number = (
                latest_version.version_number + 1
            )
        else:
            next_version_number = 1

        # -----------------------------------------
        # APPLY MODIFICATION
        # -----------------------------------------
        clause.content = modification.new_content

        clause.save(
            update_fields=[
                "content",
                "updated_at"
            ]
        )

        # -----------------------------------------
        # CREATE SNAPSHOT
        # -----------------------------------------
        snapshot = create_contract_snapshot(contract)

        # -----------------------------------------
        # CREATE NEW VERSION
        # -----------------------------------------
        new_version = Version.objects.create(
            contract=contract,
            version_number=next_version_number,
            created_by=request.user,
            snapshot=create_contract_snapshot(contract),
            change_summary=f"Approved modification #{modification.id}",
        )

        create_audit_log(
            request,
            action="CREATE",
            entity="Version",
            entity_id=new_version.id,
            details={
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "version_number": new_version.version_number,
                "modification_id": modification.id,
                "message": "New contract version created after modification approval",
            },
        )

        # -----------------------------------------
        # CREATE APPROVAL RECORD
        # -----------------------------------------
        Approval.objects.create(
            contract=contract,
            version=new_version,
            approver=request.user,
            status="Approved",
            comments=approval_comment
        )

        # -----------------------------------------
        # UPDATE MODIFICATION
        # -----------------------------------------
        modification.approval_comment = approval_comment
        modification.rejection_reason = None
        modification.status = "APPROVED"

        modification.save(
            update_fields=[
                "approval_comment",
                "rejection_reason",
                "status"
            ]
        )

        # -----------------------------------------
        # AUDIT LOG
        # -----------------------------------------
        create_audit_log(
            request,
            action="APPROVE",
            entity="Modification",
            entity_id=modification.id,
            details={
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "clause_id": clause.id,
                "clause_title": clause.title,
                "version_id": new_version.id,
                "version_number": new_version.version_number,
                "comment": approval_comment,
            },
        )

    messages.success(
        request,
        f"Modification approved successfully. "
        f"Version {new_version.version_number} created."
    )

    return redirect(
        "modification_detail",
        modification_id=modification.id
    )






@login_required
def modification_reject(request, modification_id):
    
# -----------------------------------------
# APPROVER PERMISSION
# ONLY APPROVER CAN REJECT
# -----------------------------------------
    if not can_approve_modifications(request.user):
        messages.error(
            request,
            "Only an Approver can reject modification requests."
        )
        return redirect("modification_list")

    # -----------------------------------------
    # GET MODIFICATION
    # -----------------------------------------
    modification = get_object_or_404(
        Modification,
        id=modification_id
    )

    # -----------------------------------------
    # ONLY PENDING REQUESTS
    # -----------------------------------------
    if modification.status != "PENDING":
        messages.error(
            request,
            "Only pending modification requests can be rejected."
        )
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    # -----------------------------------------
    # POST ONLY
    # -----------------------------------------
    if request.method != "POST":
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    rejection_reason = request.POST.get(
        "rejection_reason",
        ""
    ).strip()

    # -----------------------------------------
    # REJECTION REASON REQUIRED
    # -----------------------------------------
    if not rejection_reason:
        messages.error(
            request,
            "Rejection reason is required."
        )

        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    with transaction.atomic():

        contract = modification.contract

        if not contract:
            messages.error(
                request,
                "This modification is not associated with a contract."
            )
            return redirect("modification_list")

        # -----------------------------------------
        # CREATE REJECTION APPROVAL RECORD
        # -----------------------------------------
        Approval.objects.create(
            contract=contract,
            version=None,
            approver=request.user,
            status="Rejected",
            comments=rejection_reason
        )

        # -----------------------------------------
        # UPDATE MODIFICATION
        # -----------------------------------------
        modification.status = "REJECTED"
        modification.rejection_reason = rejection_reason
        modification.approval_comment = ""

        modification.save(
            update_fields=[
                "status",
                "rejection_reason",
                "approval_comment"
            ]
        )

        # -----------------------------------------
        # AUDIT LOG
        # -----------------------------------------
        create_audit_log(
            request,
            action="REJECT",
            entity="Modification",
            entity_id=modification.id,
            details={
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "reason": rejection_reason,
            },
        )

    messages.success(
        request,
        "Modification request rejected successfully."
    )

    return redirect(
        "modification_detail",
        modification_id=modification.id
    )





@login_required
def modification_delete(request, modification_id):

    modification = get_object_or_404(
        Modification,
        id=modification_id
    )

    # Only Admin can delete modification requests
    if not is_administrator(request.user):

        messages.error(
            request,
            "You are not authorized to delete modification requests."
        )

        return redirect("modification_list")

    if request.method == "POST":

        deleted_modification_id = modification.id
        contract = modification.contract

        # Create audit log BEFORE deleting the modification
        create_audit_log(
            request,
            action="DELETE",
            entity="Modification",
            entity_id=deleted_modification_id,
            details={
                "contract_id": (
                    contract.id
                    if contract
                    else None
                ),
                "contract_number": (
                    contract.contract_number
                    if contract
                    else None
                ),
                "status": modification.status,
                "message": "Modification request deleted",
            },
        )

        modification.delete()

        messages.success(
            request,
            "Modification request deleted successfully."
        )

        return redirect("modification_list")

    return render(
        request,
        "contracts/modification_confirm_delete.html",
        {
            "modification": modification
        }
    )



def create_contract_snapshot(contract):
    """
    Create a complete snapshot of the current contract
    and all of its clauses.
    """

    return {
        "contract": {
            "id": contract.id,
            "contract_number": contract.contract_number,
            "title": contract.title,
            "description": contract.description,
            "status": contract.status,
            "start_date": (
                contract.start_date.isoformat()
                if contract.start_date
                else None
            ),
            "end_date": (
                contract.end_date.isoformat()
                if contract.end_date
                else None
            ),
        },

        "clauses": [
            {
                "id": clause.id,
                "clause_number": clause.clause_number,
                "title": clause.title,
                "content": clause.content,
                "order": clause.order,
            }
            for clause in contract.clauses.all()
        ],
    }


# =========================================================
# VERSION HISTORY
# =========================================================
@login_required
def version_history(request, contract_id):
    if not is_administrator(request.user):
        return HttpResponseForbidden(
            "Only Admin can view version history."
        )

    contract = get_object_or_404(Contract, id=contract_id)

    versions = contract.versions.select_related(
        "created_by"
    ).order_by("-version_number")

    return render(
        request,
        "contracts/version_history.html",
        {
            "contract": contract,
            "versions": versions,
        }
    )
    



@login_required
def version_detail(request, contract_id, version_id):

    # =========================================================
    # ADMIN ONLY
    # =========================================================

    if not is_administrator(request.user):
        messages.error(
            request,
            "You are not authorized to view version details."
        )
        return redirect("dashboard")

    # =========================================================
    # GET CONTRACT
    # =========================================================

    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    # =========================================================
    # GET VERSION
    # =========================================================

    version = get_object_or_404(
        Version.objects.select_related(
            "contract",
            "created_by"
        ),
        id=version_id,
        contract=contract
    )

    # =========================================================
    # GET SNAPSHOT
    # =========================================================

    snapshot = version.snapshot or {}

    # =========================================================
    # GET CLAUSES FROM SNAPSHOT
    # =========================================================

    clauses = snapshot.get("clauses", [])

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "contracts/version_detail.html",
        {
            "contract": contract,
            "version": version,
            "snapshot": snapshot,
            "clauses": clauses,
        }
    )



@login_required
def version_history(request):

    if not is_administrator(request.user):
        messages.error(
            request,
            "You are not authorized to view version history."
        )
        return redirect("dashboard")

    versions = Version.objects.select_related(
        "contract",
        "created_by"
    ).order_by("-created_at")

    return render(
        request,
        "contracts/version_history.html",
        {
            "versions": versions,
        }
    )




@login_required
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)

        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.save()

            create_audit_log(
                request,
                "UPDATE",
                "User",
                request.user.id,
                {"action": "Password changed"}
            )

            logout(request)
            messages.success(
                request,
                "Password changed successfully. Please login again."
            )
            return redirect("web_login")
    else:
        form = ChangePasswordForm(request.user)

    return render(
        request,
        "contracts/change_password.html",
        {"form": form}
    )