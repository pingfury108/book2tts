# Generated by Django 5.1.2 on 2024-11-12 02:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workbench", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="books",
            name="uid",
            field=models.TextField(default="admin"),
        ),
    ]
