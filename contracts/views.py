
from django.db.models import Q
from django.http import HttpResponse, FileResponse, HttpResponseForbidden
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model

from .models import (
    Contract,
    Document,
    Clause,
    Role,
    Modification,
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
)


User = get_user_model()


# =========================================================
# AUTHENTICATION
# =========================================================

class UserLoginView(LoginView):

    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard")


class UserLogoutView(LogoutView):

    next_page = reverse_lazy("web_login")


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
    """
    Only users with the Approver role can
    approve or reject modification requests.
    """
    if not user.is_authenticated:
        return False

    return get_user_role(user) == "approver"



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

            form.save()

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

    if user == request.user:

        messages.error(
            request,
            "You cannot delete your own account."
        )

        return redirect("user_list")

    if request.method == "POST":

        username = user.username

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

            form.save()

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

            form.save()

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

    # Only show contracts created by the logged-in user
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

            # Store the logged-in user as uploader
            document.uploaded_by = request.user

            document.save()

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

    # Admin permission
    is_admin = (
        request.user.is_superuser
        or (
            request.user.role
            and request.user.role.name.strip().lower() == "admin"
        )
    )

    # Contract Manager permission
    is_manager = (
        request.user.role
        and request.user.role.name.strip().lower() == "contract manager"
    )

    # User who created the contract
    is_contract_owner = (
        document.contract.created_by == request.user
    )

    # User who uploaded the document
    is_document_uploader = (
        document.uploaded_by == request.user
    )

    # Allow any of these users
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
            instance=document
        )

        if form.is_valid():

            updated_document = form.save(commit=False)

            # Keep the original uploader
            updated_document.uploaded_by = document.uploaded_by

            updated_document.save()

            messages.success(
                request,
                "Document updated successfully."
            )

            return redirect("document_list")

    else:

        form = DocumentForm(
            instance=document
        )

    return render(
        request,
        "contracts/document_form.html",
        {
            "form": form,
            "document": document,
        }
    )




@login_required
def document_delete(request, document_id):

    role = get_user_role(request.user)

    if role in [
        "admin",
        "contract manager",
    ] or request.user.is_superuser:

        document = get_object_or_404(
            Document,
            id=document_id
        )

    elif role == "user":

        document = get_object_or_404(
            Document,
            id=document_id,
            contract__created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to delete documents."
        )

        return redirect("document_list")

    if request.method == "POST":

        document.delete()

        messages.success(
            request,
            "Document deleted successfully."
        )

        return redirect(
            "document_list"
        )

    return render(
        request,
        "contracts/document_confirm_delete.html",
        {
            "document": document
        }
    )
# =========================================================
# CONTRACT MANAGEMENT
# =========================================================

@login_required
def contract_list(request):

    contracts = Contract.objects.select_related(
        "created_by"
    ).prefetch_related(
        "documents",
        "clauses"
    ).all()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        contracts = contracts.filter(
            Q(
                contract_number__icontains=search
            )
            |
            Q(
                title__icontains=search
            )
        )

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status:

        contracts = contracts.filter(
            status=status
        )

    return render(
        request,
        "contracts/contract_list.html",
        {
            "contracts": contracts,
            "search": search,
            "selected_status": status,
            "status_choices": Contract.STATUS_CHOICES,
        }
    )


@login_required
def contract_detail(request, contract_id):

    contract = get_object_or_404(
        Contract.objects.select_related(
            "created_by"
        ).prefetch_related(
            "documents",
            "clauses"
        ),
        id=contract_id
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

    # Admin, Contract Manager, and User can create contracts
    if role not in ["admin", "contract manager", "user"] and not request.user.is_superuser:
        messages.error(request, "You are not authorized to create contracts.")
        return redirect("dashboard")

    if request.method == "POST":
        contract_form = ContractForm(request.POST)

        # First validate the contract
        if contract_form.is_valid():
            contract = contract_form.save(commit=False)
            contract.created_by = request.user
            contract.save()

            # Document is optional during contract creation
            if request.FILES.get("file"):
                document_form = DocumentForm(request.POST, request.FILES)

                # Contract is assigned automatically
                document_form.fields["contract"].required = False

                if document_form.is_valid():
                    document = document_form.save(commit=False)
                    document.contract = contract
                    document.uploaded_by = request.user
                    document.save()
                else:
                    # If document has an error, delete the contract
                    contract.delete()

                    messages.error(
                        request,
                        "Document upload failed. Please check the document details."
                    )

                    return render(
                        request,
                        "contracts/contract_form.html",
                        {
                            "contract_form": contract_form,
                            "document_form": document_form,
                            "title": "Create Contract",
                        },
                    )

            messages.success(
                request,
                "Contract created successfully."
            )

            return redirect("contract_list")

        # Contract form is invalid
        document_form = DocumentForm(request.POST, request.FILES)

    else:
        contract_form = ContractForm()
        document_form = DocumentForm()

    return render(
        request,
        "contracts/contract_form.html",
        {
            "contract_form": contract_form,
            "document_form": document_form,
            "title": "Create Contract",
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

    # Approver cannot edit contracts
    else:
        messages.error(
            request,
            "You are not authorized to edit this contract."
        )
        return redirect("contract_list")

    if request.method == "POST":
        form = ContractForm(
            request.POST,
            instance=contract
        )

        if form.is_valid():
            form.save()

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

    role = get_user_role(request.user)

    # Admin and Contract Manager can delete any contract.
    if role in ["admin", "contract manager"] or request.user.is_superuser:

        contract = get_object_or_404(
            Contract,
            id=contract_id
        )

    # User can delete only their own contract.
    elif role == "user":

        contract = get_object_or_404(
            Contract,
            id=contract_id,
            created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to delete contracts."
        )

        return redirect("dashboard")

    if request.method == "POST":

        contract.delete()

        messages.success(
            request,
            "Contract deleted successfully."
        )

        return redirect(
            "contract_list"
        )

    return render(
        request,
        "contracts/contract_confirm_delete.html",
        {
            "contract": contract
        }
    )


# =========================================================
# CLAUSE MANAGEMENT
# =========================================================

@login_required
def clause_list(request, contract_id=None):

    if contract_id:

        # All authenticated users can view clauses
        # of any contract they can access.
        contract = get_object_or_404(
            Contract,
            id=contract_id
        )

        clauses = Clause.objects.filter(
            contract=contract
        ).order_by(
            "order",
            "id"
        )

    else:

        contract = None

        if can_view_all_data(request.user):

            clauses = Clause.objects.select_related(
                "contract"
            ).all().order_by(
                "contract_id",
                "order",
                "id"
            )

        else:

            clauses = Clause.objects.select_related(
                "contract"
            ).filter(
                contract__created_by=request.user
            ).order_by(
                "contract_id",
                "order",
                "id"
            )

    return render(
        request,
        "contracts/clause_list.html",
        {
            "clauses": clauses,
            "contract": contract,
        }
    )



@login_required
def clause_create(request, contract_id):
    contract = get_object_or_404(
        Contract,
        id=contract_id
    )

    role = get_user_role(request.user)

    # Admin and Contract Manager can add clauses to any contract
    if role in ["admin", "contract manager"] or request.user.is_superuser:
        pass

    # User can add clauses ONLY to their own contract
    elif role == "user":
        if contract.created_by_id != request.user.id:
            messages.error(
                request,
                "You can only add clauses to your own contracts."
            )
            return redirect("clause_list")

    # Approver and other roles cannot add clauses
    else:
        messages.error(
            request,
            "You are not authorized to add clauses."
        )
        return redirect("clause_list")

    if request.method == "POST":
        form = ClauseForm(request.POST)

        if form.is_valid():
            clause = form.save(commit=False)
            clause.contract = contract
            clause.save()

            messages.success(
                request,
                "Clause added successfully."
            )

            return redirect(
                "clause_list",
                contract_id=contract.id
            )

    else:
        form = ClauseForm()

    return render(
        request,
        "contracts/clause_form.html",
        {
            "form": form,
            "contract": contract,
            "title": "Add Clause",
        },
    )





@login_required
def clause_update(request, clause_id):

    role = get_user_role(request.user)

    if role in ["admin", "contract manager"] or request.user.is_superuser:

        clause = get_object_or_404(
            Clause,
            id=clause_id
        )

    elif role == "user":

        clause = get_object_or_404(
            Clause,
            id=clause_id,
            contract__created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to update clauses."
        )

        return redirect("dashboard")

    if request.method == "POST":

        form = ClauseForm(
            request.POST,
            instance=clause
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Clause updated successfully."
            )

            return redirect(
                "contract_clause_list",
                contract_id=clause.contract.id
            )

    else:

        form = ClauseForm(
            instance=clause
        )

    return render(
        request,
        "contracts/clause_form.html",
        {
            "form": form,
            "contract": clause.contract,
            "title": "Edit Clause",
        }
    )



@login_required
def clause_detail(request, clause_id):
    clause = get_object_or_404(Clause, id=clause_id)

    return render(
        request,
        "contracts/clause_detail.html",
        {
            "clause": clause
        }
    )



@login_required
def clause_create_select(request):

    # Show only contracts created by the logged-in user
    contracts = Contract.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    return render(
        request,
        "contracts/clause_create_select.html",
        {
            "contracts": contracts
        }
    )



@login_required
def clause_delete(request, clause_id):

    role = get_user_role(request.user)

    if role in ["admin", "contract manager"] or request.user.is_superuser:

        clause = get_object_or_404(
            Clause,
            id=clause_id
        )

    elif role == "user":

        clause = get_object_or_404(
            Clause,
            id=clause_id,
            contract__created_by=request.user
        )

    else:

        messages.error(
            request,
            "You are not authorized to delete clauses."
        )

        return redirect("dashboard")

    contract_id = clause.contract.id

    if request.method == "POST":

        clause.delete()

        messages.success(
            request,
            "Clause deleted successfully."
        )

        return redirect(
            "contract_clause_list",
            contract_id=contract_id
        )

    return render(
        request,
        "contracts/clause_confirm_delete.html",
        {
            "clause": clause,
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
            "modified_by"
        ),
        id=modification_id
    )

    role = get_user_role(request.user)

    # Admin / Approver can view all requests
    if role in ["admin", "approver"] or request.user.is_superuser:
        pass

    # User can view ONLY their own modification requests
    elif role == "user":
        if modification.modified_by_id != request.user.id:
            messages.error(
                request,
                "You are not authorized to view this modification request."
            )
            return redirect("modification_list")

    # Contract Manager can view requests for their own contracts
    elif role == "contract manager":
        if (
            not modification.contract
            or modification.contract.created_by_id != request.user.id
        ):
            messages.error(
                request,
                "You are not authorized to view this modification request."
            )
            return redirect("modification_list")

    else:
        messages.error(
            request,
            "You are not authorized to view this modification request."
        )
        return redirect("dashboard")

    return render(
        request,
        "contracts/modification_detail.html",
        {
            "modification": modification,
        }
    )


@login_required
def modification_list(request):
    role = get_user_role(request.user)
    
    print("CURRENT USER:", request.user.username)
    print("CURRENT USER ID:", request.user.id)
    print("CURRENT ROLE:", role)

    if role in ["admin", "approver"] or request.user.is_superuser:

        # Admin and Approver can see all requests
        modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).all().order_by("-modified_at")

    elif role == "contract manager":

        # Contract Manager can see requests related
        # to contracts created by them
        modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).filter(
            contract__created_by=request.user
        ).order_by("-modified_at")

    elif role == "user":

        # User can see ONLY their own requests
        modifications = Modification.objects.select_related(
            "contract",
            "clause",
            "modified_by"
        ).filter(
            modified_by=request.user
        ).order_by("-modified_at")
        
        print("USER REQUESTS:", list(
    modifications.values_list(
        "id",
        "modified_by__username",
        "status"
    )
))

    else:

        # Any other role sees nothing
        modifications = Modification.objects.none()

    return render(
        request,
        "contracts/modification_list.html",
        {
            "modifications": modifications,
        }
    )


@login_required
def modification_create(request):
    role = get_user_role(request.user)

    # Users can create modification requests.
    # Admin / Contract Manager / Approver can also access the form.
    if role not in [
        "admin",
        "contract manager",
        "user",
        "approver",
    ] and not request.user.is_superuser:
        messages.error(
            request,
            "You are not authorized to create modification requests."
        )
        return redirect("dashboard")

    # All contracts that the logged-in user is allowed to view
    contracts = Contract.objects.all().order_by("-id")

    if request.method == "POST":
        form = ModificationForm(request.POST)

        # Make all viewable contracts available in the form
        if "contract" in form.fields:
            form.fields["contract"].queryset = contracts

        if form.is_valid():
            modification = form.save(commit=False)

            # Set the user who submitted the request
            modification.modified_by = request.user

            # New modification requests always start as PENDING
            modification.status = "PENDING"

            modification.save()

            messages.success(
                request,
                "Modification request submitted successfully."
            )

            return redirect("modification_list")

    else:
        form = ModificationForm()

        # User can select any contract they can view
        if "contract" in form.fields:
            form.fields["contract"].queryset = contracts

    return render(
        request,
        "contracts/modification_form.html",
        {
            "form": form,
            "title": "Create Modification Request",
        },
    )





@login_required
def modification_approve(request, modification_id):

    modification = get_object_or_404(
        Modification,
        id=modification_id
    )

    if not can_approve_modifications(request.user):
        messages.error(
            request,
            "Only an Approver can approve modification requests."
        )
        return redirect("modification_list")

    if modification.status != "PENDING":
        messages.error(
            request,
            "Only pending modification requests can be processed."
        )
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    if request.method != "POST":
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    approval_comment = request.POST.get(
        "approval_comment",
        ""
    ).strip()

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

    messages.success(
        request,
        "Modification request approved successfully."
    )

    return redirect(
        "modification_detail",
        modification_id=modification.id
    )




@login_required
def modification_reject(request, modification_id):

    modification = get_object_or_404(
        Modification,
        id=modification_id
    )

    if not can_approve_modifications(request.user):
        messages.error(
            request,
            "Only an Approver can reject modification requests."
        )
        return redirect("modification_list")

    if modification.status != "PENDING":
        messages.error(
            request,
            "Only pending modification requests can be processed."
        )
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    if request.method != "POST":
        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    rejection_reason = request.POST.get(
        "rejection_reason",
        ""
    ).strip()

    if not rejection_reason:
        messages.error(
            request,
            "Please provide a rejection reason."
        )

        return redirect(
            "modification_detail",
            modification_id=modification.id
        )

    modification.rejection_reason = rejection_reason
    modification.approval_comment = None
    modification.status = "REJECTED"

    modification.save(
        update_fields=[
            "rejection_reason",
            "approval_comment",
            "status"
        ]
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