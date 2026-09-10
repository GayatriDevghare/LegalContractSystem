from django.contrib.auth import authenticate
from django.http import FileResponse
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

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

from .serializers import (
    RoleSerializer,
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ContractSerializer,
    DocumentSerializer,
    ClauseSerializer,
    ModificationSerializer,
    VersionSerializer,
    ApprovalSerializer,
    AuditLogSerializer,
)

from .permissions import RoleBasedPermission, IsAdministrator



def create_audit_log(
    request,
    action,
    entity,
    entity_id=None,
    details=None
):

    AuditLog.objects.create(
        user=request.user
        if request.user.is_authenticated
        else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details or {},
        ip_address=request.META.get("REMOTE_ADDR"),
    )




@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():

        user = serializer.save()

        token, created = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                "message": "Registration successful.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": (
                        user.role.name
                        if user.role
                        else None
                    ),
                },
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )





@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):

    serializer = LoginSerializer(
        data=request.data
    )

    if not serializer.is_valid():

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]

    user = authenticate(
        username=username,
        password=password,
    )

    if user is None:

        return Response(
            {
                "error": "Invalid username or password."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:

        return Response(
            {
                "error": "User account is inactive."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    token, created = Token.objects.get_or_create(
        user=user
    )

    create_audit_log(
        request,
        "LOGIN",
        "User",
        user.id,
        {
            "username": user.username,
        },
    )

    return Response(
        {
            "message": "Login successful.",
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": (
                    user.role.name
                    if user.role
                    else None
                ),
            },
        },
        status=status.HTTP_200_OK,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):

    create_audit_log(
        request,
        "LOGOUT",
        "User",
        request.user.id,
        {
            "username": request.user.username,
        },
    )

    Token.objects.filter(
        user=request.user
    ).delete()

    return Response(
        {
            "message": "Logout successful."
        },
        status=status.HTTP_200_OK,
    )


class RoleViewSet(viewsets.ModelViewSet):

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdministrator]

    def perform_create(self, serializer):

        role = serializer.save()

        create_audit_log(
            self.request,
            "CREATE",
            "Role",
            role.id,
            {
                "name": role.name,
            },
        )

    def perform_update(self, serializer):

        role = serializer.save()

        create_audit_log(
            self.request,
            "UPDATE",
            "Role",
            role.id,
            {
                "name": role.name,
            },
        )

    def perform_destroy(self, instance):

        role_id = instance.id
        role_name = instance.name

        create_audit_log(
            self.request,
            "DELETE",
            "Role",
            role_id,
            {
                "name": role_name,
            },
        )

        instance.delete()



class UserViewSet(viewsets.ModelViewSet):

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdministrator]

    def perform_create(self, serializer):

        user = serializer.save()

        create_audit_log(
            self.request,
            "CREATE",
            "User",
            user.id,
            {
                "username": user.username,
            },
        )

    def perform_update(self, serializer):

        user = serializer.save()

        create_audit_log(
            self.request,
            "UPDATE",
            "User",
            user.id,
            {
                "username": user.username,
            },
        )

    def perform_destroy(self, instance):

        user_id = instance.id
        username = instance.username

        create_audit_log(
            self.request,
            "DELETE",
            "User",
            user_id,
            {
                "username": username,
            },
        )

        instance.delete()


class ContractViewSet(viewsets.ModelViewSet):

    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        contract = serializer.save(
            created_by=self.request.user
        )

        create_audit_log(
            self.request,
            "CREATE",
            "Contract",
            contract.id,
            {
                "contract_number": contract.contract_number,
                "title": contract.title,
            },
        )

    def perform_update(self, serializer):

        contract = serializer.save()

        create_audit_log(
            self.request,
            "UPDATE",
            "Contract",
            contract.id,
            {
                "contract_number": contract.contract_number,
                "title": contract.title,
                "status": contract.status,
            },
        )

    def perform_destroy(self, instance):

        contract_id = instance.id
        contract_number = instance.contract_number

        create_audit_log(
            self.request,
            "DELETE",
            "Contract",
            contract_id,
            {
                "contract_number": contract_number,
            },
        )

        instance.delete()





class DocumentViewSet(viewsets.ModelViewSet):

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        document = serializer.save(
            uploaded_by=self.request.user
        )

        create_audit_log(
            self.request,
            "UPLOAD",
            "Document",
            document.id,
            {
                "name": document.name,
                "contract_id": document.contract_id,
            },
        )

    def perform_update(self, serializer):

        document = serializer.save()

        create_audit_log(
            self.request,
            "UPDATE",
            "Document",
            document.id,
            {
                "name": document.name,
            },
        )

    def perform_destroy(self, instance):

        document_id = instance.id
        document_name = instance.name

        create_audit_log(
            self.request,
            "DELETE",
            "Document",
            document_id,
            {
                "name": document_name,
            },
        )

        instance.delete()

    @action(
        detail=True,
        methods=["get"],
        url_path="download",
    )
    def download(self, request, pk=None):

        document = self.get_object()

        create_audit_log(
            request,
            "DOWNLOAD",
            "Document",
            document.id,
            {
                "name": document.name,
                "file": document.file.name,
            },
        )

        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.name,
        )



class ClauseViewSet(viewsets.ModelViewSet):

    queryset = Clause.objects.all()
    serializer_class = ClauseSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        clause = serializer.save()

        create_audit_log(
            self.request,
            "CREATE",
            "Clause",
            clause.id,
            {
                "clause_number": clause.clause_number,
                "title": clause.title,
            },
        )

    def perform_update(self, serializer):

        clause = serializer.save()

        create_audit_log(
            self.request,
            "UPDATE",
            "Clause",
            clause.id,
            {
                "clause_number": clause.clause_number,
                "title": clause.title,
            },
        )

    def perform_destroy(self, instance):

        clause_id = instance.id
        clause_number = instance.clause_number

        create_audit_log(
            self.request,
            "DELETE",
            "Clause",
            clause_id,
            {
                "clause_number": clause_number,
            },
        )

        instance.delete()




class ModificationViewSet(viewsets.ModelViewSet):

    queryset = Modification.objects.all()
    serializer_class = ModificationSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        modification = serializer.save(
            modified_by=self.request.user
        )

        create_audit_log(
            self.request,
            "CREATE",
            "Modification",
            modification.id,
            {
                "clause_id": modification.clause_id,
                "modified_by": modification.modified_by_id,
                "reason": modification.reason,
            },
        )

    def perform_update(self, serializer):

        modification = serializer.save(
            modified_by=self.request.user
        )

        create_audit_log(
            self.request,
            "UPDATE",
            "Modification",
            modification.id,
            {
                "clause_id": modification.clause_id,
                "modified_by": modification.modified_by_id,
                "reason": modification.reason,
            },
        )

    def perform_destroy(self, instance):

        modification_id = instance.id
        clause_id = instance.clause_id

        create_audit_log(
            self.request,
            "DELETE",
            "Modification",
            modification_id,
            {
                "clause_id": clause_id,
            },
        )

        instance.delete()


# VERSION CRUD


class VersionViewSet(viewsets.ModelViewSet):

    queryset = Version.objects.all()
    serializer_class = VersionSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        version = serializer.save(
            created_by=self.request.user
        )

        create_audit_log(
            self.request,
            "CREATE",
            "Version",
            version.id,
            {
                "contract_id": version.contract_id,
                "version_number": version.version_number,
            },
        )

    def perform_update(self, serializer):

        version = serializer.save(
            created_by=self.request.user
        )

        create_audit_log(
            self.request,
            "UPDATE",
            "Version",
            version.id,
            {
                "contract_id": version.contract_id,
                "version_number": version.version_number,
            },
        )

    def perform_destroy(self, instance):

        version_id = instance.id
        contract_id = instance.contract_id
        version_number = instance.version_number

        create_audit_log(
            self.request,
            "DELETE",
            "Version",
            version_id,
            {
                "contract_id": contract_id,
                "version_number": version_number,
            },
        )

        instance.delete()




class ApprovalViewSet(viewsets.ModelViewSet):

    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):

        approval_status = serializer.validated_data.get(
            "status"
        )

        if approval_status == "Approved":

            approval = serializer.save(
                approver=self.request.user,
                approved_at=timezone.now(),
            )

        else:

            approval = serializer.save(
                approver=self.request.user
            )

        if approval.status == "Approved":
            action_name = "APPROVE"
        elif approval.status == "Rejected":
            action_name = "REJECT"
        else:
            action_name = "CREATE"

        create_audit_log(
            self.request,
            action_name,
            "Approval",
            approval.id,
            {
                "contract_id": approval.contract_id,
                "version_id": approval.version_id,
                "approver_id": approval.approver_id,
                "status": approval.status,
            },
        )

    def perform_update(self, serializer):

        old_status = serializer.instance.status

        new_status = serializer.validated_data.get(
            "status",
            old_status
        )

        if new_status == "Approved":

            approval = serializer.save(
                approver=self.request.user,
                approved_at=timezone.now(),
            )

        else:

            approval = serializer.save(
                approver=self.request.user,
                approved_at=None,
            )

        if approval.status == "Approved":
            action_name = "APPROVE"

        elif approval.status == "Rejected":
            action_name = "REJECT"

        else:
            action_name = "UPDATE"

        create_audit_log(
            self.request,
            action_name,
            "Approval",
            approval.id,
            {
                "contract_id": approval.contract_id,
                "version_id": approval.version_id,
                "old_status": old_status,
                "new_status": approval.status,
                "approver_id": approval.approver_id,
                "comments": approval.comments,
            },
        )

    def perform_destroy(self, instance):

        approval_id = instance.id
        contract_id = instance.contract_id

        create_audit_log(
            self.request,
            "DELETE",
            "Approval",
            approval_id,
            {
                "contract_id": contract_id,
                "version_id": instance.version_id,
            },
        )

        instance.delete()



class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = AuditLog.objects.all().order_by(
        "-timestamp"
    )

    serializer_class = AuditLogSerializer
    permission_classes = [RoleBasedPermission]