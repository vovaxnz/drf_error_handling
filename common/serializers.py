from rest_framework import serializers

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    detail = serializers.CharField()


class ValidationErrorSerializer(serializers.Serializer):
    detail = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))




def crud_schema(serializer):
    return extend_schema_view(
        list=extend_schema(
            responses={
                200: serializer(many=True),
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
            }
        ),
        retrieve=extend_schema(
            responses={
                200: serializer,
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
                404: OpenApiResponse(response=ErrorSerializer),
            }
        ),
        create=extend_schema(
            responses={
                201: serializer,
                400: OpenApiResponse(response=ValidationErrorSerializer),
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
            }
        ),
        update=extend_schema(
            responses={
                200: serializer,
                400: OpenApiResponse(response=ValidationErrorSerializer),
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
                404: OpenApiResponse(response=ErrorSerializer),
            }
        ),
        partial_update=extend_schema(
            responses={
                200: serializer,
                400: OpenApiResponse(response=ValidationErrorSerializer),
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
                404: OpenApiResponse(response=ErrorSerializer),
            }
        ),
        destroy=extend_schema(
            responses={
                204: OpenApiResponse(description="Deleted"),
                401: OpenApiResponse(response=ErrorSerializer),
                403: OpenApiResponse(response=ErrorSerializer),
                404: OpenApiResponse(response=ErrorSerializer),
            }
        ),
    )