from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .forms import SignUpForm
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test


class HomeView(TemplateView):
    template_name = 'main/home.html'


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'main/register.html'


class LoginView(AuthLoginView):
    template_name = 'main/login.html'

    def get_success_url(self):
        if self.request.user.profile.role == 'admin':
            return reverse_lazy('admin-dashboard')
        elif self.request.user.profile.role == 'instructor':
            return reverse_lazy('teacher-dashboard')
        else:
            return reverse_lazy('dashboard')


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('home')


class DashboardView(TemplateView):
    template_name = 'main/dashboard.html'


def is_admin(user):
    return user.is_authenticated and user.profile.role == 'admin'


@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, 'main/admin_dashboard.html')


def is_teacher(user):
    return user.is_authenticated and user.profile.role == 'instructor'


@user_passes_test(is_teacher)
def teacher_dashboard(request):
    return render(request, 'main/teachers_dashboard.html')
