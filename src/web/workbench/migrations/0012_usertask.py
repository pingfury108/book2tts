# Generated by Django 5.1.2 on 2025-06-03 10:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workbench', '0011_audiosegment_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('task_type', models.CharField(default='audio_synthesis', max_length=50)),
                ('title', models.CharField(blank=True, max_length=500)),
                ('status', models.CharField(choices=[('pending', '等待中'), ('processing', '处理中'), ('success', '已完成'), ('failure', '失败'), ('revoked', '已取消')], default='pending', max_length=20)),
                ('progress_message', models.TextField(blank=True)),
                ('result_data', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('book', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='workbench.books')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
