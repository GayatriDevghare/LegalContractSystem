from rest_framework import serializers

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


# ============================================================
# ROLE SERIALIZER
# ============================================================

class RoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = "__all__"


# ============================================================
# USER SERIALIZER
# ============================================================

class UserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "role",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True
            }
        }

    def create(self, validated_data):

        password = validated_data.pop(
            "password",
            None
        )

        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()

        return user

    def update(self, instance, validated_data):

        password = validated_data.pop(
            "password",
            None
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        return instance


# ============================================================
# REGISTER SERIALIZER
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "role",
        ]

    def create(self, validated_data):

        password = validated_data.pop(
            "password"
        )

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        return user


# ============================================================
# LOGIN SERIALIZER
# ============================================================

class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )


# ============================================================
# CONTRACT SERIALIZER
# ============================================================

class ContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contract
        fields = "__all__"

        read_only_fields = [
            "created_by",
            "created_at",
            "updated_at",
        ]


# ============================================================
# DOCUMENT SERIALIZER
# ============================================================

class DocumentSerializer(serializers.ModelSerializer):

    contract = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all()
    )

    uploaded_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = Document
        fields = "__all__"

        read_only_fields = [
            "uploaded_by",
        ]


# ============================================================
# CLAUSE SERIALIZER
# ============================================================

class ClauseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Clause
        fields = "__all__"

        read_only_fields = [
            "created_at",
            "updated_at",
        ]


# ============================================================
# MODIFICATION SERIALIZER
# ============================================================

class ModificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Modification
        fields = "__all__"

        read_only_fields = [
            "modified_by",
            "modified_at",
        ]


# ============================================================
# VERSION SERIALIZER
# ============================================================

class VersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Version
        fields = "__all__"

        read_only_fields = [
            "created_by",
            "created_at",
        ]


# ============================================================
# APPROVAL SERIALIZER
# ============================================================

class ApprovalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Approval
        fields = "__all__"

        read_only_fields = [
            "approver",
            "approved_at",
            "created_at",
        ]


# ============================================================
# AUDIT LOG SERIALIZER
# ============================================================

class AuditLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = AuditLog
        fields = "__all__"

        read_only_fields = [
            "timestamp",
        ]