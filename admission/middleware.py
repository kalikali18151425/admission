"""Block student-linked logins from Django's built-in administration site."""

from django.http import HttpResponseForbidden

from .access import is_admin_account


class AdminAccountSeparationMiddleware:
    """A user profile cannot also be used as an admin/staff login."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            request.path.startswith("/admin/")
            and user
            and user.is_authenticated
            and user.is_staff
            and not is_admin_account(user)
        ):
            return HttpResponseForbidden(
                "Student accounts cannot access the administration site."
            )
        return self.get_response(request)
