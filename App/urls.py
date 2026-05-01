from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

from .views import (
    AuthViewSet,
    BranchViewSet,
    DeviceAssignmentViewSet,
    DeviceViewSet,
    EmployeeViewSet,
    HeadOfficeViewSet,
    NotificationViewSet,
    RequestViewSet,
    openapi_schema_view,
    swagger_ui_view,
)

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"head-offices", HeadOfficeViewSet, basename="head-office")
router.register(r"branches", BranchViewSet, basename="branch")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"assignments", DeviceAssignmentViewSet, basename="assignment")
router.register(r"requests", RequestViewSet, basename="request")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("docs/", swagger_ui_view, name="swagger-ui"),
    path("docs/openapi.json", openapi_schema_view, name="openapi-schema"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
