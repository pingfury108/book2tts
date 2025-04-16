# Generated by Django 5.1.2 on 2025-04-16 18:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workbench', '0006_merge_0005_audiosegment_published_assign_to_superuser'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='audiosegment',
            name='uid',
        ),
        migrations.RemoveField(
            model_name='books',
            name='uid',
        ),
        migrations.AddField(
            model_name='audiosegment',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='audio_segments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='books',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='books', to=settings.AUTH_USER_MODEL),
        ),
    ]
