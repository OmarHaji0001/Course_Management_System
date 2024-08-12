# views.py
from audioop import reverse

from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.decorators import method_decorator
from .forms import SignUpForm, CourseForm, LessonForm, FeedbackForm, CategoryForm
from .models import Course, Lesson, Enrollment, Completion, Feedback, Category, Tag
from django.contrib import messages
from datetime import datetime


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

    def form_valid(self, form):
        course = form.save(commit=False)
        course.cover_image = self.request.FILES.get('cover_image')
        course.save()

        # Handle tags
        tags_input = form.cleaned_data['tags']
        if tags_input:
            tags_list = [tag.strip() for tag in tags_input.split(',')]
            for tag_name in tags_list:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                course.tags.add(tag)

        return super().form_valid(form)


class CourseDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'main/course_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        user = self.request.user
        now = datetime.now()

        # Add a flag to each lesson indicating if it's open
        lessons = []
        for lesson in course.lesson_set.all():
            lesson.is_open = lesson.open_date < now.date() or (
                lesson.open_date == now.date() and lesson.open_time <= now.time())
            lessons.append(lesson)

        # Calculate the number of completed lessons
        completed_lessons = Completion.objects.filter(student=user, lesson__course=course).count()
        total_lessons = len(lessons)

        # Calculate progress percentage
        if total_lessons > 0:
            progress = (completed_lessons / total_lessons) * 100
        else:
            progress = 0

        context['course'] = course
        context['lessons'] = lessons
        context['progress'] = progress  # Add progress to the context
        return context


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/edit_course.html'
    success_url = reverse_lazy('teacher-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()  # Pass categories to the template
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            response = self.form_valid(form)

            # Handle tags
            tags_input = form.cleaned_data.get('tags', '')
            if tags_input:
                tags_list = [tag.strip() for tag in tags_input.split(',')]
                self.object.tags.clear()  # Clear existing tags
                for tag_name in tags_list:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    self.object.tags.add(tag)

            return response
        else:
            return self.form_invalid(form)


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')

@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class EditLessonsView(LoginRequiredMixin, TemplateView):
    template_name = 'main/edit_lesson.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        context['course'] = course
        context['lessons'] = course.lesson_set.all()
        return context

    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        lessons = course.lesson_set.all()

        for lesson in lessons:
            lesson.name = request.POST.get(f'name_{lesson.id}')
            lesson.description = request.POST.get(f'description_{lesson.id}')
            lesson.open_date = request.POST.get(f'open_date_{lesson.id}')
            lesson.open_time = request.POST.get(f'open_time_{lesson.id}')
            lesson.save()

        return redirect('teacher-dashboard')


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

    total_lessons = course.lesson_set.count()
    completed_lessons = completions.count()
    progress_percentage = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

    return render(request, 'main/teacher_student_progress.html', {
        'course': course,
        'student': student,
        'completions': completions,
        'feedbacks': feedbacks,
        'progress_percentage': progress_percentage,
    })


@login_required
def teacher_dashboard(request):
    if request.method == 'POST':
        if 'category_name' in request.POST:
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                return redirect(reverse('teacher-dashboard'))
            course_form = CourseForm()  # Ensure course_form is initialized if category is added
        else:
            course_form = CourseForm(request.POST, request.FILES)
            if course_form.is_valid():
                course_form.save()
                return redirect('teacher-dashboard')
            category_form = CategoryForm()  # Ensure category_form is initialized if course is created
    else:
        course_form = CourseForm()
        category_form = CategoryForm()

    categories = Category.objects.all()
    courses = Course.objects.all()
    return render(request, 'main/teachers_dashboard.html', {
        'course_form': course_form,
        'category_form': category_form,
        'categories': categories,
        'courses': courses
    })


@login_required
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        category_description = request.POST.get('category_description')
        category = Category.objects.create(name=category_name, description=category_description)
        return JsonResponse({'success': True, 'category_id': category.id, 'category_name': category.name})
    return JsonResponse({'success': False, 'errors': 'Invalid request'}, status=400)


@user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor')
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        return redirect('teacher-dashboard')
    return render(request, 'main/teachers_dashboard.html')


class HomeView(TemplateView):
    template_name = 'main/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filter courses that are open for registration and order them by creation date
        context['new_courses'] = Course.objects.filter(open_for_registration=True).order_by('-created_at')[:8]
        return context


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
        user = self.request.user
        filter_type = self.request.GET.get('filter', '')

        if filter_type == 'enrolled':
            enrolled_courses = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
            courses = Course.objects.filter(id__in=enrolled_courses)
        else:
            courses = Course.objects.all()

        for course in courses:
            course.is_enrolled = Enrollment.objects.filter(user=user, course=course).exists()

        context['courses'] = courses
        context['filter'] = filter_type
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
