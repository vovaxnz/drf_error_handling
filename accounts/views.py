# accounts/views.py
from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from accounts.serializers import UserSerializer
from rest_framework.views import APIView

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

