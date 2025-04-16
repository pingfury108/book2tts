from pathlib import Path

from django.db import models
from django.conf import settings

# Create your models here.


class Books(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='books')
    name = models.TextField(default="")
    file_type = models.TextField(default="")
    file = models.FileField(upload_to='books/%Y/%m/%d/')

    def __str__(self) -> str:
        return self.name.__str__()

    def setkw(self, user):
        file = Path(self.file.path)
        self.user = user
        self.name = file.stem
        self.file_type = file.suffix
        return


class AudioSegment(models.Model):
    book = models.ForeignKey(Books, on_delete=models.CASCADE, related_name='audio_segments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audio_segments')
    title = models.CharField(max_length=255)
    text = models.TextField()
    book_page = models.CharField(max_length=255)
    file = models.FileField(upload_to='audio_segments/%Y/%m/%d/')
    published = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.title} - {self.book.name}"
