# Built-in
from typing import Any, Dict

# External
from django.urls import reverse
from rest_framework import status

# Internal
from cmn.base_test import BaseApiTestCase


class TestAdminCRUDSingleQuestionnaire(BaseApiTestCase):

############
# POSITIVE #
############

    def test_create_questionnaire(self) -> None:
        """
        GIVEN a valid questionnaire payload from fixtures and an authenticated admin,
        WHEN the admin submits a POST to create a questionnaire,
        THEN the response is 201 Created and the new questionnaire defaults
             to type 'regular' and scope 'draft'.
        """
        # GIVEN
        payload: Dict[str, Any] = self.load_questionnaire(to_db=False)
        admin = self.load_admin_in_db()

        # Update the payload to use the actual admin user's ID
        payload['staff_id'] = admin.id

        url: str = reverse("admin-questionnaire-list")
        self.client.force_authenticate(user=admin)

        # WHEN
        response = self.client.post(url, data=payload, format="json")

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(
            data.get("questionnaire_type"),
            "regular",
            "Expected newly created questionnaire with default type 'regular'."
        )
        self.assertEqual(
            data.get("questionnaire_scope"),
            "draft",
            "Expected newly created questionnaire with default scope 'draft'."
        )


    def test_list_questionnaires(self) -> None:
        pass


    def test_filter_questionnaires(self) -> None:
        """regular type"""
        ...

    def test_get_single_questionnaire(self) -> None:
        pass


    def test_update_single_draft_scope_questionnaire(self) -> None:
        pass


    def test_delete_single_draft_scope_questionnaire(self) -> None:
        pass


class TestAdminSingleQuestionnaireLogic(BaseApiTestCase):

############
# POSITIVE #
############


    def test_patch_regular_type_draft_scope_to_public_scope(self) -> None:
        pass

    def test_patch_regular_type_public_scope_to_draft_scope(self) -> None:
        pass

    def test_patch_regular_type_draft_scope_to_assigned_scope(self) -> None:
        pass

    def test_patch_regular_type_assigned_scope_to_draft_scope(self) -> None:
        pass



    def test_patch_regular_type_draft_scope_to_verification_type(self) -> None:
        pass

    def test_patch_verification_type_draft_scope_to_regular_type(self) -> None:
        pass

    def test_patch_verification_type_draft_scope_to_assigned_scope(self) -> None:
        pass

    def test_patch_regular_type_draft_scope_to_mandatory_type(self) -> None:
        pass

    def test_patch_mandatory_type_draft_scope_to_assigned_scope(self) -> None:
        pass

############
# NEGATIVE #
############

    def test_patch_regular_type_public_scope_to_assigned_scope(self) -> None:
        pass

    def test_patch_verification_type_draft_scope_to_public_scope(self) -> None:
        pass

    def test_patch_verification_type_assigned_scope_to_regular_type(self) -> None:
        pass

    def test_patch_mandatory_type_draft_scope_to_public_scope(self) -> None:
        pass


    def test_update_regular_type_public_scope_questionnaire(self) -> None:
        pass

    def test_delete_regular_type_public_scope_questionnaire(self) -> None:
        pass


class TestUserApiQuestionnaire(BaseApiTestCase):
    ...