from django.db import migrations
from django.contrib.auth import get_user_model

def assign_data_to_superuser(apps, schema_editor):
    # Get models
    Books = apps.get_model('workbench', 'Books')
    AudioSegment = apps.get_model('workbench', 'AudioSegment')
    User = get_user_model()
    
    # Get a superuser (create one if none exists)
    superuser = None
    superusers = User.objects.filter(is_superuser=True)
    
    if superusers.exists():
        superuser = superusers.first()
    else:
        # Create a superuser if none exists
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin'
        )
        print("Created superuser 'admin' with password 'admin'")
    
    # Assign all existing Books to the superuser
    books_updated = 0
    for book in Books.objects.all():
        book.user = superuser
        book.save()
        books_updated += 1
    
    # Assign all existing AudioSegments to the superuser
    segments_updated = 0
    for segment in AudioSegment.objects.all():
        segment.user = superuser
        segment.save()
        segments_updated += 1
    
    print(f"Migration complete: Assigned {books_updated} books and {segments_updated} audio segments to superuser '{superuser.username}'")

class Migration(migrations.Migration):
    dependencies = [
        ('workbench', '0004_audiosegment'),  # Update this to make sure AudioSegment model is available
    ]
    
    operations = [
        migrations.RunPython(assign_data_to_superuser),
    ] 