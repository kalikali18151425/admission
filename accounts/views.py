from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_POST
from admission.access import is_admin_account


def register(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required.")
            return redirect("register")

        if len(username) > 150 or len(email) > 254:
            messages.error(request, "Username or email is too long.")
            return redirect("register")

        try:
            User._meta.get_field("username").run_validators(username)
            validate_email(email)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        candidate = User(username=username, email=email)
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("register")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=False,
            is_superuser=False,
        )

        messages.success(
            request,
            "Registration successful. Please login."
        )

        return redirect("login")

    return render(
        request,
        "accounts/register.html"
    )


def user_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            if is_admin_account(user):
                return redirect("student_workspace")
            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "accounts/login.html"
    )


@require_POST
def user_logout(request):

    logout(request)

    return redirect("login")


def dashboard(request):

    if not request.user.is_authenticated:
        return redirect("login")
    if is_admin_account(request.user):
        return redirect("student_workspace")

    # Get student's profile, application and notifications
    from admission.models import (
        StudentProfile,
        Application,
        Notification,
        StudentAdmissionRecord,
    )

    application = None
    notifications = []
    admission_records = StudentAdmissionRecord.objects.none()

    profile = StudentProfile.objects.filter(
        user=request.user
    ).first()

    if profile:

        application = Application.objects.filter(
            student=profile
        ).select_related("program").first()

        notifications = Notification.objects.filter(
            student=profile
        ).order_by("-created_at")
        admission_records = StudentAdmissionRecord.objects.filter(
            application__student=profile
        ).select_related("application__program").order_by("-created_at")

    return render(
        request,
        "accounts/dashboard.html",
        {
            "application": application,
            "notifications": notifications,
            "admission_records": admission_records,
        }
    )
