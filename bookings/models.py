from django.db import models
from django.conf import settings
from django_prose_editor.fields import ProseEditorField


class Booking(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        limit_choices_to={"role": "doctor"},
        db_index=True, 
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
        limit_choices_to={"role": "patient"},
        db_index=True,
    )
    appointment_date = models.DateField(db_index=True)  # ✅ ADD INDEX
    appointment_time = models.TimeField()
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="pending",
        db_index=True,  # ✅ ADD INDEX
    )

    class Meta:
        ordering = ["-appointment_date", "-appointment_time"]
        unique_together = ["doctor", "appointment_date", "appointment_time"]
        indexes = [  # ✅ ADD COMPOSITE INDEXES
            models.Index(fields=["doctor", "appointment_date"]),
            models.Index(fields=["patient", "appointment_date"]),
            models.Index(fields=["status", "appointment_date"]),
        ]

    def __str__(self):
        return f"Appointment with Dr. {self.doctor.get_full_name()} on {self.appointment_date} at {self.appointment_time}"

class Prescription(models.Model):
    booking = models.OneToOneField(
        "Booking", on_delete=models.CASCADE, related_name="prescription"
    )
    doctor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="prescriptions_given",
    )
    patient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="prescriptions_received",
    )
    symptoms = models.TextField()
    diagnosis = models.TextField()
    medications = ProseEditorField(
        extensions={
            "Bold": True,
            "Italic": True,
            "BulletList": True,
            "ListItem": True,
            "Link": {
                "protocols": ["http", "https", "mailto"],
            },
        },
        sanitize=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription for {self.patient} by Dr. {self.doctor}"

    class Meta:
        ordering = ["-created_at"]
