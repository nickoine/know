# Built-in
from typing import Any

# External
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response


# Internal
from questionnaire.service import AdminQuestionnaireService
from .serializers import (QuestionnaireForAdminSerializer,
                          QuestionnaireCreateByAdminSerializer,
                          QuestionnaireFilterSerializer)


class AdminQuestionnaireViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for admin questionnaire operations.
    
    Provides:
    - list: GET /admin/questionnaire/ (with optional scope or type filters)
    - create: POST /admin/questionnaire/
    """
    permission_classes = [IsAdminUser]
    serializer_class = QuestionnaireForAdminSerializer
    
    def _get_serializer_class(self):

        """
        Return appropriate serializer class based on action.
        """
        if self.action == 'create':
            return QuestionnaireCreateByAdminSerializer
        return QuestionnaireForAdminSerializer


    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        GET → delegate the operation to validator, then to service and return Response with serialized results.
        """
        filter_ser = QuestionnaireFilterSerializer(data=request.query_params)
        filter_ser.is_valid(raise_exception=True)
        filters = filter_ser.validated_data

        total, qs = AdminQuestionnaireService.list_questionnaires(
            questionnaire_scope=filters.get("scope"),
            questionnaire_type=filters.get("type"),
        )

        ser = self.get_serializer(qs, many=True)
        return Response(
            {"count": total, "results": ser.data},
            status=status.HTTP_200_OK
        )


    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        POST → delegate the operation to serializer, then to Q service and return Response with results.
        """
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = AdminQuestionnaireService.create_questionnaire(write_serializer.validated_data)
        
        # Use the read serializer for output
        read_serializer = QuestionnaireForAdminSerializer(instance)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class QuestionnaireDetailView:
    pass
