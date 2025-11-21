import json
from datetime import datetime

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    Http404,
    HttpResponsePermanentRedirect,
)
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic import (
    ListView,
    DetailView,
    View,
    CreateView,
    UpdateView,
)
from django.views.generic.base import TemplateView
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from django.db.models import Q
from django.db.models import Count
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin

from bookings.models import Booking, Prescription
from core.models import Review
from core.decorators import user_is_doctor
from doctors.forms import DoctorProfileForm, PrescriptionForm
from doctors.models import Experience
from doctors.models.general import *
from doctors.serializers import (
    EducationSerializer,
    ExperienceSerializer,
    RegistrationNumberSerializer,
    SpecializationSerializer,
)
from mixins.custom_mixins import DoctorRequiredMixin
from patients.forms import ChangePasswordForm
from utils.htmx import render_toast_message_for_api
from accounts.models import User
from django.db import transaction
from django.db.models import Prefetch
import logging
import re

# Configure logger
logger = logging.getLogger(__name__)


days = {
    0: Sunday,
    1: Monday,
    2: Tuesday,
    3: Wednesday,
    4: Thursday,
    5: Friday,
    6: Saturday,
}


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    template_name = "doctors/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Get appointment counts
        context["total_patients"] = (
            Booking.objects.filter(doctor=self.request.user)
            .values("patient")
            .distinct()
            .count()
        )

        context["today_patients"] = Booking.objects.filter(
            doctor=self.request.user, appointment_date=today
        ).count()

        context["total_appointments"] = Booking.objects.filter(
            doctor=self.request.user
        ).count()

        # Get upcoming appointments
        context["upcoming_appointments"] = (
            Booking.objects.select_related("patient", "patient__profile")
            .filter(
                doctor=self.request.user,
                appointment_date__gte=today,
                status__in=["pending", "confirmed"],
            )
            .order_by("appointment_date", "appointment_time")[:10]
        )

        # Get today's appointments
        context["today_appointments"] = (
            Booking.objects.select_related("patient", "patient__profile")
            .filter(doctor=self.request.user, appointment_date=today)
            .order_by("appointment_time")
        )

        return context


def convert_to_24_hour_format(time_str):
    if time_str == "00:00 AM":
        time_str = "12:00 AM"
    return datetime.strptime(time_str, "%I:%M %p").time()


@login_required
@user_is_doctor
def schedule_timings(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        data = request.POST
        for i in range(7):
            if data.get(f"day_{i}", None):
                start_times = data.getlist(f"start_time_{i}", default=[])
                end_times = data.getlist(f"end_time_{i}", default=[])
                for index in range(len(start_times)):
                    start = convert_to_24_hour_format(start_times[index])
                    end = convert_to_24_hour_format(end_times[index])
                    time_range, time_created = TimeRange.objects.get_or_create(
                        start=start, end=end
                    )
                    day, created = days[i].objects.get_or_create(
                        user=request.user
                    )
                    ranges = day.time_range
                    if time_range.id not in list(
                        ranges.values_list("id", flat=True)
                    ):
                        day.time_range.add(time_range)

        return HttpResponsePermanentRedirect(
            reverse_lazy("doctors:schedule-timings")
        )

    return render(request, "doctors/schedule-timings.html")


class DoctorProfileUpdateView(DoctorRequiredMixin, generic.UpdateView):
    model = User
    template_name = "doctors/profile-settings.html"
    form_class = DoctorProfileForm

    def get_object(self, queryset=None):
        return self.request.user


class DoctorProfileView(DetailView):
    context_object_name = "doctor"
    model = User
    slug_url_kwarg = "username"
    slug_field = "username"
    template_name = "doctors/profile.html"

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        slug = self.kwargs.get(self.slug_url_kwarg)
        
        # ✅ OPTIMIZED: Single query with select_related and prefetch_related
        queryset = queryset.select_related("profile").prefetch_related(
            "educations",
            "experiences",
            "reviews_received__patient__profile",  # ✅ ADD THIS
            "sunday__time_range",
            "monday__time_range",
            "tuesday__time_range",
            "wednesday__time_range",
            "thursday__time_range",
            "friday__time_range",
            "saturday__time_range",
        )

        try:
            obj = queryset.get(
                **{self.slug_field: slug, "role": User.RoleChoices.DOCTOR}
            )
        except User.DoesNotExist:
            raise Http404(f"No doctor found matching the username")

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object

        # Get current day name
        current_day = datetime.now().strftime("%A")

        # Prepare business hours
        business_hours = {
            "Sunday": (
                doctor.sunday.time_range.all()
                if hasattr(doctor, "sunday")
                else []
            ),
            "Monday": (
                doctor.monday.time_range.all()
                if hasattr(doctor, "monday")
                else []
            ),
            "Tuesday": (
                doctor.tuesday.time_range.all()
                if hasattr(doctor, "tuesday")
                else []
            ),
            "Wednesday": (
                doctor.wednesday.time_range.all()
                if hasattr(doctor, "wednesday")
                else []
            ),
            "Thursday": (
                doctor.thursday.time_range.all()
                if hasattr(doctor, "thursday")
                else []
            ),
            "Friday": (
                doctor.friday.time_range.all()
                if hasattr(doctor, "friday")
                else []
            ),
            "Saturday": (
                doctor.saturday.time_range.all()
                if hasattr(doctor, "saturday")
                else []
            ),
        }

        context.update(
            {
                "current_day": current_day,
                "business_hours": business_hours,
                "reviews": doctor.reviews_received.select_related(
                    "patient", "patient__profile"
                ).order_by("-created_at"),
            }
        )

        return context


class UpdateEducationAPIView(DoctorRequiredMixin, UpdateAPIView):
    queryset = Experience.objects.all()
    serializer_class = EducationSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.id)

    @transaction.atomic  # ✅ ADD THIS
    def update(self, request, *args, **kwargs):
        data = request.POST
        ids = data.getlist("id", default=[])
        degrees = data.getlist("degree", default=[])
        colleges = data.getlist("college", default=[])
        years = data.getlist("year_of_completion", default=[])
        
        errors = []
        
        for i in range(len(degrees)):
            try:
                if i < len(ids) and ids[i]:
                    # Update existing
                    try:
                        instance = self.request.user.educations.get(id=ids[i])
                        serializer = self.get_serializer(
                            instance,
                            data={
                                "degree": degrees[i],
                                "college": colleges[i],
                                "year_of_completion": years[i] if i < len(years) else None,
                            },
                            partial=True,
                        )
                        serializer.is_valid(raise_exception=True)
                        self.perform_update(serializer)
                    except Exception as e:
                        errors.append(f"Error updating education {i+1}: {str(e)}")
                else:
                    # Create new
                    serializer = self.get_serializer(
                        data={
                            "degree": degrees[i],
                            "college": colleges[i],
                            "year_of_completion": years[i] if i < len(years) else None,
                        }
                    )
                    serializer.is_valid(raise_exception=True)
                    self.perform_update(serializer)
            except Exception as e:
                errors.append(f"Error processing education {i+1}: {str(e)}")

        if errors:
            return render_toast_message_for_api(
                "Education", "; ".join(errors), "error"
            )

        return render_toast_message_for_api(
            "Education", "Updated successfully", "success"
        )


class UpdateExperienceAPIView(DoctorRequiredMixin, UpdateAPIView):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.id)

    @transaction.atomic  # ✅ Added transaction
    def update(self, request, *args, **kwargs):
        data = request.POST
        
        # Get all lists from the form data
        ids = data.getlist("id", default=[])
        institutions = data.getlist("institution", default=[])
        from_years = data.getlist("from_year", default=[])
        to_years = data.getlist("to_year", default=[])
        designations = data.getlist("designation", default=[])

        errors = []  # ✅ List to collect errors

        # Loop based on the main field, 'institutions'
        for i in range(len(institutions)):
            try:
                # Consolidate data for this item
                experience_data = {
                    "institution": institutions[i],
                    # Add safety checks
                    "from_year": from_years[i] if i < len(from_years) else None,
                    "to_year": to_years[i] if i < len(to_years) else None,
                    "designation": designations[i] if i < len(designations) else None,
                }

                # ✅ Check if a valid ID was provided to decide between update/create
                if i < len(ids) and ids[i]:
                    # This is an UPDATE
                    try:
                        instance = self.request.user.experiences.get(id=ids[i])
                        serializer = self.get_serializer(
                            instance,
                            data=experience_data,
                            partial=True,
                        )
                        serializer.is_valid(raise_exception=True)
                        self.perform_update(serializer)
                    except Exception as e:
                        # ✅ Catch error for this specific item
                        logger.error(f"Error updating experience {ids[i]}: {str(e)}")
                        errors.append(f"Error updating experience {i+1}: {str(e)}")
                else:
                    # This is a CREATE
                    serializer = self.get_serializer(
                        data=experience_data
                    )
                    serializer.is_valid(raise_exception=True)
                    self.perform_update(serializer)
                    
            except Exception as e:
                # ✅ Catch error for processing this item
                logger.error(f"Error processing experience item {i+1}: {str(e)}")
                errors.append(f"Error processing experience {i+1}: {str(e)}")

        # ✅ Check for errors after the loop
        if errors:
            return render_toast_message_for_api(
                "Experience", "; ".join(errors), "error"
            )

        # ✅ Return success if no errors
        return render_toast_message_for_api(
            "Experience", "Updated successfully", "success"
        )


class UpdateRegistrationNumberAPIView(DoctorRequiredMixin, UpdateAPIView):
    serializer_class = RegistrationNumberSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        data = request.POST
        serializer = self.get_serializer(instance=request.user, data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return render_toast_message_for_api(
            "BM&DC number", "Updated successfully", "success"
        )


class UpdateSpecializationAPIView(DoctorRequiredMixin, UpdateAPIView):
    serializer_class = SpecializationSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.POST
        specialist = data.get("specialist")
        instance.profile.specialization = specialist
        instance.profile.save()

        return render_toast_message_for_api(
            "Specialization", "Updated successfully", "success"
        )


class DoctorsListView(ListView):
    model = User
    context_object_name = "doctors"
    template_name = "doctors/list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = self.model.objects.filter(
            role=User.RoleChoices.DOCTOR, 
            is_superuser=False, 
            is_active=True
        ).select_related("profile").prefetch_related(
            Prefetch(
                'reviews_received',
                queryset=Review.objects.select_related('patient', 'patient__profile')
            )
        )

        # Handle search query - sanitize input
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            # Limit search query length to prevent DOS
            search_query = re.sub(r'[^\w\s\-\']', '', search_query)[:100]
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(profile__specialization__icontains=search_query)
                | Q(profile__city__icontains=search_query)
            )

        # Handle gender filter - validate against allowed values
        gender = self.request.GET.getlist("gender")
        allowed_genders = ['male', 'female', 'other']
        if gender:
            validated_genders = [g for g in gender if g in allowed_genders]
            if validated_genders:
                queryset = queryset.filter(profile__gender__in=validated_genders)

        # Handle specialization filter - validate against existing specializations
        specializations = self.request.GET.getlist("specialization")
        if specializations:
            # Sanitize and validate
            valid_specializations = []
            for spec in specializations:
                cleaned_spec = spec.strip()[:255]  # Limit length
                if cleaned_spec:
                    valid_specializations.append(cleaned_spec)
            
            if valid_specializations:
                queryset = queryset.filter(
                    profile__specialization__in=valid_specializations
                )

        # Handle sorting - validate against allowed values
        sort_by = self.request.GET.get("sort", "").strip()
        allowed_sorts = {
            "price_low": "profile__price_per_consultation",
            "price_high": "-profile__price_per_consultation",
            "rating": "-rating",
            "experience": "-profile__experience"
        }
        
        if sort_by in allowed_sorts:
            queryset = queryset.order_by(allowed_sorts[sort_by])
        else:
            queryset = queryset.order_by("-pk")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add search query to context
        context["search_query"] = self.request.GET.get("q")

        # Add unique specializations to context
        specializations = (
            User.objects.filter(role=User.RoleChoices.DOCTOR, is_active=True)
            .exclude(profile__specialization__isnull=True)
            .values_list("profile__specialization", flat=True)
            .distinct()
        )

        context["specializations"] = sorted(
            list(filter(None, specializations))
        )

        return context


class AppointmentListView(DoctorRequiredMixin, ListView):
    model = Booking
    context_object_name = "appointments"
    template_name = "doctors/appointments.html"
    paginate_by = 10

    def get_queryset(self):
        return (
            self.model.objects.select_related(
                "doctor", "doctor__profile", "patient", "patient__profile"
            )
            .filter(doctor=self.request.user)
            .order_by("-appointment_date", "-appointment_time")
        )


class AppointmentDetailView(DoctorRequiredMixin, DetailView):
    model = Booking
    template_name = "doctors/appointment-detail.html"
    context_object_name = "appointment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object.patient

        # Get patient's appointment history with this doctor
        context["patient_history"] = (
            Booking.objects.select_related("doctor", "doctor__profile")
            .filter(
                doctor=self.request.user,
                patient=patient,
                appointment_date__lt=self.object.appointment_date,
            )
            .order_by("-appointment_date", "-appointment_time")
        )

        # Get total visits count
        context["total_visits"] = Booking.objects.filter(
            doctor=self.request.user, patient=patient, status="completed"
        ).count()

        return context


class AppointmentActionView(DoctorRequiredMixin, View):
    def post(self, request, pk, action):
        appointment = get_object_or_404(
            Booking,
            pk=pk,
            doctor=request.user,
            status__in=["pending", "confirmed"],
        )

        if action == "accept":
            appointment.status = "confirmed"
            messages.success(request, "Appointment confirmed successfully")
        elif action == "cancel":
            appointment.status = "cancelled"
            messages.success(request, "Appointment cancelled successfully")
        elif action == "completed":
            appointment.status = "completed"
            messages.success(
                request, "Appointment marked as completed successfully"
            )

        appointment.save()
        return redirect("doctors:dashboard")


class MyPatientsView(DoctorRequiredMixin, ListView):
    template_name = "doctors/my-patients.html"
    context_object_name = "patients"

    def get_queryset(self):
        return (
            User.objects.filter(
                patient_appointments__doctor=self.request.user, role="patient"
            )
            .distinct()
            .select_related("profile")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get appointment counts for each patient
        patient_stats = {}
        for patient in context["patients"]:
            stats = Booking.objects.filter(
                doctor=self.request.user, patient=patient
            ).aggregate(
                total_appointments=Count("id"),
                completed_appointments=Count(
                    "id", filter=Q(status="completed")
                ),
            )
            patient_stats[patient.id] = stats
        context["patient_stats"] = patient_stats
        return context


class AppointmentHistoryView(DoctorRequiredMixin, ListView):
    model = Booking
    template_name = "doctors/appointment-history.html"
    context_object_name = "appointments"

    def get_queryset(self):
        return (
            self.model.objects.select_related("patient", "patient__profile")
            .filter(
                doctor=self.request.user, patient_id=self.kwargs["patient_id"]
            )
            .order_by("-appointment_date", "-appointment_time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient"] = get_object_or_404(
            User.objects.select_related("profile"),
            id=self.kwargs["patient_id"],
            role="patient",
        )
        return context


class DoctorChangePasswordView(DoctorRequiredMixin, View):
    template_name = "doctors/change-password.html"

    def get(self, request, *args, **kwargs):
        return render(
            request, self.template_name, {"form": ChangePasswordForm()}
        )

    def post(self, request, *args, **kwargs):
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user = request.user

            if user.check_password(form.cleaned_data["old_password"]):
                user.set_password(form.cleaned_data["new_password"])
                user.save()

                # Update session to prevent logout
                update_session_auth_hash(request, user)

                messages.success(request, "Password changed successfully")
                return redirect("doctors:dashboard")
            else:
                messages.error(request, "Current password is incorrect")

        return render(request, self.template_name, {"form": form})


class PrescriptionCreateView(DoctorRequiredMixin, CreateView):
    model = Prescription
    form_class = PrescriptionForm
    template_name = "doctors/add_prescription.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.kwargs.get("booking_id")
        context["booking"] = get_object_or_404(
            Booking, id=booking_id, doctor=self.request.user
        )
        return context

    def form_valid(self, form):
        booking_id = self.kwargs.get("booking_id")
        booking = get_object_or_404(
            Booking, id=booking_id, doctor=self.request.user
        )

        if booking.status != "completed":
            messages.error(
                self.request,
                "Can only add prescription for completed appointments",
            )
            return redirect("doctors:appointment-detail", pk=booking_id)

        form.instance.booking = booking
        form.instance.doctor = self.request.user
        form.instance.patient = booking.patient
        messages.success(self.request, "Prescription added successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "doctors:appointment-detail",
            kwargs={"pk": self.kwargs["booking_id"]},
        )


class PrescriptionDetailView(LoginRequiredMixin, DetailView):
    model = Prescription
    template_name = "doctors/prescription_detail.html"
    context_object_name = "prescription"

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Prescription.objects.none()
        
        # Doctors can view prescriptions they wrote
        if user.role == 'doctor':
            return Prescription.objects.filter(
                doctor=user
            ).select_related(
                "doctor",
                "doctor__profile",
                "patient",
                "patient__profile",
                "booking",
            )
        
        # Patients can view their own prescriptions
        elif user.role == 'patient':
            return Prescription.objects.filter(
                patient=user
            ).select_related(
                "doctor",
                "doctor__profile",
                "patient",
                "patient__profile",
                "booking",
            )
        
        # No access for others (including superusers accessing via URL)
        return Prescription.objects.none()
    
    def dispatch(self, request, *args, **kwargs):
        # Verify the prescription exists and user has access
        try:
            self.get_object()
        except:
            from django.http import Http404
            raise Http404("Prescription not found or access denied")
        return super().dispatch(request, *args, **kwargs)