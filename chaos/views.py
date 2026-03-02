import random
import time
import uuid
from datetime import datetime

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from drf_spectacular.types import OpenApiTypes

from .serializers import ErrorResponseSerializer, SuccessResponseSerializer
from rest_framework.permissions import AllowAny


def build_error(code: str, message: str, error_type: str, http_status: int, headers=None):
    correlation_id = uuid.uuid4()
    payload = {
        "code": code,
        "message": message,
        "correlationId": correlation_id,
        "errorType": error_type,
        "details": {
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    response = Response(payload, status=http_status)
    response["X-Correlation-Id"] = str(correlation_id)

    if headers:
        for k, v in headers.items():
            response[k] = v

    return response


class RandomFailureView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Random transient failure simulation",
        description="""
Simulates unstable upstream dependency.

Behavior:
- If random value < failureRate -> returns transient error.
- Error codes randomly selected from 500, 503, 429.
- 429 and 503 responses may include Retry-After header.
- If no failure triggered -> 200 OK.

Retry semantics:
- errorType = transient
- Safe to retry with exponential backoff + jitter.
- Designed to trigger circuit breaker when failure ratio threshold exceeded.

Headers:
- X-Correlation-Id: unique request identifier.
- Retry-After: present for 429 or 503.
""",
        parameters=[
            OpenApiParameter(
                name="failureRate",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Probability of failure between 0 and 1.",
                required=True
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Successful response."
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Transient internal failure. Retryable."
            ),
            503: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Service unavailable. Retryable. Includes Retry-After."
            ),
            429: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Too many requests. Retryable. Includes Retry-After."
            ),
        }
    )
    def get(self, request):
        failure_rate = float(request.query_params.get("failureRate", 0.5))
        correlation_id = uuid.uuid4()

        if random.random() < failure_rate:
            http_status = random.choice(
                [status.HTTP_500_INTERNAL_SERVER_ERROR,
                 status.HTTP_503_SERVICE_UNAVAILABLE,
                 status.HTTP_429_TOO_MANY_REQUESTS]
            )

            headers = {}
            if http_status in [503, 429]:
                headers["Retry-After"] = "2"

            return build_error(
                code="TRANSIENT_FAILURE",
                message="Simulated transient failure",
                error_type="transient",
                http_status=http_status,
                headers=headers
            )

        response = Response(
            {
                "status": "ok",
                "processingTimeMs": 10,
                "correlationId": correlation_id
            },
            status=status.HTTP_200_OK
        )
        response["X-Correlation-Id"] = str(correlation_id)
        return response


class SlowProcessingView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Artificial slow processing",
        description="""
Simulates long request processing.

Behavior:
- Sleeps for delayMs milliseconds.
- Always returns 200 unless client timeout occurs externally.
- Used for timeout chain testing and hedging.

Timeout considerations:
- Should be used to validate that inner service timeout < outer timeout.
- If client timeout < delayMs, request may never complete.

Headers:
- X-Correlation-Id.
""",
        parameters=[
            OpenApiParameter(
                name="delayMs",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Processing delay in milliseconds.",
                required=True
            )
        ],
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Completed after artificial delay."
            )
        }
    )
    def get(self, request):
        delay_ms = int(request.query_params.get("delayMs", 1000))
        correlation_id = uuid.uuid4()

        time.sleep(delay_ms / 1000)

        response = Response(
            {
                "status": "completed",
                "processingTimeMs": delay_ms,
                "correlationId": correlation_id
            },
            status=status.HTTP_200_OK
        )
        response["X-Correlation-Id"] = str(correlation_id)
        return response


class TailLatencyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Tail latency simulation",
        description="""
Simulates tail latency distribution.

Behavior:
- 95% of requests return quickly.
- 5% of requests sleep for 3000ms.
- Always 200 OK.

Purpose:
- Test hedging.
- Measure P95/P99 latency.
- Validate impact of slow tail on average latency.

Headers:
- X-Correlation-Id.
""",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Response with variable latency."
            )
        }
    )
    def get(self, request):
        correlation_id = uuid.uuid4()

        if random.random() < 0.05:
            delay_ms = 3000
        else:
            delay_ms = 50

        time.sleep(delay_ms / 1000)

        response = Response(
            {
                "status": "ok",
                "processingTimeMs": delay_ms,
                "correlationId": correlation_id
            },
            status=status.HTTP_200_OK
        )
        response["X-Correlation-Id"] = str(correlation_id)
        return response


class PermanentFailureView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Permanent logical failure",
        description="""
Simulates non-retryable error.

Behavior:
- Always returns permanent error.
- errorType = permanent.
- Must NOT be retried.

Used to validate:
- Fail closed policies.
- Retry filtering.
- Client logic that distinguishes transient vs permanent.

Headers:
- X-Correlation-Id.
""",
        responses={
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Permanent validation error."
            ),
            422: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Permanent business rule violation."
            )
        }
    )
    def get(self, request):
        return build_error(
            code="VALIDATION_ERROR",
            message="Simulated permanent validation error",
            error_type="permanent",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    

import random
import time
import uuid
from collections import deque
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import ErrorResponseSerializer, SuccessResponseSerializer


class ExponentialLoadDegradationView(APIView):

    permission_classes = [AllowAny]

    # sliding window 1 second
    request_timestamps = deque()

    # overload memory
    overload_score = 0.0
    last_decay = datetime.utcnow()

    MAX_WINDOW_SECONDS = 1
    DECAY_RATE = 0.15  # recovery speed per request

    def _current_rps(self):
        now = datetime.utcnow()

        while self.request_timestamps and \
                (now - self.request_timestamps[0]).total_seconds() > self.MAX_WINDOW_SECONDS:
            self.request_timestamps.popleft()

        return len(self.request_timestamps)

    def _update_overload(self, rps):
        now = datetime.utcnow()
        delta = (now - self.last_decay).total_seconds()
        self.last_decay = now

        # recovery when load drops
        self.overload_score = max(
            0.0,
            self.overload_score - delta * self.DECAY_RATE
        )

        if rps > 50:
            growth_factor = (rps - 50) / 50
            self.overload_score += growth_factor ** 2  # exponential growth

    @extend_schema(
        summary="Exponential load degradation simulator",
        description="""
Simulates exponential performance degradation based on RPS.

Behavior model:

0-50 rps:
- Stable.
- Latency ~ 20-40ms.
- No errors.

50-100 rps:
- Exponential latency growth.
- Occasional transient errors.

100-200 rps:
- High latency.
- Frequent 500/503.
- Circuit breaker should start opening.

>200 rps:
- Near total collapse.
- Almost always transient errors.
- Simulates thread pool exhaustion.

Recovery:
- When load drops, overload_score decays gradually.
- Service does not recover instantly.
- Cold-start effect after overload.

Purpose:
- Stress test retry policies.
- Trigger circuit breaker.
- Observe tail latency explosion.
- Validate fallback strategies.
""",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Successful response with variable latency."
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Transient overload failure."
            ),
            503: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Service unavailable due to overload."
            ),
        }
    )
    def get(self, request):
        now = datetime.utcnow()
        self.request_timestamps.append(now)

        rps = self._current_rps()
        self._update_overload(rps)

        correlation_id = uuid.uuid4()

        # compute latency exponentially
        if rps <= 50:
            latency_ms = random.randint(20, 40)
            error_probability = 0.0
        elif rps <= 100:
            latency_ms = int(50 * (1 + self.overload_score))
            error_probability = min(0.2, self.overload_score / 10)
        elif rps <= 200:
            latency_ms = int(200 * (1 + self.overload_score))
            error_probability = min(0.6, self.overload_score / 5)
        else:
            latency_ms = int(500 * (1 + self.overload_score))
            error_probability = min(0.95, 0.7 + self.overload_score / 3)

        # simulate latency
        time.sleep(latency_ms / 1000)

        if random.random() < error_probability:
            http_status = random.choice([
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_503_SERVICE_UNAVAILABLE
            ])

            payload = {
                "code": "OVERLOAD",
                "message": "Service overloaded",
                "correlationId": correlation_id,
                "errorType": "transient",
                "details": {
                    "rps": rps,
                    "overloadScore": round(self.overload_score, 2),
                    "latencyMs": latency_ms
                }
            }

            response = Response(payload, status=http_status)
            response["X-Correlation-Id"] = str(correlation_id)
            return response

        response = Response(
            {
                "status": "ok",
                "processingTimeMs": latency_ms,
                "correlationId": correlation_id
            },
            status=status.HTTP_200_OK
        )
        response["X-Correlation-Id"] = str(correlation_id)
        return response