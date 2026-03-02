from django.urls import path
from .views import (
    ExponentialLoadDegradationView,
    RandomFailureView,
    SlowProcessingView,
    TailLatencyView,
    PermanentFailureView
)

app_name = "chaos"

urlpatterns = [
    path("chaos/random-failures", RandomFailureView.as_view()),
    path("chaos/slow-processing", SlowProcessingView.as_view()),
    path("chaos/tail-latency", TailLatencyView.as_view()),
    path("chaos/permanent-failure", PermanentFailureView.as_view()),
    path("chaos/exponential-load/", ExponentialLoadDegradationView.as_view()),
]