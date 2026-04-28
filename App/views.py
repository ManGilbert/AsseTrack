from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSerializer


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role")

        # Validate input
        if not email or not password or not role:
            return Response(
                {"error": "Email, password and role are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check password
        if not user.check_password(password):
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ROLE VALIDATION
        if user.role != role:
            return Response(
                {
                    "error": f"Access denied. You are registered as '{user.role}', not '{role}'"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # OPTIONAL: Check employee active status
        if hasattr(user, 'employee_profile') and not user.employee_profile.is_active:
            return Response(
                {"error": "Account is inactive. Contact admin."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": f"Login successful as {user.role}",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)