# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("username", "email", "role", "is_active", "is_staff", "is_superuser", "date_joined", "last_login")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("date_joined", "last_login")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )