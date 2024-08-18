from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import modelformset_factory

from .models import Course, Lesson, Feedback, Category


class CourseForm(forms.ModelForm):
    tags = forms.CharField(required=False, help_text="Enter tags separated by commas")

    class Meta:
        model = Course
        fields = ['name', 'description', 'cover_image', 'category', 'price', 'duration_weeks', 'modality',
                  'open_for_registration', 'start_date']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']


class LessonForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Lesson
        fields = ['name', 'description', 'open_date', 'open_time']
        widgets = {
            'open_date': forms.DateInput(attrs={'type': 'date'}),
            'open_time': forms.TimeInput(attrs={'type': 'time'}),
        }


LessonFormSet = modelformset_factory(Lesson, form=LessonForm, extra=0)


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['comment']


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    email = forms.EmailField(max_length=254, help_text='Enter a valid email address')
    address_line1 = forms.CharField(max_length=255, required=True, help_text='Required')
    address_line2 = forms.CharField(max_length=255, required=False, help_text='Optional')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # The profile is created automatically by the signal, so no need to create it manually here
            user.profile.address_line1 = self.cleaned_data['address_line1']
            user.profile.address_line2 = self.cleaned_data['address_line2']
            user.profile.save()  # Save the profile with the additional fields
        return user
