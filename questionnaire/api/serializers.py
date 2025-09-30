# External
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

# Internal
from questionnaire.models import Questionnaire


class QuestionnaireForAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = Questionnaire
        fields = '__all__'


class QuestionnaireFilterSerializer(serializers.Serializer):

    questionnaire_scope = serializers.ChoiceField(
        choices=Questionnaire.SCOPE_CHOICES,
        help_text="Filter by questionnaire scope"
    )

    questionnaire_type = serializers.ChoiceField(
        choices=Questionnaire.TYPE_CHOICES,
        help_text="Filter by questionnaire type"
    )


class QuestionnaireCreateByAdminSerializer(serializers.Serializer):
    """
    Serializer for admin to create new Questionnaires.
    """

    staff_id = serializers.IntegerField(
        required=True,
        help_text="ID of the staff member creating the questionnaire"
    )
    name = serializers.CharField(
        validators=[UniqueValidator(queryset=Questionnaire.objects.all())]
    )
    about = serializers.CharField(max_length=1000)

    questionnaire_type = serializers.ChoiceField(
        choices=Questionnaire.TYPE_CHOICES[0][0]
    )
    questionnaire_scope = serializers.ChoiceField(
        choices=Questionnaire.SCOPE_CHOICES[0][0]
    )
