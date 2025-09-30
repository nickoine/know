# Built-in
from __future__ import annotations
from typing import TYPE_CHECKING

# External
from django.db.models import QuerySet

# Internal
from .repo import QuestionnaireRepository

if TYPE_CHECKING:
    from typing import Any, Dict, Optional, Tuple
    from .models import Questionnaire


class AdminQuestionnaireService:
    """
    Encapsulates business logic for Questionnaire entities.
    """

    @staticmethod
    def list_questionnaires(questionnaire_scope: Optional[str] = None,
                            questionnaire_type: Optional[str] = None) -> Tuple[int, QuerySet[Questionnaire]]:
        """
        Retrieve questionnaires, optionally filtering by questionnaire scope or type.

        :param questionnaire_scope: Optional scope to filter by (e.g., 'draft', 'public', 'assigned').
        :param questionnaire_type: Optional type to filter by (e.g., 'regular', 'verification', 'mandatory').
        :return: A tuple of (total_count, queryset) where:
                 - total_count is the number of matched questionnaires.
                 - queryset is a Django QuerySet of Questionnaire instances.
        """

        q_repo = QuestionnaireRepository()
        queryset = q_repo.manager.get_all()

        if questionnaire_scope:
            queryset = queryset.filter(scope=questionnaire_scope)
        elif questionnaire_type:
            queryset = queryset.filter(type=questionnaire_type)

        return queryset.count(), queryset


    @staticmethod
    def create_questionnaire(data: Dict[str, Any]) -> Questionnaire:
        """
        Create and persist a new Questionnaire from validated data.

        :param data: Dict of fields matching Questionnaire model.
        :return: The newly created Questionnaire instance.
        """
        repo = QuestionnaireRepository()
        instance = repo.manager.create_instance(**data)
        return instance
