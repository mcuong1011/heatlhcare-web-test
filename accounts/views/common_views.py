from django.contrib import messages, auth
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, RedirectView, UpdateView
from rest_framework.generics import UpdateAPIView

from accounts.forms import (
    DoctorRegistrationForm,
    PatientRegistrationForm,
    UserLoginForm,
)
from accounts.models import User
from accounts.serializers import BasicUserInformationSerializer
from utils.htmx import render_toast_message_for_api
from django.db import transaction


class RegisterDoctorView(CreateView):
    model = User
    form_class = DoctorRegistrationForm
    template_name = "accounts/register.html"
    success_url = "/"

    extra_context = {"title": "Register"}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(self.request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        form = self.form_class(data=request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get("password1")
            user.set_password(password)
            user.save()
            return redirect("accounts:login")
        else:
            return render(request, "accounts/register.html", {"form": form})


class RegisterPatientView(CreateView):
    form_class = PatientRegistrationForm
    template_name = "accounts/register.html"
    success_url = "/"

    extra_context = {"title": "Register"}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(self.request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        form = self.form_class(data=request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get("password1")
            user.set_password(password)
            user.save()
            return redirect("accounts:login")
        else:
            return render(request, "accounts/register.html", {"form": form})


class LoginView(FormView):
    """
    Provides the ability to login as a user with an email and password
    """

    success_url = "/"
    form_class = UserLoginForm
    template_name = "accounts/login.html"

    extra_context = {"title": "Login"}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(self.request, *args, **kwargs)

    def get_success_url(self):
        if "next" in self.request.GET and self.request.GET["next"] != "":
            return self.request.GET["next"]
        else:
            return self.success_url

    def get_form_class(self):
        return self.form_class

    def form_valid(self, form):
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(RedirectView):
    """
    Provides users the ability to logout
    """

    url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        auth.logout(request)
        messages.success(request, "You are now logged out")
        return super(LogoutView, self).get(request, *args, **kwargs)


class UpdateBasicUserInformationAPIView(LoginRequiredMixin, UpdateAPIView):
    serializer_class = BasicUserInformationSerializer

    def get_object(self):
        return self.request.user

    @transaction.atomic  # Add transaction
    def put(self, request, *args, **kwargs):
        try:
            user = request.user
            data = request.data if hasattr(request, 'data') else request.POST
            files = request.FILES

            # Update user information
            user.first_name = data.get("first_name", user.first_name).strip()
            user.last_name = data.get("last_name", user.last_name).strip()
            
            # Validate names are not empty
            if not user.first_name or not user.last_name:
                return render_toast_message_for_api(
                    "Error", "First name and last name are required", "error"
                )
            
            user.save()

            # Update profile information
            user_profile = user.profile
            
            # Validate DOB
            dob = data.get("dob")
            if dob:
                from datetime import datetime
                try:
                    dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
                    if dob_date > datetime.now().date():
                        return render_toast_message_for_api(
                            "Error", "Date of birth cannot be in the future", "error"
                        )
                    user_profile.dob = dob_date
                except ValueError:
                    return render_toast_message_for_api(
                        "Error", "Invalid date format. Use YYYY-MM-DD", "error"
                    )
            
            # Validate and update phone
            phone = data.get("phone", "").strip()
            if phone:
                # Basic phone validation
                if not phone.replace("+", "").replace(" ", "").replace("-", "").isdigit():
                    return render_toast_message_for_api(
                        "Error", "Invalid phone number format", "error"
                    )
                user_profile.phone = phone

            # Handle avatar file upload
            if "avatar" in files:
                # Validate file size (max 5MB)
                if files["avatar"].size > 5 * 1024 * 1024:
                    return render_toast_message_for_api(
                        "Error", "Avatar file size must be less than 5MB", "error"
                    )
                user_profile.avatar = files["avatar"]

            user_profile.save()

            return render_toast_message_for_api(
                "Information", "Updated successfully", "success"
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Profile update error: {str(e)}", exc_info=True)
            return render_toast_message_for_api(
                "Error", "An error occurred while updating profile", "error"
            )