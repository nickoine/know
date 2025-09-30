# External
from __future__ import annotations

# Internal
from cmn.base_repo import BaseRepository
from .models import Questionnaire


class QuestionnaireRepository(BaseRepository[Questionnaire]):
    """Repository for handling Questionnaire model operations."""

    _model = Questionnaire
