# views.py
from audioop import reverse
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.decorators import method_decorator
from .forms import SignUpForm, CourseForm, LessonForm, FeedbackForm, CategoryForm
from .models import Course, Lesson, Enrollment, Completion, Feedback, Category, Tag
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone


class CourseCardDetailView(DetailView):
    model = Course
    template_name = 'main/course_card_details.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_enrolled'] = False
        if self.request.user.is_authenticated:
            context['is_enrolled'] = self.object.enrolled_students.filter(id=self.request.user.id).exists()
        return context


@login_required
def enroll_in_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check if the user is already enrolled
    if not Enrollment.objects.filter(course=course, user=request.user).exists():
        # Create the Enrollment entry
        Enrollment.objects.create(course=course, user=request.user)

        # Add the user to the enrolled_students field in the Course model
        course.enrolled_students.add(request.user)

        messages.success(request, f'You have successfully enrolled in {course.name}.')
    else:
        messages.info(request, f'You are already enrolled in {course.name}.')

    return redirect('course-card-detail', pk=course_id)


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'main/create_course.html'
    success_url = reverse_lazy('teacher-dashboard')

    def form_valid(self, form):
        # Save the course
        course = form.save(commit=False)
        course.teacher = self.request.user  # Assign the logged-in user as the course creator
        course.cover_image = self.request.FILES.get('cover_image')
        course.start_date = form.cleaned_data['start_date']  # Handle the start date
        course.save()

        # Handle tags
        tags_input = form.cleaned_data.get('tags')
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

    def get_initial(self):
        initial = super().get_initial()
        course = self.get_object()
        initial['tags'] = ', '.join([tag.name for tag in course.tags.all()])
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def form_valid(self, form):
        # Handle tags
        tags_input = form.cleaned_data.get('tags', '')
        if tags_input:
            tags_list = [tag.strip() for tag in tags_input.split(',')]
            form.instance.tags.clear()  # Clear existing tags
            for tag_name in tags_list:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                form.instance.tags.add(tag)

        # Save the course with the updated information
        return super().form_valid(form)


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = 'main/teachers_dashboard.html'
    success_url = reverse_lazy('teacher-dashboard')


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.profile.role == 'instructor'), name='dispatch')
class EditLessonsView(TemplateView):
    template_name = 'main/edit_lesson.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        lessons = course.lesson_set.all()
        lesson_forms = [LessonForm(instance=lesson, prefix=str(lesson.id)) for lesson in lessons]
        context['course'] = course
        context['lesson_forms'] = lesson_forms
        return context

    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        lessons = course.lesson_set.all()
        lesson_forms = [LessonForm(request.POST, instance=lesson, prefix=str(lesson.id)) for lesson in lessons]

        if all([form.is_valid() for form in lesson_forms]):
            for form in lesson_forms:
                form.save()
            return redirect('teacher-dashboard')

        context = self.get_context_data()
        context['lesson_forms'] = lesson_forms
        return self.render_to_response(context)


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.profile.role == 'instructor'), name='dispatch')
class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'main/create_lesson.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        context['course'] = course  # Pass the course object to the template
        return context

    def form_valid(self, form):
        lesson = form.save(commit=False)
        lesson.course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        lesson.save()
        return redirect('edit-lesson', course_id=lesson.course.id)

    def get_success_url(self):
        return reverse_lazy('edit-lesson', kwargs={'course_id': self.object.course.id})


class LessonDeleteView(LoginRequiredMixin, DeleteView):
    model = Lesson
    pk_url_kwarg = 'lesson_id'
    template_name = 'main/teachers_dashboard.html'

    def get_success_url(self):
        return reverse_lazy('edit-lesson', kwargs={'course_id': self.kwargs['course_id']})

    def get_object(self, queryset=None):
        return get_object_or_404(Lesson, pk=self.kwargs['lesson_id'])


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
    teacher = request.user
    courses = Course.objects.filter(teacher=teacher)  # Only fetch courses created by the logged-in teacher

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
                # Assign the logged-in teacher as the creator of the course
                course = course_form.save(commit=False)
                course.teacher = teacher
                course.save()
                return redirect('teacher-dashboard')
            category_form = CategoryForm()  # Ensure category_form is initialized if course is created
    else:
        course_form = CourseForm()
        category_form = CategoryForm()

    categories = Category.objects.all()

    return render(request, 'main/teachers_dashboard.html', {
        'course_form': course_form,
        'category_form': category_form,
        'categories': categories,
        'courses': courses  # Pass the filtered courses to the template
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
        context['categories'] = Category.objects.all()
        context['new_courses'] = Course.objects.filter(open_for_registration=True).order_by('-created_at')[:9]
        context['featured_courses'] = Course.objects.annotate(enrollment_count=Count('enrollment')).order_by(
            '-enrollment_count')[:9]
        now = timezone.now().date()
        one_week_later = now + timedelta(weeks=1)
        context['starting_soon_courses'] = Course.objects.filter(
            start_date__range=[now, one_week_later]
        ).order_by('start_date')[:9]
        return context


class AllCoursesView(TemplateView):
    template_name = 'main/all_courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = Course.objects.filter(open_for_registration=True).order_by('-created_at')

        subject_area = self.request.GET.get('subject_area')
        price = self.request.GET.get('price')
        start_date = self.request.GET.get('start_date')
        duration = self.request.GET.get('duration')
        modality = self.request.GET.get('modality')
        search_query = self.request.GET.get('search')

        if search_query:
            courses = courses.filter(name__icontains=search_query)

        if subject_area:
            courses = courses.filter(category_id=subject_area)
            context['selected_subject_area'] = Category.objects.get(id=subject_area).name

        if price:
            if price == 'free':
                courses = courses.filter(price=0)
            elif price == 'paid':
                courses = courses.exclude(price=0)

        if start_date:
            now = timezone.now()
            if start_date == '1_week':
                courses = courses.filter(start_date__lte=now + timedelta(weeks=1))
            elif start_date == '1_month':
                courses = courses.filter(start_date__lte=now + timedelta(weeks=4))
            elif start_date == '3_months':
                courses = courses.filter(start_date__lte=now + timedelta(weeks=12))
            elif start_date == '6_months':
                courses = courses.filter(start_date__lte=now + timedelta(weeks=26))
            elif start_date == '1_year':
                courses = courses.filter(start_date__lte=now + timedelta(weeks=52))

        if duration:
            if duration == '0_1':
                courses = courses.filter(duration_weeks__lte=1)
            elif duration == '1_3':
                courses = courses.filter(duration_weeks__gt=1, duration_weeks__lte=3)
            elif duration == '3_6':
                courses = courses.filter(duration_weeks__gt=3, duration_weeks__lte=6)
            elif duration == '6_9':
                courses = courses.filter(duration_weeks__gt=6, duration_weeks__lte=9)
            elif duration == '9_12':
                courses = courses.filter(duration_weeks__gt=9, duration_weeks__lte=12)
            elif duration == '12_plus':
                courses = courses.filter(duration_weeks__gt=12)

        if modality:
            courses = courses.filter(modality=modality)

        # Pagination
        paginator = Paginator(courses, 12)  # Show 12 courses per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['page_obj'] = page_obj
        context['courses'] = page_obj.object_list
        context['subject_areas'] = Category.objects.all()

        # Collecting filters for display
        context['filters'] = {
            'subject_area': context.get('selected_subject_area'),
            'price': price,
            'start_date': start_date,
            'duration': duration,
            'modality': modality,
            'search_query': search_query,
            'total_results': courses.count(),
        }
        return context


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'main/register.html'


class LoginView(AuthLoginView):
    template_name = 'main/login.html'

    def get_success_url(self):
        # Check if there is a 'next' parameter in the URL
        next_url = self.request.GET.get('next')
        print(self.request.GET)

        if next_url:
            return next_url
        elif self.request.user.profile.role == 'admin':
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

        # Get the enrolled courses for the logged-in user
        enrolled_courses = Course.objects.filter(enrollment__user=user)

        # Calculate progress and end date for each course
        for course in enrolled_courses:
            total_lessons = course.lesson_set.count()
            completed_lessons = Completion.objects.filter(student=user, lesson__course=course).count()
            course.progress = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

            # Calculate the end date
            if course.start_date and course.duration_weeks:
                course.end_date = course.start_date + timedelta(weeks=course.duration_weeks)
            else:
                course.end_date = None  # Handle cases where the start date or duration is missing

        context['enrolled_courses'] = enrolled_courses

        # Fetch the featured courses (limit to 5)
        context['featured_courses'] = Course.objects.annotate(enrollment_count=Count('enrollment')).order_by(
            '-enrollment_count')[:5]

        return context


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
