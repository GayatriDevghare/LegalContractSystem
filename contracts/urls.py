from django.urls import path
from . import views

urlpatterns = [


# =========================================================
# USER MANAGEMENT
# =========================================================

path(
    "users/",
    views.user_list,
    name="user_list"
),

path(
    "users/add/",
    views.user_create,
    name="user_create"
),

path(
    "users/<int:user_id>/edit/",
    views.user_update,
    name="user_update"
),

path(
    "users/<int:user_id>/delete/",
    views.user_delete,
    name="user_delete"
),


# =========================================================
# CONTRACT MANAGEMENT
# =========================================================

path(
    "contracts/",
    views.contract_list,
    name="contract_list"
),

path(
    "contracts/add/",
    views.contract_create,
    name="contract_create"
),

path(
    "contracts/<int:contract_id>/",
    views.contract_detail,
    name="contract_detail"
),

path(
    "contracts/<int:contract_id>/edit/",
    views.contract_update,
    name="contract_update"
),

path(
    "contracts/<int:contract_id>/delete/",
    views.contract_delete,
    name="contract_delete"
),


# =========================================================
# DOCUMENT MANAGEMENT
# =========================================================

path(
    "documents/",
    views.document_list,
    name="document_list"
),

path(
    "documents/<int:document_id>/view/",
    views.document_view,
    name="document_view"
),

path(
    "documents/<int:document_id>/download/",
    views.document_download,
    name="document_download"
),

# Create document 
path( "documents/add/", views.document_create, name="document_create" ),

path(
    "documents/<int:document_id>/edit/",
    views.document_update,
    name="document_update"
),

path(
    "documents/<int:document_id>/delete/",
    views.document_delete,
    name="document_delete"
),


# =========================================================
# CLAUSE MANAGEMENT
# =========================================================

# All clauses
path(
    "clauses/",
    views.clause_list,
    name="clause_list"
),

# Clauses belonging to a particular contract
path(
    "contracts/<int:contract_id>/clauses/",
    views.clause_list,
    name="contract_clause_list"
),

# Create clause for a particular contract
path(
    "contracts/<int:contract_id>/clauses/add/",
    views.clause_create,
    name="clause_create"
),

# Edit clause
path(
    "clauses/<int:clause_id>/edit/",
    views.clause_update,
    name="clause_update"
),

# Delete clause
path(
    "clauses/<int:clause_id>/delete/",
    views.clause_delete,
    name="clause_delete"
),


path(
    "clauses/<int:clause_id>/",
    views.clause_detail,
    name="clause_detail"
),


path(
    "clauses/create/",
    views.clause_create_select,
    name="clause_create_select"
),





# =========================================================
# MODIFICATION REQUESTS
# =========================================================

# Modification request list
path(
    "modifications/",
    views.modification_list,
    name="modification_list"
),

# Create modification request
path(
    "modifications/add/",
    views.modification_create,
    name="modification_create"
),

# Approve modification
path(
    "modifications/<int:modification_id>/approve/",
    views.modification_approve,
    name="modification_approve"
),

path(
    "modifications/<int:modification_id>/",
    views.modification_detail,
    name="modification_detail"
),


# Reject modification
path(
    "modifications/<int:modification_id>/reject/",
    views.modification_reject,
    name="modification_reject"
),

# Delete modification
path(
    "modifications/<int:modification_id>/delete/",
    views.modification_delete,
    name="modification_delete"
),


# =========================================================
# ROLE MANAGEMENT
# =========================================================

path(
    "roles/",
    views.role_list,
    name="role_list"
),

path(
    "roles/create/",
    views.role_create,
    name="role_create"
),

path(
    "roles/<int:role_id>/edit/",
    views.role_update,
    name="role_update"
),

path(
    "roles/<int:role_id>/delete/",
    views.role_delete,
    name="role_delete"
),


# =========================================================
# PROFILE
# =========================================================

path(
    "profile/",
    views.profile,
    name="profile"
),

path(
    "profile/edit/",
    views.profile_edit,
    name="profile_edit"
),

path(
    "profile/remove-photo/",
    views.profile_remove_photo,
    name="profile_remove_photo"
),

path(
    "profile/password/",
    views.password_change,
    name="password_change"
),


# =========================================================
# DASHBOARD
# =========================================================

path(
    "dashboard/users/",
    views.dashboard_users,
    name="dashboard_users"
),

path(
    "dashboard/active-users/",
    views.dashboard_active_users,
    name="dashboard_active_users"
),

path(
    "dashboard/today-users/",
    views.dashboard_today_users,
    name="dashboard_today_users"
),

path(
    "dashboard/roles/",
    views.dashboard_roles,
    name="dashboard_roles"
),


]
