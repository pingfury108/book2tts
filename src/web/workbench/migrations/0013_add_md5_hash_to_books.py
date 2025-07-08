# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workbench', '0012_usertask'),
    ]

    operations = [
        migrations.AddField(
            model_name='books',
            name='md5_hash',
            field=models.CharField(blank=True, db_index=True, help_text='文件的MD5哈希值，用于检测重复文件', max_length=32),
        ),
    ] 