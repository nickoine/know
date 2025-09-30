from django.db import models
from django.utils.translation import gettext_lazy as _
from cmn.base_model import BaseModel


class Questionnaire(BaseModel):
    """Represents a form with multiple questions."""

    SCOPE_CHOICES = [('draft', 'Draft'), ('public', 'Public'), ('assigned', 'Assigned')]
    TYPE_CHOICES = [('regular', 'Regular'), ('verification', 'Verification'), ('mandatory', 'Mandatory')]

    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name=_("Name"),
        help_text=_("Unique identifier for the questionnaire (e.g., 'KYC Form 2025').")
    )

    about = models.TextField(
        max_length=255,
        null=True,
        verbose_name=_("About"),
        help_text=_("Purpose and instructions for respondents.")
    )

    questionnaire_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_("Type"),
        help_text=_("Classification of questionnaire type.")
    )

    questionnaire_scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_CHOICES[0][0],
        db_index=True,
        blank=True,
        verbose_name=_("Scope"),
        help_text=_("Publication state of the questionnaire.")
    )

    questions = models.ManyToManyField(
        'Question',
        related_name='questionnaire',
        through='QuestionnaireQuestion',
        blank=True,
        help_text="Questions included in this questionnaire"
    )

    submitted_by = models.ManyToManyField(
        'user.User',
        blank=True,
        related_name='submitted_questionnaires',
        help_text = "Users the questionnaire was submitted by"
    )

    assigned_to = models.ManyToManyField(
        'user.User',
        blank=True,
        related_name='assigned_questionnaires',
        help_text="Users that this questionnaire is assigned to"
    )

    staff_id = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_questionnaire'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        verbose_name=_("Created At"),
        help_text=_("When this questionnaire was created.")
    )


    # group = models.ForeignKey(
    #     'QuestionnaireGroup',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True
    # )
    # question_group = models.ManyToManyField(
    #     'QuestionGroup',
    #     related_name='questionnaire_category',
    #     through='QuestionnaireQuestionGroup',
    #     blank=True,
    #     help_text="Questions category included in this questionnaire"
    #
    # )
    # assigned_to_groups = models.ManyToManyField(
    #     'UserGroups',
    #     blank=True
    # )
    #
    # supported_languages = models.JSONField(
    #     default=list,
    #     verbose_name=_("Supported Languages"),
    #     help_text=_("List of language codes (e.g., ['en', 'es']) for multilingual support.")
    # )


    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")
        ordering = ['-questionnaire_scope', '-created_at']
        indexes = [
            models.Index(fields=['questionnaire_scope', 'questionnaire_type']),
            models.Index(fields=['name', 'questionnaire_scope']),
            models.Index(fields=['staff_id', 'questionnaire_scope']),
        ]
        # admin
        permissions = []


    def __str__(self):
        return f"{self.name} (Type: {self.questionnaire_type}, Scope: {self.questionnaire_scope})"


# class QuestionnaireGroup(BaseModel):
#     """Questionnaires can be grouped in categories."""
#
#     name = models.CharField(max_length=100, unique=True)


class Question(BaseModel):
    """
    Represents an individual question item that can be reused across multiple questionnaires.
    Supports various response types and validation rules.
    """

    QUESTION_TYPE_CHOICES = [
        ('text', 'Text Input'),
        ('checkbox', 'Checkboxes'),
        ('dropdown', 'Dropdown Select'),
        ('file', 'File Upload'),
        ('date', 'Date Selector'),
        ('number', 'Numeric Input'),
        ('boolean', 'Yes/No Toggle'),
        ('url', 'URL / Link'),

        ('multiple_choice', 'Multiple Choice'),
        ('rating', 'Star Rating'),
        ('datetime', 'Date & Time Selector'),
        ('time', 'Time Selector'),
        ('paragraph', 'Long Text / Paragraph'),
        ('slider', 'Slider / Range'),
        ('signature', 'Signature Capture'),
    ]

    question_type = models.CharField(
        max_length=50,
        choices=QUESTION_TYPE_CHOICES,
        db_index=True,
        verbose_name=_("Question Type"),
        help_text=_("Determines what input widget to display.")
    )

    reference_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Reference Code"),
        help_text=_("Unique identifier for business logic (e.g., 'TAX_ID_VERIFICATION').")
    )

    text = models.TextField(
        max_length=255,
        verbose_name=_("Text"),
        help_text=_("Actual question text for respondents.")
    )

    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Validation Rules"),
        help_text=_("Configurable validation (e.g., {'min_length': 2, 'max_length': 100}).")
    )

    staff_id = models.ForeignKey(
        'user.User',
        null=True,
        on_delete=models.SET_NULL,
        related_name='created_question'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        verbose_name=_("Created At"),
        help_text=_("When this question was first defined.")
    )

    # group = models.ForeignKey(
    #     'QuestionGroup',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference_code', 'question_type']),
            models.Index(fields=['staff_id', 'created_at']),
        ]
        permissions = []

    def __str__(self):
        return f"Question [{self.reference_code}] ({self.question_type})"


# class QuestionGroup(BaseModel):
#     """Questions can be grouped in categories."""
#
#     name = models.CharField(max_length=100, unique=True)


class QuestionnaireQuestion(BaseModel):
    """
    Join table to associate Questions with Questionnaires in a specific order.
    """
    questionnaire = models.ForeignKey(
        'Questionnaire',
        on_delete=models.CASCADE,
        related_name='items'
    )
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        related_name='questionnaire_items'
    )
    order_index = models.PositiveIntegerField(
        help_text='Position of this question within the questionnaire'
    )

    class Meta:
        # Prevent duplicate questions and index collisions within a questionnaire
        unique_together = (
            ('questionnaire', 'question'),
            ('questionnaire', 'order_index'),
        )
        indexes = [
            models.Index(fields=['questionnaire', 'order_index'], name='qitem_order_idx'),
        ]
        ordering = ['order_index']
        verbose_name = 'Questionnaire Item'
        verbose_name_plural = 'Questionnaire Items'

    def __str__(self):
        return f"{self.questionnaire.id} – {self.question.id} @ {self.order_index}"


# class QuestionnaireQuestionGroup(models.Model):
#     questionnaire = models.ForeignKey('Questionnaire', on_delete=models.CASCADE)
#     question_group = models.ForeignKey('QuestionGroup', on_delete=models.PROTECT)
#
#     class Meta:
#         unique_together = ('questionnaire', 'question_group')
