from django.urls import path
from . import views

urlpatterns = [
    path("apply/", views.apply_admission, name="apply_admission"),
    path("details/", views.application_details, name="application_details"),
    path("profile/", views.profile, name="profile"),
    path("documents/", views.manage_documents, name="manage_documents"),
    path("documents/<int:document_id>/download/", views.document_download, name="document_download"),
    path("students/<int:profile_id>/photo/", views.student_photo, name="student_photo"),
    path("print/", views.print_application, name="print_application"),
    path("confirm/", views.confirm_admission, name="confirm_admission"),
    path("record/", views.my_student_record, name="my_student_record"),
    path("review/notices/", views.manage_homepage_notices, name="manage_homepage_notices"),
    path("review/records/<int:record_id>/", views.staff_student_record, name="staff_student_record"),
]
