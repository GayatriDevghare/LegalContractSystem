from django.db import models
from django.contrib.auth.models import AbstractUser


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    
    
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username


class Contract(models.Model):

    STATUS_CHOICES = [
    ("Draft", "Draft"),
    ("Active", "Active"),
    ("Expired", "Expired"),
    ("Terminated", "Terminated"),
]

    contract_number = models.CharField(
        max_length=100,
        unique=True
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft"
    )

    created_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="created_contracts"
)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.contract_number} - {self.title}"


class Document(models.Model):

    DOCUMENT_TYPES = [
        ("Contract", "Contract"),
        ("Attachment", "Attachment"),
        ("Supporting", "Supporting Document"),
        ("Other", "Other"),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    name = models.CharField(max_length=255)

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPES,
        default="Contract"
    )

    file = models.FileField(
        upload_to="contracts/documents/"
    )

    uploaded_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="uploaded_documents"
)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Clause(models.Model):
    
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="clauses"
    )

    clause_number = models.CharField(max_length=50)

    title = models.CharField(max_length=255)

    content = models.TextField()

    order = models.PositiveIntegerField(
        default=1
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.clause_number} - {self.title}"



class Modification(models.Model):
    
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="modifications"
    )

    clause = models.ForeignKey(
        Clause,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="modifications"
    )

    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modifications"
    )

    old_content = models.TextField()

    new_content = models.TextField()

    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    # Comment added by the Approver
    approval_comment = models.TextField(
        blank=True,
        null=True
    )

    # Reason provided by the Approver when rejecting
    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    modified_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-modified_at"]

    def __str__(self):
        return f"{self.contract} - {self.status}"



class Version(models.Model):

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    version_number = models.PositiveIntegerField()

    created_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="created_versions"
)

    snapshot = models.JSONField(
        default=dict
    )

    change_summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "version_number"],
                name="unique_contract_version"
            )
        ]
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.contract.contract_number} - v{self.version_number}"


class Approval(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="approvals"
    )

    version = models.ForeignKey(
        Version,
        on_delete=models.CASCADE,
        related_name="approvals"
    )

    approver = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="contract_approvals"
)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    comments = models.TextField(blank=True)

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contract} - {self.status}"


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("UPLOAD", "Upload"),
        ("DOWNLOAD", "Download"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    entity = models.CharField(
        max_length=100
    )

    entity_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    details = models.JSONField(
        default=dict,
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.action} - {self.entity} - {self.timestamp}"