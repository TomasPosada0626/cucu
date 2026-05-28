from django.urls import path
from .views import ConsumeExternalJsonAPIView, ExternalServicesTestAPIView, TriggerAsyncTaskAPIView

urlpatterns = [
    path("external-services", ExternalServicesTestAPIView.as_view(), name="external-services-test"),
    path("external-services/", ExternalServicesTestAPIView.as_view(), name="external-services-test-slash"),
    path("trigger-task", TriggerAsyncTaskAPIView.as_view(), name="trigger-task"),
    path("trigger-task/", TriggerAsyncTaskAPIView.as_view(), name="trigger-task-slash"),
    path("aliados/consumir", ConsumeExternalJsonAPIView.as_view(), name="ally-consume"),
    path("aliados/consumir/", ConsumeExternalJsonAPIView.as_view(), name="ally-consume-slash"),
]
