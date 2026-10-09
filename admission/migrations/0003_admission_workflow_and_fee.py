import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("admission", "0002_notification")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="admission_result",
            field=models.CharField(
                choices=[("Pending", "Pending"), ("Eligible", "Eligible"), ("Not eligible", "Not eligible")],
                default="Pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="result_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="application",
            name="status",
            field=models.CharField(
                choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected"), ("Confirmed", "Confirmed")],
                default="Pending",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="ApplicationFee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, default=1000, max_digits=8)),
                ("status", models.CharField(choices=[("Pending", "Pending"), ("Paid", "Paid")], default="Pending", max_length=10)),
                ("payment_reference", models.CharField(blank=True, max_length=100)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="fee", to="admission.application")),
            ],
        ),
    ]
