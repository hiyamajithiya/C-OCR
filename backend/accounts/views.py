"""
DRF Views for accounts app — auth and user management endpoints.
"""

from datetime import datetime

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import (
    LoginResponseSerializer,
    UserCreateSerializer,
    UserResponseSerializer,
    UserUpdateSerializer,
)
from audit.models import AuditLog
from core.authentication import JWTBearerAuthentication
from core.permissions import AllowAny, IsActiveUser, IsAdminUser
from core.security import create_access_token, get_password_hash, verify_password


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------


class LoginRateThrottle(AnonRateThrottle):
    rate = "5/min"


class LoginView(APIView):
    """POST /api/v1/auth/login — form-urlencoded login."""

    parser_classes = [FormParser, MultiPartParser]
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get("username")  # email
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.select_related("tenant").get(email=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_password(password, user.password_hash):
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "User account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update last login
        user.last_login_at = datetime.utcnow()
        user.save(update_fields=["last_login_at", "updated_at"])

        # Audit log
        AuditLog.objects.create(
            tenant=user.tenant,
            actor_user=user,
            action="user_login",
            entity_type="user",
            entity_id=user.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        access_token = create_access_token(data={"sub": user.id})

        data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        }
        return Response(data, status=status.HTTP_200_OK)


class RefreshView(APIView):
    """POST /api/v1/auth/refresh — issue a new JWT for the current user."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def post(self, request):
        user = request.user
        access_token = create_access_token(data={"sub": user.id})
        return Response(
            {"access_token": access_token, "token_type": "bearer"},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# User views
# ---------------------------------------------------------------------------


class UserListCreateView(APIView):
    """
    GET  /api/v1/users/  — list users (admin)
    POST /api/v1/users/  — create user (admin)
    """

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(tenant_id=request.user.tenant_id)
        serializer = UserResponseSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create(
            tenant=request.user.tenant,
            name=serializer.validated_data["name"],
            email=email,
            password_hash=get_password_hash(serializer.validated_data["password"]),
            role=serializer.validated_data["role"],
        )

        # Audit log
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="user_create",
            entity_type="user",
            entity_id=user.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        response_serializer = UserResponseSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class UserMeView(APIView):
    """GET /api/v1/users/me — return current authenticated user."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsActiveUser]

    def get(self, request):
        serializer = UserResponseSerializer(request.user)
        return Response(serializer.data)


class UserUpdateView(APIView):
    """PATCH /api/v1/users/<user_id>/ — partial update (admin only)."""

    authentication_classes = [JWTBearerAuthentication]
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, tenant_id=request.user.tenant_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(user, field, value)

        user.save()

        # Audit log
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="user_update",
            entity_type="user",
            entity_id=user.id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        response_serializer = UserResponseSerializer(user)
        return Response(response_serializer.data)

    def delete(self, request, user_id):
        """DELETE /api/v1/users/<user_id>/ — delete user (admin only)."""
        try:
            user = User.objects.get(id=user_id, tenant_id=request.user.tenant_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.id == request.user.id:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_user_id = user.id
        deleted_user_email = user.email
        user.delete()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor_user=request.user,
            action="user_delete",
            entity_type="user",
            entity_id=deleted_user_id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata_json={"email": deleted_user_email},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
