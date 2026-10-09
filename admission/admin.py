from django.contrib import admin, messages
from django.utils import timezone
from .models import (
    Program,
    StudentProfile,
    Application,
    ApplicationFee,
    Document,
    Notification,
    HomepageNotice,
    PaymentHistory,
    StudentAdmissionRecord,
)


@admin.action(description="Reject selected applications")
def reject_applications(modeladmin, request, queryset):

    updated = 0

    for application in queryset.exclude(status="Rejected"):

        application.status = "Rejected"
        application.save()

        Notification.objects.create(
            student=application.student,
            message=(
                f"Your admission application "
                f"{application.application_id} has been rejected."
            )
        )

        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} application(s) rejected successfully.",
        messages.WARNING
    )


@admin.action(description="Approve selected applications")
def approve_applications(modeladmin, request, queryset):

    updated = 0

    for application in queryset.exclude(status="Approved"):

        application.status = "Approved"
        application.save()

        Notification.objects.create(
            student=application.student,
            message=(
                f"Your admission application "
                f"{application.application_id} has been approved."
            )
        )

        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} application(s) approved successfully.",
        messages.SUCCESS
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "application_id",
        "student",
        "program",
        "status",
        "admission_result",
        "submitted_at",
    )

    list_filter = ("status", "program")
    list_editable = ("status", "admission_result")
    date_hierarchy = "submitted_at"
    ordering = ("-submitted_at",)

    search_fields = (
        "application_id",
        "student__user__username",
        "student__user__email",
    )

    actions = [
        approve_applications,
        reject_applications,
    ]

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = Application.objects.get(pk=obj.pk)
        super().save_model(request, obj, form, change)
        if obj.status == "Confirmed":
            StudentAdmissionRecord.objects.get_or_create(application=obj)
        if not previous:
            return
        updates = []
        if previous.status != obj.status and obj.status in ("Approved", "Rejected"):
            updates.append(f"Your admission application {obj.application_id} is now {obj.status.lower()}.")
        if previous.admission_result != obj.admission_result and obj.admission_result != "Pending":
            updates.append(f"An admission result is available for {obj.application_id}: {obj.admission_result}.")
        for message in updates:
            Notification.objects.create(student=obj.student, message=message)


admin.site.register(Program)
admin.site.register(StudentProfile)
admin.site.register(Document)
admin.site.register(Notification)


@admin.register(HomepageNotice)
class HomepageNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "message")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ApplicationFee)
class ApplicationFeeAdmin(admin.ModelAdmin):
    list_display = ("application", "amount", "status", "payment_reference", "paid_at")
    list_filter = ("status",)
    search_fields = ("application__application_id", "payment_reference")
    readonly_fields = ("application",)

    def save_model(self, request, obj, form, change):
        previous = ApplicationFee.objects.get(pk=obj.pk) if change else None
        if obj.status == "Paid" and not obj.paid_at:
            obj.paid_at = timezone.now()
        if obj.status == "Pending":
            obj.paid_at = None
        super().save_model(request, obj, form, change)
        if (
            previous is None
            or previous.status != obj.status
            or previous.payment_reference != obj.payment_reference
            or previous.amount != obj.amount
        ):
            PaymentHistory.objects.create(
                application=obj.application,
                amount=obj.amount,
                status=obj.status,
                payment_reference=obj.payment_reference,
                note="Fee updated in administration",
                recorded_by=request.user,
            )


@admin.register(StudentAdmissionRecord)
class StudentAdmissionRecordAdmin(admin.ModelAdmin):
    list_display = ("record_number", "application", "created_at")
    search_fields = ("record_number", "application__application_id", "application__student__user__username")
    readonly_fields = ("record_number", "application", "created_at")
    fields = readonly_fields
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "amount", "status", "payment_reference", "recorded_at", "recorded_by")
    list_filter = ("status", "recorded_at")
    search_fields = ("application__application_id", "payment_reference", "application__student__user__username")
    readonly_fields = ("application", "amount", "status", "payment_reference", "note", "recorded_by", "recorded_at")
    fields = readonly_fields
    ordering = ("-recorded_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.site_header = "University Admission Administration"
admin.site.site_title = "Admission Portal Admin"
admin.site.index_title = "Review applications and manage admission records"
