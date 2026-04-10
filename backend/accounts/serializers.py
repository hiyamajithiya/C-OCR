"""
DRF Serializers for accounts app.
"""

from rest_framework import serializers


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    user = serializers.DictField()


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(max_length=255, write_only=True)
    role = serializers.ChoiceField(choices=["admin", "operator", "reviewer"])


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(max_length=255, required=False)
    role = serializers.ChoiceField(choices=["admin", "operator", "reviewer"], required=False)
    is_active = serializers.BooleanField(required=False)


class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    last_login_at = serializers.DateTimeField(allow_null=True)
