"""
Django management command to test Celery configuration and tasks
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from book_tts.celery import debug_task
from workbench.tasks import synthesize_audio_task
from workbench.models import Books


class Command(BaseCommand):
    help = 'Test Celery configuration and tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-debug',
            action='store_true',
            help='Test the debug task',
        )
        parser.add_argument(
            '--test-synthesis',
            action='store_true',
            help='Test the audio synthesis task (requires valid user and book)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID for testing synthesis task',
        )
        parser.add_argument(
            '--book-id',
            type=int,
            help='Book ID for testing synthesis task',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Celery configuration...'))

        if options['test_debug']:
            self.test_debug_task()

        if options['test_synthesis']:
            if not options['user_id'] or not options['book_id']:
                self.stdout.write(
                    self.style.ERROR('--user-id and --book-id are required for synthesis test')
                )
                return
            self.test_synthesis_task(options['user_id'], options['book_id'])

        if not options['test_debug'] and not options['test_synthesis']:
            self.stdout.write(
                self.style.WARNING('No tests specified. Use --test-debug or --test-synthesis')
            )

    def test_debug_task(self):
        """Test the debug task from Celery configuration"""
        self.stdout.write('Testing debug task...')
        
        try:
            # Test synchronous execution first
            result = debug_task.apply()
            self.stdout.write(
                self.style.SUCCESS(f'Debug task executed synchronously: {result}')
            )
            
            # Test asynchronous execution
            task = debug_task.delay()
            self.stdout.write(
                self.style.SUCCESS(f'Debug task queued asynchronously with ID: {task.id}')
            )
            
            # Check task state
            self.stdout.write(f'Task state: {task.state}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Debug task failed: {str(e)}')
            )

    def test_synthesis_task(self, user_id, book_id):
        """Test the audio synthesis task"""
        self.stdout.write(f'Testing synthesis task with user {user_id} and book {book_id}...')
        
        try:
            # Verify user and book exist
            user = User.objects.get(pk=user_id)
            book = Books.objects.get(pk=book_id)
            
            self.stdout.write(f'Found user: {user.username}')
            self.stdout.write(f'Found book: {book.name}')
            
            # Test with minimal text
            test_text = "这是一个测试文本，用于验证Celery音频合成任务的配置。"
            
            # Queue the task
            task = synthesize_audio_task.delay(
                user_id=user_id,
                text=test_text,
                voice_name='zh-CN-YunxiNeural',  # Default voice
                book_id=book_id,
                title='Celery测试音频',
                page_display_name='测试页面',
                audio_title='Celery配置测试',
                ip_address='127.0.0.1',
                user_agent='Django Management Command'
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Synthesis task queued with ID: {task.id}')
            )
            self.stdout.write(f'Task state: {task.state}')
            self.stdout.write('You can check task progress in the Django admin or by monitoring the worker.')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with ID {user_id} does not exist')
            )
        except Books.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Book with ID {book_id} does not exist')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Synthesis task failed: {str(e)}')
            ) 