from django.urls import path
from . import views
from .views import (
    HomeView, SignUpView, LoginView, LogoutView, DashboardView,
    admin_dashboard, teacher_dashboard, CourseDetailView, enroll_in_course,
    CourseCreateView, CourseUpdateView, LessonCreateView, LessonDetailView,
    delete_course, teacher_student_progress,
    mark_lesson_complete, submit_feedback, add_category, EditLessonsView, AllCoursesView, LessonDeleteView,
    CourseCardDetailView, manage_account
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('all-courses/', AllCoursesView.as_view(), name='all_courses'),
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
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/complete/', mark_lesson_complete, name='mark-lesson-complete'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/delete/', LessonDeleteView.as_view(), name='delete-lesson'),
    path('courses/<int:course_id>/feedback/', submit_feedback, name='submit-feedback'),
    path('course/<int:course_id>/students/', views.teacher_course_students, name='teacher_course_students'),
    path('course/<int:course_id>/students/<int:student_id>/progress/', views.teacher_student_progress,
         name='teacher_student_progress'),
    path('add-category/', add_category, name='add-category'),
    path('courses/<int:course_id>/lessons/edit/', EditLessonsView.as_view(), name='edit-lesson'),
    path('course_card_details/<int:pk>/', CourseCardDetailView.as_view(), name='course-card-detail'),
    path('manage-account/', manage_account, name='manage-account'),
    path('manage-quizzes/', views.manage_quizzes, name='manage-quizzes'),
    path('create-quiz/', views.create_quiz, name='create-quiz'),
]
