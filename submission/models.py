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

    SUBMISSION_TYPE = [('mandatory', 'Mandatory'), ('regular', 'Regular')]
    SUBMISSION_STATUSES = [('started', 'Started'), ('completed', 'Completed'),
                           ('failed', 'Failed'), ('pending', 'Pending'), ('approved', 'Approved')]

    submission_type = models.CharField(
        max_length=50,
        choices=SUBMISSION_TYPE
    )

    status = models.CharField(
        max_length=20,
        choices=SUBMISSION_STATUSES,
        default=SUBMISSION_STATUSES[0][0],
        blank=True
    )

    is_orphan = models.BooleanField(
        null=True,
        blank=True,
        default=False,
        help_text=_("Submission becomes orphan, when the user's account and data is deleted")
        )

    user = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='submissions',
        verbose_name=_("User"),
        help_text=_("The user that submitted the questionnaire.")
    )

    questionnaire = models.ForeignKey(
        'questionnaire.Questionnaire',
        on_delete=models.PROTECT, # Don’t allow deleting forms with user data
        related_name='submissions',
        verbose_name=_("Questionnaire"),
        help_text=_("The questionnaire being filled.")
    )

    submitted_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Submitted At"),
        help_text=_("When the questionnaire was submitted (must be in year/month/days).")
    )

    approved_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_submissions',
        help_text=_('Approved by admin manually.')
    )

    approved_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
        help_text=_("Last modification timestamp.")
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
            # Fast access to all mandatory-type submissions
            Index(
                fields=["submission_type"],
                name="idx_mandatory_submissions",
                condition=Q(submission_type='mandatory')
            ),

            # Query most recent submissions (history or audit trails)
            Index(
                fields=["submitted_at"],
                name="idx_submitted_at"
            ),

            # Used to detect incomplete/stuck submissions
            Index(
                fields=["status"],
                name="idx_status_started"
            ),
        ]

    def __str__(self):
        return f"Submission#{self.id}. Type: {self.submission_type}. Status: {self.status}. User: {self.user.id}"


class SubmissionPayload(BaseModel):
    """
    Stores full questionnaire responses (as JSON) tied to a single submission.
    One-to-one payload blob for the submission.
    """

    submission = models.OneToOneField(
        'Submission',
        on_delete=models.CASCADE,
        related_name='payload'
    )

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
            Index(fields=['submission'], name='index_by_submission'),
            GinIndex(fields=['payload'], name='payload_gin_idx'),
        ]

    def __str__(self):
        return f"Payload for submission {self.id}"



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
    """Stores individual responses to questions within a questionnaire submission."""


    DOCUMENT_TYPES = [('passport', 'Passport'), ('national_id', 'National ID'), ('driver_license', 'Driver License')]

    submission = models.OneToOneField(
        'Submission',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES
    )

    document_file = models.FileField(
        upload_to='documents/'
    )
    #
    # selfie_file = models.ImageField(
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
            Index(fields=['submission'], name='idx_by_submission'),
            Index(fields=['document_type'], name='idx_by_document_type'),
            Index(fields=['uploaded_at'], name='idx_by_upload_time'),
        ]

        permissions = [
            ("can_verify_documents", "Can manually review and verify uploaded documents")
        ]
