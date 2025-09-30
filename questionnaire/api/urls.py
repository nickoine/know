from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminQuestionnaireViewSet

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'admin/questionnaire', AdminQuestionnaireViewSet, basename='admin-questionnaire')

urlpatterns = [
    # Include router URLs - this automatically generates:
    # GET/POST /admin/questionnaire/ -> list/create actions
    # GET/PUT/PATCH/DELETE /admin/questionnaire/{id}/ -> retrieve/update/partial_update/destroy actions
    path('', include(router.urls)),
]