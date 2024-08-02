# CMS/urls.py
from django.contrib import admin
from django.urls import path
from main.views import HomeView, SignUpView, LoginView, LogoutView, DashboardView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', SignUpView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
]
