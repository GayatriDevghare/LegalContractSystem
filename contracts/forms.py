from os import name
import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.serializers import python
from .models import (
    User,
    Role,
    Contract,
    Document,
    Clause,
    Modification,
)

User = get_user_model()


class UserCreateForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Password"
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "role",
            "is_active",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data["password"]

        user.set_password(password)

        if commit:
            user.save()

        return user



class RegistrationForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
            }
        )
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.all().order_by("name"),
        empty_label="Select Role",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        )
    )

    class Meta:
        model = User
        fields = ["username", "password", "email", "role"]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter email address",
                }
            ),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()

        if len(username) < 6:
            raise forms.ValidationError(
                "Username must be at least 6 characters long."
            )

        if not re.search(r"[A-Z]", username):
            raise forms.ValidationError(
                "Username must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", username):
            raise forms.ValidationError(
                "Username must contain at least one lowercase letter."
            )

        if not re.search(r"[0-9]", username):
            raise forms.ValidationError(
                "Username must contain at least one number."
            )

        if not re.search(r"[^A-Za-z0-9]", username):
            raise forms.ValidationError(
                "Username must contain at least one special character."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already registered."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()

        if not email:
            raise forms.ValidationError(
                "Email address is required."
            )

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "This email address is already registered."
            )

        return email


    def clean_password(self):
        password = self.cleaned_data.get("password", "")

        if len(password) < 6:
            raise forms.ValidationError(
                "Password must be at least 6 characters long."
            )

        if not re.search(r"[A-Z]", password):
            raise forms.ValidationError(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", password):
            raise forms.ValidationError(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"[0-9]", password):
            raise forms.ValidationError(
                "Password must contain at least one number."
            )

        if not re.search(r"[^A-Za-z0-9]", password):
            raise forms.ValidationError(
                "Password must contain at least one special character."
            )

        return password


    def save(self, commit=True):
        user = super().save(commit=False)

        # Password is stored as a secure Django hash
        user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            user.save()

        return user



class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter current password",
        })
    )

    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter new password",
        })
    )

    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new password",
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")

        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Current password is incorrect."
            )

        return password

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")

        if len(password) < 6:
            raise forms.ValidationError(
                "New password must be at least 6 characters long."
            )

        if not any(char.isupper() for char in password):
            raise forms.ValidationError(
                "New password must contain at least one uppercase letter."
            )

        if not any(char.islower() for char in password):
            raise forms.ValidationError(
                "New password must contain at least one lowercase letter."
            )

        if not any(char.isdigit() for char in password):
            raise forms.ValidationError(
                "New password must contain at least one number."
            )

        if not any(not char.isalnum() for char in password):
            raise forms.ValidationError(
                "New password must contain at least one special character."
            )

        if self.user.check_password(password):
            raise forms.ValidationError(
                "New password must be different from your current password."
            )

        return password

    def clean(self):
        cleaned_data = super().clean()

        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error(
                    "confirm_password",
                    "New passwords do not match."
                )

        return cleaned_data


class ModificationForm(forms.ModelForm):
    class Meta:
        model = Modification
        fields = [
            "clause",
            "new_content",
            "reason",
        ]

        widgets = {
            "clause": forms.Select(attrs={
                "class": "form-control"
            }),
            "new_content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 8,
                "placeholder": "Enter the modified clause content"
            }),
            "reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter reason for modification"
            }),
        }



class UserUpdateForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="New Password"
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "role",
            "is_active",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user
    

class ContractForm(forms.ModelForm):
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control"
            }
        )
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control"
            }
        )
    )

    class Meta:

        model = Contract

        fields = [
            "contract_number",
            "title",
            "description",
            "status",
            "start_date",
            "end_date",
        ]

        widgets = {

            "contract_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter contract number"
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter contract title"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter contract description",
                    "rows": 5
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:

            raise forms.ValidationError(
                "End date cannot be earlier than start date."
            )

        return cleaned_data
    
    


class DocumentForm(forms.ModelForm):

    class Meta:
        model = Document

        fields = [
            "contract",
            "name",
            "document_type",
            "file",
        ]

    def __init__(self, *args, user=None, **kwargs):

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:

            role = (
                user.role.name.strip().lower()
                if user.role
                else ""
            )

            # Admin and Contract Manager
            # can select from all contracts
            if user.is_superuser or role in [
                "admin",
                "contract manager",
            ]:
                self.fields["contract"].queryset = (
                    Contract.objects.all()
                    .order_by("-created_at")
                )

            # User can select only their own contracts
            elif role == "user":
                self.fields["contract"].queryset = (
                    Contract.objects.filter(
                        created_by=user
                    ).order_by("-created_at")
                )

            # Approver and other roles
            # cannot select any contract
            else:
                self.fields["contract"].queryset = (
                    Contract.objects.none()
                )






class RoleForm(forms.ModelForm):
    
    class Meta:
        model = Role
        fields = ["name", "description"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter role name",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter role description",
                "rows": 4,
            }),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Role name is required."
            )

        queryset = Role.objects.filter(
            name__iexact=name
        )

        # Don't consider the current role a duplicate while editing
        if self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise forms.ValidationError(
                "A role with this name already exists."
            )

        return name



class UserProfileForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "profile_photo",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter first name"
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter last name"
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter email address"
                }
            ),

            "profile_photo": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*"
                }
            ),
        }
    
    
class PasswordChangeForm(forms.Form):
    
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter current password"
            }
        )
    )

    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter new password"
            }
        )
    )

    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm new password"
            }
        )
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")

        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                "Current password is incorrect."
            )

        return old_password

    def clean(self):
        cleaned_data = super().clean()

        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError(
                    "New passwords do not match."
                )

        return cleaned_data



class ClauseForm(forms.ModelForm):
    class Meta:
        model = Clause
        fields = [
            "clause_number",
            "title",
            "content",
            "order",
        ]

        widgets = {
            "clause_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter clause number"
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter clause title"
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Enter clause content"
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Enter display order"
                }
            ),
        }