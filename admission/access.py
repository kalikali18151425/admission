"""Permission helpers that keep student logins separate from staff accounts."""

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect

from .models import StudentProfile


def is_admin_account(user):
    """Return true only for staff accounts that are not student accounts."""
    if not user.is_authenticated or not user.is_staff:
        return False
    return not StudentProfile.objects.filter(user_id=user.pk).exists()


def admissions_staff_required(view_func):
    """Protect admissions tools from regular and student-linked accounts."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not is_admin_account(request.user):
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapped


def require_admin_or_owner(user, owner_id):
    """Allow a student to access their own file; staff can access any file."""
    if user.id == owner_id or is_admin_account(user):
        return
    raise Http404
