from django.contrib import admin
from django.urls import path
from .views import HomeView, SignUpView, LoginView, LogoutView, DashboardView, admin_dashboard, teacher_dashboard
from .views import CourseCreateView, CourseUpdateView, CourseDeleteView, LessonCreateView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', SignUpView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    path('teacher-dashboard/', teacher_dashboard, name='teacher-dashboard'),
    path('courses/new/', CourseCreateView.as_view(), name='course-create'),
    path('courses/<int:pk>/edit/', CourseUpdateView.as_view(), name='course-edit'),
    path('courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='course-delete'),
    path('courses/<int:course_id>/lessons/new/', LessonCreateView.as_view(), name='lesson-create'),
    path('admin/', admin.site.urls),
]
