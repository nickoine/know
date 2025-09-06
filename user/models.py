# Built-in
from __future__ import annotations

# External
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser

# Internal
from cmn.base_model import BaseModel


class User(BaseModel, AbstractUser):
    """
    User model representing application users with support for multiple
    registration methods, verification tracking, and custom metadata.
    """

    # a username field
    # first_name and last_name
    # email
    # password
    # is_staff (a flag that controls access to the admin site)
    # is_active (whether the user account is considered active)
    # is_superuser (whether the user has all permissions)
    # last_login (timestamp of last authentication)
    # date_joined (timestamp of account creation)

    # Registration method choices
    REG_EMAIL: str = 'email'
    REG_GOOGLE: str = 'google'

    REGISTRATION_CHOICES: list[tuple[str, str]] = [
        (REG_EMAIL, 'Email'),
        (REG_GOOGLE, 'Google'),
    ]

    registration_method: models.CharField = models.CharField(
        max_length=20,
        choices=REGISTRATION_CHOICES,
        help_text=_('Method used for account registration.'),
    )
# If someone explicitly sets "is_verified": true or "is_verified": false in their request, that value will override the default.
    is_verified: models.BooleanField = models.BooleanField(
        blank=True,
        default=False,
        verbose_name=_('Verification status'),
        help_text=_('True = verified, False = unverified'),
    )

    date_verified: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Verification date'),
        help_text=_('Datetime when the user was verified'),
    )

    metadata: models.JSONField = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata'),
        help_text=_('Optional JSON with browser, device, geolocation, etc.'),
    )

    def __str__(self) -> str:
        """
        Human-readable representation, showing email and registration method.
        """
        return f"User {self.email or '[unsaved]'} via {self.registration_method or '[unknown]'}"


    @property
    def age_days(self) -> int | None:
        """
        Compute the account age in days since date_joined.

        :return: Days since join or None if date_joined is unset.
        """
        if self.date_joined:
            return (timezone.now() - self.date_joined).days
        return None


    class Meta:
        verbose_name: str = _('User')
        verbose_name_plural: str = _('Users')
        ordering: list[str] = ['date_joined']
        app_label = "user"

        constraints = [
            # Enforce unique, case-insensitive usernames
            models.UniqueConstraint(
                Lower('username'),
                name='unique_lower_username'
            )
        ]

        indexes = [
            # Index for efficient lookups by verification status
            models.Index(
                fields=['is_verified'],
                name='verified_user_lookup_idx'
            )
        ]

        permissions = [
            ('view_users', 'Ability to list and view user records'),
            ('change_user_status', 'Grant or revoke a user’s verification status'),
            ('view_submissions', 'See all questionnaire submissions'),
            ('approve_submissions', 'Mark verification submissions as approved'),
            ('reject_submissions', 'Mark verification submissions as failed and trigger re‑submission flows'),
            ('assign_questionnaires', 'Allocate private questionnaires to specific user accounts or groups'),
            ('view_audit_logs', 'Access a history of critical actions'),
            ('export_data', 'Download user or submission data in CSV/JSON for reporting or compliance'),
            ('manage_staff', 'Create or modify other admin/staff accounts'),
        ]
