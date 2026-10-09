from django.contrib import admin
from django.urls import path, include
from admission import views as admission_views

urlpatterns = [
    # Keep the admissions dashboard under /admin/ while leaving the rest of
    # Django's built-in admin site available at the same prefix.
    path("admin/dashboard/", admission_views.student_workspace, name="student_workspace"),
    path("admin/", admin.site.urls),
    path("media/<path:file_path>", admission_views.protected_media, name="protected_media"),
    path("", admission_views.home, name="home"),
    path("", include("accounts.urls")),
    path("admission/", include("admission.urls")),
]
