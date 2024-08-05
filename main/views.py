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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson_form'] = LessonForm()
        context['lessons'] = self.object.lesson_set.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'save_course' in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        elif 'save_lesson' in request.POST:
            lesson_id = request.POST.get('lesson_id')
            lesson = get_object_or_404(Lesson, id=lesson_id)
            lesson_form = LessonForm(request.POST, instance=lesson)
            if lesson_form.is_valid():
                lesson_form.save()
                return redirect('course-edit', pk=self.object.pk)
            else:
                return self.form_invalid(lesson_form)


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
    if request.method == 'POST':
        course_form = CourseForm(request.POST)
        if course_form.is_valid():
            course_form.save()
            return redirect('teacher-dashboard')
    else:
        course_form = CourseForm()
    return render(request, 'main/teachers_dashboard.html', {
        'courses': courses,
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
