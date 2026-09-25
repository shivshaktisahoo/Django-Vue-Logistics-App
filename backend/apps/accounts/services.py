from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import DomainError

from .models import User

DEMO_EMAIL_DOMAIN = "demo.cargopulse.app"


def demo_email(role: str) -> str:
    return f"{role}@{DEMO_EMAIL_DOMAIN}"


def register_user(*, email: str, password: str, full_name: str) -> User:
    if User.objects.filter(email__iexact=email).exists():
        raise DomainError("An account with this email already exists.", field="email")
    validate_password(password)
    return User.objects.create_user(email, password, full_name=full_name)


def login_with_password(*, email: str, password: str) -> User:
    user = authenticate(email=email.lower(), password=password)
    if user is None:
        raise DomainError("Invalid email or password.", code="invalid_credentials")
    return user


def demo_user_for_role(*, role: str) -> User:
    """One-click showcase login: no password to type, no signup friction."""
    user = User.objects.filter(email=demo_email(role), is_demo=True, is_active=True).first()
    if user is None:
        raise DomainError("The demo workspace is being prepared. Try again in a minute.")
    return user


def issue_tokens(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}
