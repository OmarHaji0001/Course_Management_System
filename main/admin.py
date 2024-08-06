from django.contrib import admin
from .models import Profile, Course, Lesson, Enrollment, Feedback, Completion


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(Feedback)
admin.site.register(Completion)
