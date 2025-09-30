from __future__ import annotations

# External
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Index, Q
from django.contrib.postgres.indexes import GinIndex


# Internal
from cmn.base_model import BaseModel


class Submission(BaseModel):
    """
    An account's submission of a questionnaire.
    """

    QUESTIONNAIRE_TYPE = [('verification', 'Verification'), ('mandatory', 'Mandatory'), ('regular', 'Regular')]
    QUESTIONNAIRE_SCOPE = [('public', 'Public'), ('assigned', 'Assigned')]

    SUBMISSION_STATUSES = [('submitted', 'Submitted'), ('completed', 'Completed'), ('failed', 'Failed'),
                           ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    submission_status = models.CharField(
        max_length=20,
        choices=SUBMISSION_STATUSES,
        default=SUBMISSION_STATUSES[0][0]
    )

    questionnaire = models.ForeignKey(
        'questionnaire.Questionnaire',
        on_delete=models.SET_NULL,
        null=True,
        related_name='submissions',
        verbose_name=_("Questionnaire"),
        help_text=_("The questionnaire being filled.")
    )

    questionnaire_type = models.CharField(
        max_length=50,
        choices=QUESTIONNAIRE_TYPE
    )

    questionnaire_scope = models.CharField(
        max_length=50,
        choices=QUESTIONNAIRE_SCOPE
    )

    user = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='submissions',
        verbose_name=_("User"),
        help_text=_("The user that submitted the questionnaire.")
    )

    submitted_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Submitted At"),
        help_text=_("When the questionnaire was submitted (must be in year/month/days).")
    )

    is_failed = models.BooleanField(
        null=True,
        blank=True,
        default=False,
        help_text=_("After X failed attempts to verify user identity")
    )

    is_orphan = models.BooleanField(
        null=True,
        blank=True,
        default=False,
        help_text=_("Submission becomes orphan, when the user's account and data is deleted")
    )

    patched_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Patched At"),
        help_text=_("Last modification timestamp.")
    )

    staff_id = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patched_submissions',
        help_text=_('Approved or rejected by admin manually.')
    )

    payload = models.OneToOneField(
        'SubmissionPayload',
        on_delete=models.CASCADE,
        related_name='submission',
        verbose_name=_("Payload"),
        null=True,
        blank=True
    )

    docs = models.OneToOneField(
        'SubmissionDocument',
        on_delete=models.CASCADE,
        related_name='submission',
        null=True,
        blank=True
    )


    class Meta:
        verbose_name = _("Submission")
        verbose_name_plural = _("Submissions")

        # Most recent first
        ordering = ['-submitted_at']

        # Prevent duplicate submissions by same user to same questionnaire
        constraints = [
            models.UniqueConstraint(fields=['user', 'questionnaire'], name='uq_user_questionnaire')
        ]

        indexes = [
            # Fast access to all verification-type submissions
            Index(
                fields=["questionnaire_type"],
                name="idx_verification_submissions",
                condition=Q(questionnaire_type='verification')
            ),

            # Query most recent submissions (history or audit trails)
            Index(
                fields=["submitted_at"],
                name="idx_submitted_at"
            ),

            # Used to detect incomplete/stuck submissions
            Index(
                fields=["submission_status"],
                name="idx_submission_status"
            ),
        ]

    def __str__(self):
        return f"Submission#{self.id}. Type: {self.questionnaire_type}. submission_status: {self.submission_status}. User: {self.user.id}"

# todo
class SubmissionPayload(BaseModel):
    """
    Stores full questionnaire responses (as JSON) tied to a single submission.
    One-to-one payload blob for the submission.
    """

    payload = models.JSONField(
        verbose_name=_("Answer"),
        help_text=_("The actual response content (text, choices, file reference, etc.)")
    )

    saved_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = _("SubmissionPayload")
        verbose_name_plural = _("SubmissionPayloads")
        ordering = ['-saved_at']

        indexes = [
            GinIndex(fields=['payload'], name='payload_gin_idx'),
        ]

    def __str__(self):
        return f"Payload for submission under ID {self.id}"



    @property
    def response_summary(self):
        """Extracts a safe string representation of the payload"""

        if isinstance(self.payload, dict):
            return str(list(self.payload.values())[0])[:100]
        return str(self.payload)[:100]


    def clean(self):
        """
        Validates a single question response:
        - Required fields are filled
        - Payload matches question rules
        """

        # Rule: Required questions must have a value
        # Rule: Payload must match validation rules for this question
        pass


class SubmissionDocument(BaseModel):
    """Stores documents for verification within a questionnaire submission."""


    DOCUMENT_TYPES = [('passport', 'Passport'), ('national_id', 'National ID'), ('driver_license', 'Driver License')]


    doc_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES
    )

    doc = models.FileField(
        upload_to='documents/'
    )

    # selfie = models.ImageField(
    #     upload_to='selfies/'
    # )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        verbose_name = _("SubmissionDocument")
        verbose_name_plural = _("SubmissionDocuments")
        ordering = ['-uploaded_at']  # Show latest uploads first

        indexes = [
            Index(fields=['doc_type'], name='idx_by_document_type'),
            Index(fields=['uploaded_at'], name='idx_by_upload_time'),
        ]

        permissions = []
