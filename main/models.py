from django.db import models
from django.contrib.auth.models import User
from datetime import date, time
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    slug = models.SlugField(unique=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    MODALITY_CHOICES = [
        ('online', 'Online'),
        ('blended', 'Blended'),
        ('in_person', 'In-Person'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    open_for_registration = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    tags = models.ManyToManyField(Tag, related_name='courses')
    modality = models.CharField(max_length=10, choices=MODALITY_CHOICES, default='online')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_weeks = models.IntegerField(default=0)

    def is_free(self):
        return self.price == 0.00

    def __str__(self):
        return self.name


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    open_date = models.DateField(default=date.today)
    open_time = models.TimeField(default=time(0, 0))

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


class Completion(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.student.username} completed {self.lesson.name}'


class Feedback(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return f'{self.student.username} feedback on {self.course.name}'


class Profile(models.Model):
    USER_ROLES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='student')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'
