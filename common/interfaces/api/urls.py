from django.urls import path
from .views import (
    ConsumeExternalJsonAPIView,
    ExternalServicesTestAPIView,
    HealthAPIView,
    TriggerAsyncTaskAPIView,
)

urlpatterns = [
    path("health", HealthAPIView.as_view(), name="health"),
    path("health/", HealthAPIView.as_view(), name="health-slash"),
    path("external-services", ExternalServicesTestAPIView.as_view(), name="external-services-test"),
    path("external-services/", ExternalServicesTestAPIView.as_view(), name="external-services-test-slash"),
    path("trigger-task", TriggerAsyncTaskAPIView.as_view(), name="trigger-task"),
    path("trigger-task/", TriggerAsyncTaskAPIView.as_view(), name="trigger-task-slash"),
    path("aliados/consumir", ConsumeExternalJsonAPIView.as_view(), name="ally-consume"),
    path("aliados/consumir/", ConsumeExternalJsonAPIView.as_view(), name="ally-consume-slash"),
]
