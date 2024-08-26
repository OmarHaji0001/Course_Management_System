# views.py
from audioop import reverse

import pandas as pd
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponseNotAllowed, JsonResponse, HttpResponse
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.decorators import method_decorator
from .forms import SignUpForm, CourseForm, LessonForm, FeedbackForm, CategoryForm, UserUpdateForm, ProfileUpdateForm, \
    CustomLoginForm
from .models import Course, Lesson, Enrollment, Completion, Feedback, Category, Tag, Quiz, Question, Answer, \
    StudentAnswer, StudentQuiz

from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone


@login_required
def attempt_quiz(request, course_id, question_index=0):
    course = get_object_or_404(Course, id=course_id)
    quiz = Quiz.objects.filter(course=course).last()

    if not quiz:
        return HttpResponse("No quiz available for this course.")

    # Get the current question
    questions = quiz.questions.all()
    if question_index >= len(questions):
        return redirect('submit-quiz', course_id=course_id)

    question = questions[question_index]

    if request.method == 'POST':
        selected_answer_id = request.POST.get('answer')
        selected_answer = get_object_or_404(Answer, id=selected_answer_id)

        # Find or create the StudentQuiz record
        student_quiz, _ = StudentQuiz.objects.get_or_create(
            student=request.user,
            quiz=quiz
        )

        # Store the user's answer immediately
        StudentAnswer.objects.create(
            student_quiz=student_quiz,
            question=question,
            selected_answer=selected_answer
        )

        # Move to the next question or finish the quiz
        if question_index + 1 < len(questions):
            return redirect('attempt-quiz', course_id=course_id, question_index=question_index + 1)
        else:
            return redirect('submit-quiz', course_id=course_id)

    return render(request, 'main/attempt_quiz.html', {
        'quiz': quiz,
        'question': question,
        'question_index': question_index,
        'total_questions': len(questions),
    })


@login_required
def submit_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    quiz = Quiz.objects.filter(course=course).last()

    if not quiz:
        return HttpResponse("No quiz available for this course.")

    # Find the StudentQuiz record
    student_quiz = StudentQuiz.objects.filter(student=request.user, quiz=quiz).first()

    if not student_quiz:
        return HttpResponse("You haven't attempted this quiz.")

    # Calculate the total possible score
    total_possible_score = sum(question.mark for question in quiz.questions.all())

    # Calculate the student's score
    total_score = 0
    correct_answers = 0
    student_answer_list = StudentAnswer.objects.filter(student_quiz=student_quiz)

    for student_answer in student_answer_list:
        if student_answer.selected_answer.is_correct:
            correct_answers += 1
            total_score += student_answer.question.mark

    # Calculate the percentage score
    percentage_score = (total_score / total_possible_score) * 100 if total_possible_score > 0 else 0

    # Update the student's score and status
    student_quiz.score = percentage_score
    student_quiz.status = 'passed' if percentage_score >= quiz.success_threshold else 'failed'
    student_quiz.save()

    return redirect('quiz-result', course_id=course_id, student_quiz_id=student_quiz.id)


@login_required
def quiz_result(request, course_id, student_quiz_id):  # noqa: E501
    student_quiz = get_object_or_404(StudentQuiz, id=student_quiz_id, student=request.user)
    quiz = student_quiz.quiz
    correct_count = student_quiz.answers.filter(selected_answer__is_correct=True).count()

    context = {
        'quiz': quiz,
        'student_quiz': student_quiz,
        'correct_count': correct_count,  # Pass the correct count to the template
    }

    return render(request, 'main/quiz_result.html', context)


@login_required
def manage_quizzes(request):
    teacher = request.user
    # Fetch courses for the logged-in instructor
    courses = Course.objects.filter(teacher=teacher)

    # Annotate courses with a flag indicating if they already have a quiz
    courses = courses.annotate(
        has_quiz=Exists(Quiz.objects.filter(course=OuterRef('pk')))
    )

    # Fetch quizzes for the logged-in instructor's courses
    quizzes = Quiz.objects.filter(course__teacher=teacher)

    return render(request, 'main/manage_quizzes.html', {
        'courses': courses,
        'quizzes': quizzes,
    })


@login_required
def create_quiz(request):
    if request.method == 'POST':
        course_id = request.POST.get('course')
        quiz_name = request.POST.get('quiz_name')
        excel_file = request.FILES.get('excel_file')
        success_threshold = request.POST.get('success_threshold')  # Capture the threshold
        duration_minutes = request.POST.get('duration_minutes')

        course = get_object_or_404(Course, id=course_id)

        # Check if the course already has a quiz
        if Quiz.objects.filter(course=course).exists():
            messages.error(
                request,
                f"A quiz already exists for the course {course.name}. "
                "Please delete it before creating a new one."
            )
            return redirect('manage-quizzes')

        quiz = Quiz.objects.create(
            name=quiz_name,
            course=course,
            success_threshold=success_threshold,
            duration_minutes=duration_minutes,
            excel_file=excel_file
        )

        # Parse the Excel file
        if excel_file:
            df = pd.read_excel(excel_file)

            # Ensure the correct column names are used
            if 'Question Text' not in df.columns or 'Question Type' not in df.columns:
                messages.error(request, "The uploaded Excel file does not have the required columns.")
                return redirect('manage-quizzes')

            for _, row in df.iterrows():
                question_text = row['Question Text']
                question_type = row['Question Type']
                correct_answer = str(row['Correct Answer']).strip().lower()
                options = [row.get('Option 1'), row.get('Option 2'), row.get('Option 3'), row.get('Option 4')]
                mark = row.get('Mark', 1)  # Default mark to 1 if not provided

                # Create Question
                question = Question.objects.create(
                    quiz=quiz,
                    text=question_text,
                    question_type=question_type,
                    mark=mark
                )

                # Create Answers
                if question_type.strip().lower() == "true/false":
                    for option in ["true", "false"]:
                        is_correct = (option == correct_answer)
                        Answer.objects.create(question=question, text=option.upper(), is_correct=is_correct)
                else:  # Assume Multiple Choice
                    for option in options:
                        if pd.notna(option):  # Ensure there's no NaN in options
                            is_correct = (str(option).strip().lower() == correct_answer)
                            Answer.objects.create(question=question, text=option, is_correct=is_correct)

        return redirect('manage-quizzes')


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        if 'delete_quiz' in request.POST:
            quiz.delete()
            return redirect('manage-quizzes')

        # Update quiz name, course, and success threshold
        quiz_name = request.POST.get('quiz_name')
        course_id = request.POST.get('course')
        success_threshold = request.POST.get('success_threshold')

        quiz.name = quiz_name
        quiz.course_id = course_id
        quiz.success_threshold = success_threshold  # Update success threshold

        quiz.save()

        return redirect('manage-quizzes')

    courses = Course.objects.filter(teacher=request.user)

    return render(request, 'main/edit_quiz.html', {
        'quiz': quiz,
        'courses': courses,
    })


@login_required
def quiz_students_progress(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student_quizzes = StudentQuiz.objects.filter(quiz=quiz)

    paginator = Paginator(student_quizzes, 6)  # Show 6 students per page
    page_number = request.GET.get('page')
    student_quizzes_page = paginator.get_page(page_number)

    return render(request, 'main/quiz_students_progress.html', {
        'quiz': quiz,
        'student_quizzes': student_quizzes_page,
    })


def student_answers(request, student_quiz_id):
    student_quiz = get_object_or_404(StudentQuiz, id=student_quiz_id)
    student_answer_list = student_quiz.answers.select_related('question', 'selected_answer').all()

    # Create a list of dictionaries with the student answer, the question, and the correct answer
    answer_data = []
    for student_answer in student_answer_list:
        correct_answer = student_answer.question.answers.get(is_correct=True)
        answer_data.append({
            'question': student_answer.question,
            'selected_answer': student_answer.selected_answer,
            'correct_answer': correct_answer,
        })

    paginator = Paginator(answer_data, 3)  # Show 3 answers per page
    page_number = request.GET.get('page')
    paginated_answer_data = paginator.get_page(page_number)

    context = {
        'student_quiz': student_quiz,
        'paginated_answer_data': paginated_answer_data,
    }

    return render(request, 'main/student_answers.html', context)


@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully.')
    return redirect('manage-quizzes')


@login_required
def manage_account(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your account has been updated successfully.')
            # Redirect based on user role
            if request.user.profile.role == 'admin':
                return redirect('admin-dashboard')
            elif request.user.profile.role == 'instructor':
                return redirect('teacher-dashboard')
            else:
                return redirect('dashboard')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'main/manage_account.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


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

        # Check if the student has completed the quiz
        if context['is_last_lesson']:
            context['has_completed_quiz'] = StudentQuiz.objects.filter(student=self.request.user,
                                                                       quiz__course=course).exists()
        else:
            context['has_completed_quiz'] = False

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
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    students = course.enrolled_students.all()
    student_progress = []

    for student in students:
        lessons_count = course.lesson_set.count()
        completed_lessons = Completion.objects.filter(student=student, lesson__course=course).count()
        progress_percentage = (completed_lessons / lessons_count) * 100 if lessons_count > 0 else 0
        student_progress.append({
            'student': student,
            'progress': progress_percentage
        })

    paginator = Paginator(student_progress, 6)  # Show 6 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/teacher_course_students.html', {
        'course': course,
        'students': page_obj,
    })


@login_required
def teacher_student_progress(request, course_id, student_id):
    course = get_object_or_404(Course, pk=course_id)
    student = get_object_or_404(User, pk=student_id)

    # Fetch the student's course progress
    total_lessons = course.lesson_set.count()
    completed_lessons = Completion.objects.filter(student=student, lesson__course=course).count()
    progress_percentage = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0

    # Fetch the student's feedback for this course
    feedbacks = Feedback.objects.filter(student=student, course=course)

    # Fetch the student's completion activities
    completions = Completion.objects.filter(
        student=student, lesson__course=course
    ).select_related(
        'lesson', 'lesson__course'
    ).order_by('-id')

    return render(request, 'main/teacher_student_progress.html', {
        'course': course,
        'student': student,
        'progress_percentage': progress_percentage,
        'feedbacks': feedbacks,
        'completions': completions,
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

    # Fetch recent completions for the teacher's courses
    activities = Completion.objects.filter(lesson__course__teacher=teacher).select_related('lesson', 'student',
                                                                                           'lesson__course').order_by(
        '-id')[:10]

    # Prepare the data for the template
    activities_data = [{
        'student_name': activity.student.username,
        'lesson_name': activity.lesson.name,
        'course_name': activity.lesson.course.name
    } for activity in activities]

    return render(request, 'main/teachers_dashboard.html', {
        'course_form': course_form,
        'category_form': category_form,
        'categories': categories,
        'courses': courses,  # Pass the filtered courses to the template
        'activities': activities_data,  # Pass the activity feed data to the template
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

    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('search', '')

        if search_query:
            # Redirect to the All Courses page with the search query as a parameter
            return redirect(f'/all-courses/?search={search_query}')

        return super().get(request, *args, **kwargs)

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
    form_class = CustomLoginForm

    def get_success_url(self):
        # Check if there is a 'next' parameter in the URL
        next_url = self.request.GET.get('next')

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
