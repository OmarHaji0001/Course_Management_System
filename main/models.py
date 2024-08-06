from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    open_for_registration = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=date.today)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user.username} enrolled in {self.course.name}'


class Profile(models.Model):
    USER_ROLES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='student')

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'
