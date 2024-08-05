from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from .forms import SignUpForm, CourseForm, LessonForm
from .models import Course, Lesson

@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/edit_course.html'
    success_url = reverse_lazy('teacher-dashboard')

@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

def teacher_dashboard(request):
    courses = Course.objects.all()
    lessons = Lesson.objects.all()
    if request.method == 'POST':
        course_form = CourseForm(request.POST)
        if course_form.is_valid():
            course_form.save()
            return redirect('teacher-dashboard')
    else:
        course_form = CourseForm()
    return render(request, 'main/teachers_dashboard.html', {
        'courses': courses,
        'lessons': lessons,
        'course_form': course_form
    })

@user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor')
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        return redirect('teacher-dashboard')
    return render(request, 'main/teachers_dashboard.html', {'course': course})

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
