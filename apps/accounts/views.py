"""
Accounts & Authentication Feature Views
=======================================
Handles user onboarding, authentication, session lifecycle, and profile management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from study_companion.models import UserProfile


def home_view(request):
    """SignAI Pro landing page."""
    return render(request, 'home.html')


def about_view(request):
    """About SignAI Pro page."""
    return render(request, 'about.html')


def contact_view(request):
    """Contact page."""
    return render(request, 'contact.html')


def signup_view(request):
    """User registration view."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('animation')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login view."""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('animation')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    logout(request)
    return redirect("home")


@login_required(login_url="login")
def profile_view(request):
    """User profile details view and update form."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_info')

        if action == 'update_info':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()

            errors = []
            if not username:
                errors.append("Username cannot be empty.")
            elif username != user.username and User.objects.filter(username=username).exclude(pk=user.pk).exists():
                errors.append("This username is already taken. Please choose another.")

            if email and email != user.email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
                errors.append("This email is already registered to another account.")

            if errors:
                for err in errors:
                    messages.error(request, err)
            else:
                user.username = username
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                messages.success(request, "Your profile details have been updated successfully!")
                return redirect('profile')

        elif action == 'change_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(old_password):
                messages.error(request, "Current password is incorrect.")
            elif len(new_password) < 6:
                messages.error(request, "New password must be at least 6 characters long.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed successfully!")
                return redirect('profile')

    context = {
        'profile': profile,
        'user': user,
    }
    return render(request, 'profile.html', context)
