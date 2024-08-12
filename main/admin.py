from django.contrib import admin
from .models import Profile, Course, Lesson, Enrollment, Completion, Feedback, Category, Tag


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
