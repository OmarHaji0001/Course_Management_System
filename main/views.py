# views.py
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.decorators import method_decorator
from .forms import SignUpForm, CourseForm, LessonForm, FeedbackForm
from .models import Course, Lesson, Enrollment, Completion, Feedback
from django.contrib import messages
from datetime import datetime


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

    def form_valid(self, form):
        form.instance.cover_image = self.request.FILES.get('cover_image')
        return super().form_valid(form)


class CourseDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'main/course_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        now = datetime.now()

        # Add a flag to each lesson indicating if it's open
        lessons = []
        for lesson in course.lesson_set.all():
            lesson.is_open = lesson.open_date < now.date() or (
                lesson.open_date == now.date() and lesson.open_time <= now.time())
            lessons.append(lesson)

        context['course'] = course
        context['lessons'] = lessons
        return context


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


# views.py

class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'main/lesson_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object.course
        last_lesson = course.lesson_set.order_by('-open_date', '-open_time').first()
        context['is_last_lesson'] = self.object == last_lesson
        context['feedback_form'] = FeedbackForm() if context['is_last_lesson'] else None
        context['completion'] = Completion.objects.filter(student=self.request.user, lesson=self.object).exists()
        context['course_id'] = course.id  # Pass the course_id to the context
        return context


@login_required
def submit_feedback(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        feedback_form = FeedbackForm(request.POST)
        if feedback_form.is_valid():
            feedback = feedback_form.save(commit=False)
            feedback.course = course
            feedback.student = request.user
            feedback.save()
            messages.success(request, 'Feedback submitted successfully.')
    return redirect('course-detail', pk=course.id)



@login_required
def teacher_course_students(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollments = Enrollment.objects.filter(course=course)
    return render(request, 'main/teacher_course_students.html', {'course': course, 'enrollments': enrollments})


@login_required
def teacher_student_progress(request, course_id, student_id):
    course = get_object_or_404(Course, pk=course_id)
    student = get_object_or_404(User, pk=student_id)
    completions = Completion.objects.filter(student=student, lesson__course=course)
    feedbacks = Feedback.objects.filter(student=student, course=course)
    return render(request, 'main/teacher_student_progress.html', {
        'course': course,
        'student': student,
        'completions': completions,
        'feedbacks': feedbacks,
    })


def teacher_dashboard(request):
    courses = Course.objects.all()
    if request.method == 'POST':
        course_form = CourseForm(request.POST, request.FILES)
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
    return render(request, 'main/teachers_dashboard.html')


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


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.all()
        context['today'] = datetime.now().date()
        context['now'] = datetime.now().time()
        return context


@login_required
def enroll_in_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrollment, created = Enrollment.objects.get_or_create(course=course, user=request.user)
    if created:
        messages.success(request, f'You have successfully enrolled in {course.name}.')
    else:
        messages.info(request, f'You are already enrolled in {course.name}.')
    return redirect('dashboard')


@login_required
def mark_lesson_complete(request, lesson_id):
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        Completion.objects.get_or_create(student=request.user, lesson=lesson)
        messages.success(request, 'Lesson marked as complete.')
        return redirect('lesson-detail', pk=lesson_id)
    else:
        return HttpResponseNotAllowed(['POST'])


def is_admin(user):
    return user.is_authenticated and user.profile.role == 'admin'


@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, 'main/admin_dashboard.html')
