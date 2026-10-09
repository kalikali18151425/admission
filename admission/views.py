from io import BytesIO
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps, UnidentifiedImageError
from .access import admissions_staff_required, is_admin_account, require_admin_or_owner
from .forms import HomepageNoticeForm
from .models import (
    Program,
    StudentProfile,
    Application,
    Document,
    ApplicationFee,
    Notification,
    HomepageNotice,
    PaymentHistory,
    StudentAdmissionRecord,
)
import uuid


MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}


def _valid_image_upload(upload, max_bytes=MAX_PHOTO_BYTES):
    if not upload or upload.size > max_bytes:
        return False
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                return False
            image.verify()
        upload.seek(0)
        return True
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        upload.seek(0)
        return False


def _valid_document_upload(upload):
    if not upload or upload.size > MAX_DOCUMENT_BYTES:
        return False
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        return False
    if extension == ".pdf":
        upload.seek(0)
        valid = upload.read(5) == b"%PDF-"
        upload.seek(0)
        return valid
    return _valid_image_upload(upload, MAX_DOCUMENT_BYTES)


def _valid_email(value):
    try:
        validate_email(value)
    except ValidationError:
        return False
    return True

@login_required
def apply_admission(request):

    programs = Program.objects.all()

    # Check if the student already has a profile
    profile = StudentProfile.objects.filter(
        user=request.user
    ).first()

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        date_of_birth = request.POST.get("date_of_birth")
        address = request.POST.get("address")

        program_id = request.POST.get("program")
        ssc_result = request.POST.get("ssc_result")
        hsc_result = request.POST.get("hsc_result")

        photo = request.FILES.get("photo")
        ssc_certificate = request.FILES.get("ssc_certificate")
        hsc_certificate = request.FILES.get("hsc_certificate")

        if photo and not _valid_image_upload(photo):
            messages.error(request, "Upload a valid PNG or JPEG photo up to 5 MB.")
            return redirect("apply_admission")
        if any(file and not _valid_document_upload(file) for file in (ssc_certificate, hsc_certificate)):
            messages.error(request, "Certificates must be PDF, PNG, or JPEG files up to 10 MB.")
            return redirect("apply_admission")
        if len(full_name) > 150 or len(phone) > 20 or len(address) > 5000:
            messages.error(request, "Name, phone, or address is too long.")
            return redirect("apply_admission")

        # Validate input before changing a profile or creating an application.
        if not all([
            full_name,
            phone,
            address,
            program_id,
            ssc_result,
            hsc_result
        ]):
            messages.error(
                request,
                "Please fill in all required fields."
            )
            return redirect("apply_admission")

        try:
            program = Program.objects.get(id=program_id)
            ssc_result = float(ssc_result)
            hsc_result = float(hsc_result)
            if not (0 <= ssc_result <= 5 and 0 <= hsc_result <= 5):
                raise ValueError
            birth_date = parse_date(date_of_birth) if date_of_birth else None
            if date_of_birth and not birth_date:
                raise ValueError
        except (Program.DoesNotExist, TypeError, ValueError):
            messages.error(request, "Select a valid program, date, and results from 0 to 5.")
            return redirect("apply_admission")

        # Prevent duplicate application
        if profile and Application.objects.filter(
            student=profile
        ).exists():
            messages.error(
                request,
                "You have already submitted an application."
            )
            return redirect("apply_admission")

        # Create student profile
        if not profile:

            profile = StudentProfile.objects.create(
                user=request.user,
                phone=phone,
                date_of_birth=birth_date,
                address=address,
                photo=photo
            )

        else:

            profile.phone = phone
            profile.date_of_birth = birth_date
            profile.address = address

            if photo:
                profile.photo = photo

            profile.save()

        # Save student's name in Django User
        request.user.first_name = full_name
        request.user.save()

        # Generate application ID
        application_id = "APP-" + uuid.uuid4().hex[:8].upper()

        # Create application
        application = Application.objects.create(
            student=profile,
            program=program,
            application_id=application_id,
            ssc_result=ssc_result,
            hsc_result=hsc_result
        )
        fee = ApplicationFee.objects.create(application=application)
        PaymentHistory.objects.create(
            application=application,
            amount=fee.amount,
            status=fee.status,
            note="Application fee created",
        )

        # Save SSC document
        if ssc_certificate:
            Document.objects.create(
                application=application,
                document_name="SSC Certificate",
                file=ssc_certificate
            )

        # Save HSC document
        if hsc_certificate:
            Document.objects.create(
                application=application,
                document_name="HSC Certificate",
                file=hsc_certificate
            )

        messages.success(
            request,
            "Application submitted successfully."
        )

        return redirect("dashboard")

    return render(
        request,
        "admission/apply.html",
        {
            "programs": programs,
            "profile": profile,
        }
    )
@login_required
def application_details(request):

    profile = StudentProfile.objects.filter(
        user=request.user
    ).first()

    if not profile:
        messages.error(
            request,
            "You have not submitted an application yet."
        )
        return redirect("dashboard")

    application = Application.objects.filter(
        student=profile
    ).select_related("program").first()

    if not application:
        messages.error(
            request,
            "You have not submitted an application yet."
        )
        return redirect("dashboard")

    documents = Document.objects.filter(
        application=application
    )

    return render(
        request,
        "admission/application_details.html",
        {
            "application": application,
            "documents": documents,
            "profile": profile,
        }
    )


@login_required
def profile(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user, defaults={"phone": ""})
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        raw_date = request.POST.get("date_of_birth", "").strip()
        uploaded_photo = request.FILES.get("photo")
        if not full_name or not phone:
            messages.error(request, "Name and phone number are required.")
        elif len(full_name) > 150 or len(phone) > 20 or len(email) > 254:
            messages.error(request, "Name, phone, or email is too long.")
        elif email and not _valid_email(email):
            messages.error(request, "Enter a valid email address.")
        elif raw_date and not parse_date(raw_date):
            messages.error(request, "Enter a valid date of birth.")
        elif uploaded_photo and not _valid_image_upload(uploaded_photo):
            messages.error(request, "Upload a valid PNG or JPEG photo up to 5 MB.")
        else:
            request.user.first_name = full_name
            request.user.email = email
            request.user.save()
            profile.phone = phone
            profile.address = request.POST.get("address", "").strip()
            profile.date_of_birth = parse_date(raw_date) if raw_date else None
            if uploaded_photo:
                profile.photo = uploaded_photo
            profile.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def manage_documents(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    application = Application.objects.filter(student=profile).first() if profile else None
    if not application:
        messages.info(request, "Submit an application before managing documents.")
        return redirect("apply_admission")
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            document = Document.objects.filter(
                pk=request.POST.get("document_id"), application=application
            ).first()
            if document:
                document.file.delete(save=False)
                document.delete()
                messages.success(request, "Document removed.")
        else:
            uploaded = request.FILES.get("document")
            name = request.POST.get("document_name", "").strip()
            if uploaded and name and len(name) <= 100 and _valid_document_upload(uploaded):
                Document.objects.create(application=application, document_name=name, file=uploaded)
                messages.success(request, "Document uploaded.")
            else:
                messages.error(request, "Choose a PDF, PNG, or JPEG file up to 10 MB and enter a name of 100 characters or fewer.")
        return redirect("manage_documents")
    return render(request, "admission/documents.html", {
        "application": application,
        "documents": Document.objects.filter(application=application),
    })


@login_required
def document_download(request, document_id):
    document = get_object_or_404(
        Document.objects.select_related("application__student"), pk=document_id
    )
    is_owner = document.application.student.user_id == request.user.id
    if not is_owner:
        require_admin_or_owner(request.user, document.application.student.user_id)
    try:
        response = FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=Path(document.file.name).name,
            content_type="application/octet-stream",
        )
    except (FileNotFoundError, OSError):
        raise Http404
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def student_photo(request, profile_id):
    profile = get_object_or_404(StudentProfile, pk=profile_id)
    if profile.user_id != request.user.id:
        require_admin_or_owner(request.user, profile.user_id)
    if not profile.photo:
        raise Http404
    try:
        profile.photo.open("rb")
        with Image.open(profile.photo.file) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise Http404
            image = ImageOps.exif_transpose(source)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            image.thumbnail((1400, 1400))
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise Http404
    finally:
        profile.photo.close()
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@login_required
def protected_media(request, file_path):
    document = Document.objects.filter(file=file_path).only("pk").first()
    if document:
        return document_download(request, document.pk)
    profile = StudentProfile.objects.filter(photo=file_path).only("pk").first()
    if profile:
        return student_photo(request, profile.pk)
    raise Http404


@login_required
def print_application(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    application = Application.objects.filter(student=profile).select_related("program").first() if profile else None
    if not application:
        raise Http404("Application not found")
    fee = ApplicationFee.objects.filter(application=application).first()
    return render(request, "admission/print_application.html", {
        "application": application, "profile": profile, "fee": fee,
    })


@login_required
@require_POST
def confirm_admission(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    application = Application.objects.filter(student=profile, status="Approved").first() if profile else None
    if not application:
        messages.error(request, "Only an approved application can be confirmed.")
    else:
        with transaction.atomic():
            application.status = "Confirmed"
            application.save(update_fields=["status"])
            record, _created = StudentAdmissionRecord.objects.get_or_create(
                application=application
            )
            Notification.objects.create(
                student=profile,
                message=f"Your admission for {application.program.name} has been confirmed.",
            )
        messages.success(
            request,
            f"Your admission has been confirmed. Your student record number is {record.record_number}.",
        )
    return redirect("dashboard")


def _render_student_record(request, profile, records, staff_view=False):
    return render(request, "admission/student_record.html", {
        "profile": profile,
        "admission_records": records,
        "staff_view": staff_view,
    })


@login_required
def my_student_record(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    records = StudentAdmissionRecord.objects.filter(
        application__student=profile
    ).select_related(
        "application__program", "application__student__user"
    ).prefetch_related(
        "application__document_set", "application__payment_history__recorded_by"
    )
    if not records.exists():
        messages.info(request, "Your permanent student record will be available after you confirm an approved admission.")
        return redirect("dashboard")
    return _render_student_record(request, profile, records)


@admissions_staff_required
def staff_student_record(request, record_id):
    record = get_object_or_404(
        StudentAdmissionRecord.objects.select_related(
            "application__program", "application__student__user"
        ).prefetch_related(
            "application__document_set", "application__payment_history__recorded_by"
        ),
        pk=record_id,
    )
    profile = record.application.student
    return _render_student_record(request, profile, [record], staff_view=True)


@admissions_staff_required
def student_workspace(request):
    """Review one student's complete application and document history."""
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        application_id = request.POST.get("application_id")
        action = request.POST.get("action")
        profile = StudentProfile.objects.filter(pk=student_id).first()
        application = Application.objects.filter(
            pk=application_id, student=profile
        ).select_related("program").first() if profile else None

        if not application:
            messages.error(request, "That application could not be found for this student.")
        elif action in ("approve", "reject"):
            new_status = "Approved" if action == "approve" else "Rejected"
            application.status = new_status
            application.save(update_fields=["status"])
            Notification.objects.create(
                student=profile,
                message=f"Your admission application {application.application_id} has been {new_status.lower()}.",
            )
            messages.success(request, f"{application.application_id} marked {new_status.lower()}. The student was notified.")
        elif action == "payment":
            fee, fee_created = ApplicationFee.objects.get_or_create(application=application)
            if fee_created:
                PaymentHistory.objects.create(
                    application=application,
                    amount=fee.amount,
                    status=fee.status,
                    note="Application fee created",
                )
            if fee.status == "Paid":
                messages.error(request, f"Payment for {application.application_id} is already recorded.")
            else:
                fee.status = "Paid"
                fee.payment_reference = request.POST.get("payment_reference", "").strip()
                fee.paid_at = timezone.now()
                fee.save(update_fields=["status", "payment_reference", "paid_at"])
                PaymentHistory.objects.create(
                    application=application,
                    amount=fee.amount,
                    status=fee.status,
                    payment_reference=fee.payment_reference,
                    note="Payment accepted by admissions staff",
                    recorded_by=request.user,
                )
                Notification.objects.create(
                    student=profile,
                    message=f"Your application fee for {application.application_id} has been recorded as paid.",
                )
                messages.success(request, f"Payment recorded for {application.application_id}.")
        elif action == "notify":
            message = request.POST.get("message", "").strip()
            if message:
                Notification.objects.create(student=profile, message=message)
                messages.success(request, "Notification sent to the student.")
            else:
                messages.error(request, "Enter a message before sending a notification.")
        else:
            messages.error(request, "Choose a valid application action.")

        target = reverse("student_workspace")
        if profile:
            target += f"?student={profile.pk}"
            if application:
                target += f"&application={application.pk}"
        return redirect(target)

    students = StudentProfile.objects.select_related("user").prefetch_related(
        "application_set__program", "application_set__document_set", "application_set__fee"
    ).order_by("user__first_name", "user__username")

    overview_view = request.GET.get("view", "").strip().lower()
    if overview_view not in {"students", "applications", "pending", "fees"}:
        overview_view = ""

    student_records = StudentProfile.objects.select_related("user").annotate(
        application_count=Count("application")
    ).order_by("user__first_name", "user__username")
    overview_applications = Application.objects.select_related(
        "student__user", "program", "student"
    ).prefetch_related("fee").order_by("-submitted_at")
    if overview_view == "pending":
        overview_applications = overview_applications.filter(status="Pending")
    elif overview_view == "fees":
        overview_applications = overview_applications.filter(
            Q(fee__isnull=True) | Q(fee__status="Pending")
        )

    overview = {
        "student_count": StudentProfile.objects.count(),
        "application_count": Application.objects.count(),
        "pending_count": Application.objects.filter(status="Pending").count(),
        "unpaid_count": (
            Application.objects.filter(fee__isnull=True).count()
            + ApplicationFee.objects.filter(status="Pending").count()
        ),
        "active_notice_count": HomepageNotice.objects.filter(is_active=True).count(),
    }

    student_id = request.GET.get("student")
    profile = students.filter(pk=student_id).first() if student_id else students.first()
    applications = list(profile.application_set.all().order_by("-submitted_at")) if profile else []

    requested_application = request.GET.get("application")
    active_application = next(
        (app for app in applications if str(app.pk) == requested_application),
        applications[0] if applications else None,
    )

    return render(request, "admission/student_workspace.html", {
        "students": students,
        "profile": profile,
        "applications": applications,
        "active_application": active_application,
        "overview": overview,
        "overview_view": overview_view,
        "student_records": student_records,
        "overview_applications": overview_applications,
    })

@admissions_staff_required
def manage_homepage_notices(request):
    """Let staff publish, update, and archive announcements shown on the homepage."""
    if request.method == "POST" and request.POST.get("action") == "toggle":
        notice = get_object_or_404(HomepageNotice, pk=request.POST.get("notice_id"))
        notice.is_active = not notice.is_active
        notice.save(update_fields=["is_active", "updated_at"])
        state = "published" if notice.is_active else "archived"
        messages.success(request, f'“{notice.title}” was {state}.')
        return redirect("manage_homepage_notices")

    notice_id = (
        request.POST.get("notice_id")
        if request.method == "POST"
        else request.GET.get("edit")
    )
    instance = get_object_or_404(HomepageNotice, pk=notice_id) if notice_id else None
    form = HomepageNoticeForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        notice = form.save()
        messages.success(request, f'“{notice.title}” was saved.')
        return redirect("manage_homepage_notices")

    return render(request, "admission/manage_homepage_notices.html", {
        "form": form,
        "editing_notice": instance,
        "notices": HomepageNotice.objects.all(),
        "active_notice_count": HomepageNotice.objects.filter(is_active=True).count(),
    })

def home(request):
    homepage_notices = HomepageNotice.objects.filter(is_active=True).order_by("-updated_at")[:5]
    return render(request, "home.html", {
        "homepage_notices": homepage_notices,
        "is_admissions_admin": is_admin_account(request.user),
    })
