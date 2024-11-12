from django import forms

from .models import Books


class UploadFileForm(forms.ModelForm):

    class Meta:
        model = Books
        fields = ('file', )
