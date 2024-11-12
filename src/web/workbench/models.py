from django.db import models

# Create your models here.


class Books(models.Model):
    uid = models.TextField(default="admin")
    file = models.FileField(upload_to='books/%Y/%m/%d/')
