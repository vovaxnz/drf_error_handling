from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    correlationId = serializers.UUIDField()
    errorType = serializers.ChoiceField(choices=["transient", "permanent"])
    details = serializers.JSONField(required=False)


class SuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    processingTimeMs = serializers.IntegerField()
    correlationId = serializers.UUIDField()