from io import BytesIO
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from PIL import Image

from .models import Application, Document, Program, StudentProfile


class AdmissionAccessTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_directory = tempfile.TemporaryDirectory(dir=settings.BASE_DIR)
        cls.media_settings = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_settings.disable()
        cls.media_directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.owner = User.objects.create_user(username="student_owner", password="test-passphrase")
        self.other = User.objects.create_user(username="student_other", password="test-passphrase")
        self.staff = User.objects.create_user(
            username="admissions_staff", password="test-passphrase", is_staff=True
        )
        self.profile = StudentProfile.objects.create(user=self.owner, phone="0123456789")
        program = Program.objects.create(name="Test program", department="Testing")
        self.application = Application.objects.create(
            student=self.profile,
            program=program,
            application_id="APP-TEST0001",
            ssc_result="4.50",
            hsc_result="4.25",
        )
        self.document = Document.objects.create(
            application=self.application,
            document_name="Certificate",
            file=SimpleUploadedFile("certificate.pdf", b"%PDF-1.4\nTest file"),
        )
        image_bytes = BytesIO()
        Image.new("RGB", (8, 8), "white").save(image_bytes, format="PNG")
        self.profile.photo.save(
            "student-photo.png",
            SimpleUploadedFile("student-photo.png", image_bytes.getvalue(), content_type="image/png"),
        )

    def test_private_documents_require_login_and_belong_to_owner_or_staff(self):
        download_url = reverse("document_download", args=[self.document.pk])
        media_url = "/media/" + self.document.file.name

        anonymous = Client()
        self.assertEqual(anonymous.get(download_url).status_code, 302)
        self.assertIn("/login/", anonymous.get(download_url)["Location"])
        self.assertEqual(anonymous.get(media_url).status_code, 302)

        other_client = Client()
        other_client.force_login(self.other)
        self.assertEqual(other_client.get(download_url).status_code, 404)
        self.assertEqual(other_client.get(media_url).status_code, 404)

        owner_client = Client()
        owner_client.force_login(self.owner)
        response = owner_client.get(download_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4\nTest file")
        response.close()
        response = owner_client.get(media_url)
        self.assertEqual(response.status_code, 200)
        response.close()

        staff_client = Client()
        staff_client.force_login(self.staff)
        response = staff_client.get(download_url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_student_photos_are_private_and_return_sanitized_images(self):
        photo_url = reverse("student_photo", args=[self.profile.pk])
        media_url = "/media/" + self.profile.photo.name

        anonymous = Client()
        self.assertEqual(anonymous.get(photo_url).status_code, 302)
        self.assertEqual(anonymous.get(media_url).status_code, 302)

        other_client = Client()
        other_client.force_login(self.other)
        self.assertEqual(other_client.get(photo_url).status_code, 404)
        self.assertEqual(other_client.get(media_url).status_code, 404)

        owner_client = Client()
        owner_client.force_login(self.owner)
        response = owner_client.get(photo_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(Image.open(BytesIO(response.content)).format, "PNG")

    def test_student_pages_redirect_to_the_project_login(self):
        client = Client()
        for page in (
            "dashboard", "apply_admission", "application_details", "profile",
            "manage_documents", "print_application",
        ):
            response = client.get(reverse(page))
            self.assertEqual(response.status_code, 302, page)
            self.assertTrue(response["Location"].startswith("/login/"), page)

    def test_review_page_requires_staff_access(self):
        client = Client()
        client.force_login(self.other)
        self.assertEqual(client.get(reverse("student_workspace")).status_code, 302)
