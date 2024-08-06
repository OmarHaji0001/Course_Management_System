from django.urls import path
from .views import HomeView, SignUpView, LoginView, LogoutView, DashboardView, admin_dashboard, teacher_dashboard, CourseDetailView, enroll_in_course
from .views import CourseCreateView, CourseUpdateView, LessonCreateView, delete_course

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', SignUpView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    path('teacher-dashboard/', teacher_dashboard, name='teacher-dashboard'),
    path('enroll/<int:course_id>/', enroll_in_course, name='enroll-in-course'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('courses/new/', CourseCreateView.as_view(), name='course-create'),
    path('courses/<int:pk>/edit/', CourseUpdateView.as_view(), name='course-edit'),
    path('courses/<int:pk>/delete/', delete_course, name='course-delete'),
    path('courses/<int:course_id>/lessons/new/', LessonCreateView.as_view(), name='lesson-create'),
]
