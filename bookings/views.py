from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.http import HttpRequest, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic.base import TemplateView

from accounts.models import User
from doctors.models.general import TimeRange
from mixins.custom_mixins import PatientRequiredMixin
from .models import Booking
from django_ratelimit.decorators import ratelimit
from django.db import transaction, IntegrityError
from django.utils.decorators import method_decorator
from django.utils import timezone

class BookingView(LoginRequiredMixin, View):
    template_name = "bookings/booking.html"

    def get_week_dates(self):
        """Get the next 7 days starting from today"""
        today = datetime.now().date()
        week_dates = []
        for i in range(7):
            date = today + timedelta(days=i)
            week_dates.append(
                {
                    "date": date,
                    "day": date.strftime("%a"),
                    "day_num": date.strftime("%d"),
                    "month": date.strftime("%b"),
                    "year": date.strftime("%Y"),
                    "full_date": date.strftime("%Y-%m-%d"),
                }
            )
        return week_dates

    def get_available_slots(self, doctor, date):
        """Get available time slots for a specific date"""
        day_name = date.strftime("%A").lower()
        day_schedule = getattr(doctor, day_name, None)

        if not day_schedule or not day_schedule.time_range.exists():
            return []

        booked_times = set(
            doctor.appointments.filter(
                appointment_date=date,
                status__in=["pending", "confirmed"]
            ).values_list('appointment_time', flat=True)
        )

        time_slots = []
        now = timezone.now()

        for time_range in day_schedule.time_range.all():

            # Get slot duration
            slot_duration = time_range.get_slot_duration()

            # Convert time range to slots (e.g., 30-minute intervals)
            current_time = datetime.combine(date, time_range.start)
            end_time = datetime.combine(date, time_range.end)

            # Limit to prevent excessive iterations
            max_slots = 50
            slot_count = 0

            while current_time < end_time and slot_count < max_slots:
                slot_count += 1
                # Skip past times
                if date == now.date() and current_time.time() < now.time():
                    current_time += timedelta(minutes=slot_duration)
                    continue
            
                # Check if slot is available
                if current_time.time() not in booked_times:
                    time_slots.append({
                    "time": current_time.time(),
                    "formatted_time": current_time.strftime("%I:%M %p"),
                })
            
                current_time += timedelta(minutes=slot_duration)
                

        return time_slots

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            doctor = (
                User.objects.select_related("profile")
                .prefetch_related(
                    "sunday__time_range",
                    "monday__time_range",
                    "tuesday__time_range",
                    "wednesday__time_range",
                    "thursday__time_range",
                    "friday__time_range",
                    "saturday__time_range",
                    "appointments",
                )
                .get(
                    username=kwargs["username"],
                    role=User.RoleChoices.DOCTOR,
                    is_active=True,
                )
            )
        except User.DoesNotExist:
            raise Http404("Doctor not found")

        # Get week dates
        week_dates = self.get_week_dates()

        # Get available slots for each day
        schedule = {}
        for date_info in week_dates:
            date = datetime.strptime(date_info["full_date"], "%Y-%m-%d").date()
            schedule[date_info["full_date"]] = self.get_available_slots(
                doctor, date
            )

        context = {
            "doctor": doctor,
            "week_dates": week_dates,
            "schedule": schedule,
            "selected_date": request.GET.get(
                "date", week_dates[0]["full_date"]
            ),
        }

        return render(request, self.template_name, context)


@method_decorator(ratelimit(key='user', rate='10/h'), name='dispatch')
class BookingCreateView(LoginRequiredMixin, View):
    template_name = "bookings/booking.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, username):
        doctor = get_object_or_404(User, username=username, role="doctor", is_active=True)
        
        date = request.POST.get("selected_date")
        time = request.POST.get("selected_time")
        
        if not date or not time:
            messages.error(request, "Please select both date and time")
            return redirect("bookings:doctor-booking-view", username=username)
        
        try:
            appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
            appointment_time = datetime.strptime(time, "%H:%M").time()
            
            # Validate future datetime
            now = timezone.now()
            appointment_datetime = timezone.make_aware(
                datetime.combine(appointment_date, appointment_time)
            )
            
            if appointment_datetime < now:
                messages.error(request, "Cannot book appointments in the past")
                return redirect("bookings:doctor-booking-view", username=username)
            
            # FIX: Use atomic transaction with select_for_update to prevent race condition
            with transaction.atomic():
                # Lock BOTH doctor's schedule AND patient's schedule
                locked_doctor_bookings = Booking.objects.select_for_update().filter(
                    doctor=doctor,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status__in=["pending", "confirmed"]
                )

                locked_patient_bookings = Booking.objects.select_for_update().filter(
                    patient=request.user,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status__in=["pending", "confirmed"]
                )

                if locked_doctor_bookings.exists():
                    messages.error(request, "This time slot is already booked")
                    return redirect("bookings:doctor-booking-view", username=username)
                
                if locked_patient_bookings.exists():
                    messages.error(request, "You already have an appointment at this time")
                    return redirect("bookings:doctor-booking-view", username=username)
                
                # Verify doctor availability
                day_name = appointment_date.strftime("%A").lower()
                day_schedule = getattr(doctor, day_name, None)
                
                if not day_schedule or not day_schedule.time_range.exists():
                    messages.error(request, f"Doctor not available on {appointment_date.strftime('%A')}s")
                    return redirect("bookings:doctor-booking-view", username=username)
                
                # Verify time within working hours
                is_valid_time = False
                for time_range in day_schedule.time_range.all():
                    if time_range.start <= appointment_time <= time_range.end:
                        is_valid_time = True
                        break
                
                if not is_valid_time:
                    messages.error(request, "Selected time outside doctor's working hours")
                    return redirect("bookings:doctor-booking-view", username=username)
                
                # Prevent double booking by same patient
                patient_existing = Booking.objects.filter(
                    patient=request.user,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status__in=["pending", "confirmed"]
                ).exists()
                
                if patient_existing:
                    messages.error(request, "You already have an appointment at this time")
                    return redirect("bookings:doctor-booking-view", username=username)
                
                # Create booking atomically
                booking = Booking.objects.create(
                    doctor=doctor,
                    patient=request.user,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status="pending"
                )
            
            messages.success(
                request,
                f"Appointment booked for {appointment_date} at {appointment_time.strftime('%I:%M %p')}"
            )
            return redirect("bookings:booking-success", booking_id=booking.id)
            
        except IntegrityError:
            messages.error(request, "This time slot was just booked. Please choose another")
            return redirect("bookings:doctor-booking-view", username=username)
        except ValueError:
            messages.error(request, "Invalid date or time format")
            return redirect("bookings:doctor-booking-view", username=username)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Booking error: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred. Please try again")
            return redirect("bookings:doctor-booking-view", username=username)


class BookingSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "bookings/booking-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["booking"] = Booking.objects.get(id=kwargs["booking_id"])
        return context


class BookingInvoiceView(LoginRequiredMixin, TemplateView):
    template_name = "bookings/booking-invoice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = get_object_or_404(
            Booking.objects.select_related(
                "doctor", "doctor__profile", "patient", "patient__profile"
            ),
            id=kwargs["booking_id"],
        )

        # Ensure user can only view their own bookings
        if not (
            self.request.user == booking.patient
            or self.request.user == booking.doctor
        ):
            raise Http404("Not found")

        context["booking"] = booking
        context["issued_date"] = booking.booking_date.strftime("%d/%m/%Y")

        # Calculate invoice amounts
        consultation_fee = booking.doctor.profile.price_per_consultation
        context["subtotal"] = consultation_fee
        context["total"] = (
            consultation_fee  # Add any additional fees/discounts here
        )

        return context


class BookingListView(LoginRequiredMixin, View):
    template_name = "bookings/booking-list.html"
    
    def get(self, request: HttpRequest, *args, **kwargs):
        # Get all bookings for the logged-in user
        if request.user.role == User.RoleChoices.DOCTOR:
            bookings = Booking.objects.filter(doctor=request.user)
        else:
            bookings = Booking.objects.filter(patient=request.user)
            
        # Prefetch related data to avoid N+1 queries
        bookings = bookings.select_related(
            'doctor', 
            'doctor__profile',
            'patient', 
            'patient__profile'
        ).order_by('-appointment_date', '-appointment_time')
        
        context = {
            'bookings': bookings,
        }
        
        return render(request, self.template_name, context)
