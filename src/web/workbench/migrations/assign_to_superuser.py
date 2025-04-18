from django.db import migrations
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

def assign_data_to_superuser(apps, schema_editor):
    # Get models
    Books = apps.get_model('workbench', 'Books')
    AudioSegment = apps.get_model('workbench', 'AudioSegment')
    
    # Check if there are any records to update
    if not Books.objects.exists() and not AudioSegment.objects.exists():
        print("No books or audio segments found, skipping migration")
        return
    
    User = get_user_model()
    
    # Temporarily disconnect signals to avoid UserProfile creation
    # First, store the receivers
    receivers = []
    for receiver_function in post_save.receivers[:]:
        if receiver_function[1].__self__.__class__.__name__ == 'User' or receiver_function[1].__module__ == 'workbench.models':
            receivers.append((receiver_function, post_save.disconnect(receiver=receiver_function[1], 
                                                                    sender=User,
                                                                    dispatch_uid=receiver_function[0])))
    
    try:
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
    
    finally:
        # Reconnect all signals
        for receiver_function, _ in receivers:
            post_save.connect(receiver=receiver_function[1], 
                            sender=User,
                            dispatch_uid=receiver_function[0])

class Migration(migrations.Migration):
    dependencies = [
        ('workbench', '0004_audiosegment'),  # Update this to make sure AudioSegment model is available
    ]
    
    operations = [
        migrations.RunPython(assign_data_to_superuser),
    ] 