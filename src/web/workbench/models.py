from pathlib import Path

from django.db import models

# Create your models here.


class Books(models.Model):
    uid = models.TextField(default="admin")
    name = models.TextField(default="")
    file_type = models.TextField(default="")
    file = models.FileField(upload_to='books/%Y/%m/%d/')

    def __str__(self) -> str:
        return self.name.__str__()

    def setkw(self, uid):
        file = Path(self.file.path)
        self.uid = uid
        self.name = file.stem
        self.file_type = file.suffix
        return
