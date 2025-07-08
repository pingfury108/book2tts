# Generated manually

from django.db import migrations
import hashlib
import os


def calculate_existing_md5(apps, schema_editor):
    """为现有书籍计算MD5哈希值"""
    Books = apps.get_model('workbench', 'Books')
    
    for book in Books.objects.filter(md5_hash=''):
        try:
            if book.file and os.path.exists(book.file.path):
                # 计算文件MD5
                hash_md5 = hashlib.md5()
                with open(book.file.path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                
                book.md5_hash = hash_md5.hexdigest()
                book.save(update_fields=['md5_hash'])
                print(f"Updated MD5 for book: {book.name} -> {book.md5_hash}")
            else:
                print(f"File not found for book: {book.name}")
        except Exception as e:
            print(f"Error calculating MD5 for book {book.name}: {str(e)}")


def reverse_md5_calculation(apps, schema_editor):
    """回滚操作：清空MD5字段"""
    Books = apps.get_model('workbench', 'Books')
    Books.objects.update(md5_hash='')


class Migration(migrations.Migration):

    dependencies = [
        ('workbench', '0013_add_md5_hash_to_books'),
    ]

    operations = [
        migrations.RunPython(
            calculate_existing_md5,
            reverse_md5_calculation,
        ),
    ] 