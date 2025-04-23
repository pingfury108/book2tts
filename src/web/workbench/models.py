from pathlib import Path
from django.utils import timezone
from django.db import models
from django.conf import settings
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class Books(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='books', null=True, blank=True)
    name = models.TextField(default="")
    file_type = models.TextField(default="")
    file = models.FileField(upload_to='books/%Y/%m/%d/')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name.__str__()

    def setkw(self, user):
        file = Path(self.file.path)
        self.user = user
        self.name = file.stem
        self.file_type = file.suffix
        return

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)


class AudioSegment(models.Model):
    book = models.ForeignKey(Books, on_delete=models.CASCADE, related_name='audio_segments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audio_segments', null=True)
    title = models.CharField(max_length=255)
    text = models.TextField()
    book_page = models.CharField(max_length=255)
    file = models.FileField(upload_to='audio_segments/%Y/%m/%d/')
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.title} - {self.book.name}"
        
    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)


# Add UserProfile model
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    rss_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# Signal to create/update UserProfile whenever a User object is saved
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    try:
        # 尝试获取用户的profile
        profile = instance.profile
    except UserProfile.DoesNotExist:
        # 如果用户没有profile，创建一个
        profile = UserProfile.objects.create(user=instance)
    profile.save()
