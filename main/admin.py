from django.contrib import admin
from .models import Profile, Course, Lesson, Enrollment, Completion, Feedback, Category, Tag, Quiz, Question, Answer, \
    StudentQuiz, StudentAnswer


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Feedback)
admin.site.register(Enrollment)
admin.site.register(Completion)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(StudentQuiz)
admin.site.register(StudentAnswer)
