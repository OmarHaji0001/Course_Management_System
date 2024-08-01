from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Course(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, default=1)  # Replace 1 with the actual course ID
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, default=1)  # Replace 1 with the actual course ID
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)  # Replace 1 with the actual user ID
    date_enrolled = models.DateField(default=date.today)  # Use default=date.today

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user.username} enrolled in {self.course.name}'
