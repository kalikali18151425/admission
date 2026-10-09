from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


def generate_admission_record_number():
    return f"ISTT-{uuid.uuid4().hex[:12].upper()}"


class Program(models.Model):
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="students/", blank=True)

    def __str__(self):
        return self.user.username


class Application(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Confirmed", "Confirmed"),
    ]

    RESULT_CHOICES = [
        ("Pending", "Pending"),
        ("Eligible", "Eligible"),
        ("Not eligible", "Not eligible"),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE
    )

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE
    )

    application_id = models.CharField(
        max_length=20,
        unique=True
    )

    ssc_result = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    hsc_result = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    admission_result = models.CharField(
        max_length=20, choices=RESULT_CHOICES, default="Pending"
    )
    result_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.application_id


class ApplicationFee(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Paid", "Paid")]
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name="fee"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=1000)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    payment_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.application.application_id} — {self.status}"


class PaymentHistory(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Paid", "Paid")]

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="payment_history"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    payment_reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=160, blank=True)
    recorded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="admission_payment_history",
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-recorded_at", "-pk")
        verbose_name_plural = "payment histories"

    def __str__(self):
        return f"{self.application.application_id} — {self.status} — {self.amount}"


class StudentAdmissionRecord(models.Model):
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name="student_record"
    )
    record_number = models.CharField(
        max_length=18, unique=True, default=generate_admission_record_number,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")

    def __str__(self):
        return self.record_number


class Document(models.Model):

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE
    )

    document_name = models.CharField(max_length=100)

    file = models.FileField(
        upload_to="documents/"
    )

    def __str__(self):
        return self.document_name
class Notification(models.Model):

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.message


class HomepageNotice(models.Model):
    title = models.CharField(max_length=140)
    message = models.TextField(max_length=1200)
    link_url = models.URLField(blank=True)
    link_label = models.CharField(max_length=50, blank=True, default="Read details")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-pk")
        verbose_name = "homepage notice"
        verbose_name_plural = "homepage notices"

    def __str__(self):
        return self.title
    
