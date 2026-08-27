from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status

from .models import (
    Role,
    User,
    Contract,
    Clause,
    Modification,
    Version,
    Approval,
)


class CRUDAPITestCase(APITestCase):

    def setUp(self):

        # Create role
        self.role = Role.objects.create(
            name="Admin",
            description="Administrator"
        )

        # Create user
        self.user = User.objects.create_user(
            username="testadmin",
            email="testadmin@example.com",
            password="Test@12345",
            role=self.role
        )

        # Create authentication token
        self.token = Token.objects.create(
            user=self.user
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

        # Create contract
        self.contract = Contract.objects.create(
            contract_number="CON-TEST-001",
            title="Test Contract",
            description="Test contract description",
            status="Draft",
            created_by=self.user
        )

        # Create clause
        self.clause = Clause.objects.create(
            contract=self.contract,
            clause_number="1",
            title="Payment Clause",
            content="Payment terms"
        )

        # Create version
        self.version = Version.objects.create(
            contract=self.contract,
            version_number=1,
            created_by=self.user,
            snapshot={
                "title": "Test Contract"
            },
            change_summary="Initial version"
        )


    # ========================================================
    # ROLE CRUD
    # ========================================================

    def test_role_list(self):

        response = self.client.get(
            "/api/roles/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )


    def test_role_create(self):

        data = {
            "name": "Manager",
            "description": "Contract manager"
        }

        response = self.client.post(
            "/api/roles/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.assertTrue(
            Role.objects.filter(
                name="Manager"
            ).exists()
        )


    # ========================================================
    # USER CRUD
    # ========================================================

    def test_user_list(self):

        response = self.client.get(
            "/api/users/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )


    def test_user_create(self):

        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUser@123",
            "role": self.role.id
        }

        response = self.client.post(
            "/api/users/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        user = User.objects.get(
            username="newuser"
        )

        self.assertTrue(
            user.check_password("NewUser@123")
        )


    # ========================================================
    # CONTRACT CRUD
    # ========================================================

    def test_contract_list(self):

        response = self.client.get(
            "/api/contracts/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )


    def test_contract_create(self):

        data = {
            "contract_number": "CON-TEST-002",
            "title": "New Test Contract",
            "description": "Created using API",
            "status": "Draft"
        }

        response = self.client.post(
            "/api/contracts/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        contract = Contract.objects.get(
            contract_number="CON-TEST-002"
        )

        self.assertEqual(
            contract.created_by,
            self.user
        )


    def test_contract_update(self):

        data = {
            "contract_number": self.contract.contract_number,
            "title": "Updated Contract",
            "description": "Updated description",
            "status": "Active"
        }

        response = self.client.put(
            f"/api/contracts/{self.contract.id}/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.contract.refresh_from_db()

        self.assertEqual(
            self.contract.title,
            "Updated Contract"
        )


    def test_contract_delete(self):

        contract_id = self.contract.id

        response = self.client.delete(
            f"/api/contracts/{contract_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )

        self.assertFalse(
            Contract.objects.filter(
                id=contract_id
            ).exists()
        )


    # ========================================================
    # CLAUSE CRUD
    # ========================================================

    def test_clause_list(self):

        response = self.client.get(
            "/api/clauses/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )


    def test_clause_create(self):

        data = {
            "contract": self.contract.id,
            "clause_number": "2",
            "title": "Confidentiality",
            "content": "Confidentiality terms"
        }

        response = self.client.post(
            "/api/clauses/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )


    # ========================================================
    # MODIFICATION CRUD
    # ========================================================

    def test_modification_create(self):

        data = {
            "clause": self.clause.id,
            "old_content": "Old clause",
            "new_content": "New clause",
            "reason": "Updated terms"
        }

        response = self.client.post(
            "/api/modifications/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        modification = Modification.objects.latest(
            "id"
        )

        self.assertEqual(
            modification.modified_by,
            self.user
        )


    # ========================================================
    # VERSION CRUD
    # ========================================================

    def test_version_create(self):

        data = {
            "contract": self.contract.id,
            "version_number": 2,
            "snapshot": {
                "title": "Updated Contract"
            },
            "change_summary": "Updated contract version"
        }

        response = self.client.post(
            "/api/versions/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        version = Version.objects.get(
            contract=self.contract,
            version_number=2
        )

        self.assertEqual(
            version.created_by,
            self.user
        )


    # ========================================================
    # APPROVAL CRUD
    # ========================================================

    def test_approval_create(self):

        data = {
            "contract": self.contract.id,
            "version": self.version.id,
            "status": "Pending",
            "comments": "Waiting for approval"
        }

        response = self.client.post(
            "/api/approvals/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        approval = Approval.objects.latest(
            "id"
        )

        self.assertEqual(
            approval.approver,
            self.user
        )


    def test_approval_approved_timestamp(self):

        data = {
            "contract": self.contract.id,
            "version": self.version.id,
            "status": "Approved",
            "comments": "Approved successfully"
        }

        response = self.client.post(
            "/api/approvals/",
            data,
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        approval = Approval.objects.latest(
            "id"
        )

        self.assertIsNotNone(
            approval.approved_at
        )