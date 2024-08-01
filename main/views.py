from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .forms import SignUpForm


class HomeView(TemplateView):
    template_name = 'main/home.html'


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('home')
    template_name = 'main/register.html'


class LoginView(AuthLoginView):
    template_name = 'main/login.html'
    success_url = reverse_lazy('home')  # Update if you have a different success URL


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('home')
