from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
import tempfile
import os

from home.models import UserQuota
from .models import Books, AudioSegment

class QuotaTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create a test book
        self.book = Books.objects.create(
            user=self.user,
            name='Test Book',
            file_type='.pdf'
        )
        
    def test_user_quota_creation(self):
        """Test that user quota is created automatically"""
        quota = UserQuota.objects.get(user=self.user)
        self.assertEqual(quota.remaining_audio_duration, 3600)  # Default 1 hour
        self.assertEqual(quota.available_storage_bytes, 1073741824)  # Default 1GB
        
    def test_quota_methods(self):
        """Test quota checking and consumption methods"""
        quota = UserQuota.objects.get(user=self.user)
        
        # Test can_create_audio
        self.assertTrue(quota.can_create_audio(1800))  # 30 minutes
        self.assertFalse(quota.can_create_audio(7200))  # 2 hours (more than available)
        
        # Test consume_audio_duration
        initial_quota = quota.remaining_audio_duration
        success = quota.consume_audio_duration(600)  # 10 minutes
        self.assertTrue(success)
        self.assertEqual(quota.remaining_audio_duration, initial_quota - 600)
        
        # Test add_audio_duration
        quota.add_audio_duration(300)  # 5 minutes
        self.assertEqual(quota.remaining_audio_duration, initial_quota - 300)
        
        # Test force_consume_audio_duration with sufficient quota
        quota.force_consume_audio_duration(300)  # 5 minutes
        self.assertEqual(quota.remaining_audio_duration, initial_quota - 600)
        
        # Test force_consume_audio_duration with insufficient quota
        remaining = quota.remaining_audio_duration
        quota.force_consume_audio_duration(remaining + 1000)  # More than available
        self.assertEqual(quota.remaining_audio_duration, 0)  # Should be reduced to 0
        
    @patch('book2tts.audio_utils.get_audio_duration')
    @patch('book2tts.audio_utils.estimate_audio_duration_from_text')
    @patch('book2tts.edgetts.EdgeTTS.synthesize_long_text')
    def test_synthesize_audio_quota_deduction(self, mock_synthesize, mock_estimate, mock_get_duration):
        """Test that audio synthesis properly deducts quota"""
        # Mock successful audio synthesis
        mock_synthesize.return_value = True
        
        # Mock estimated duration (used for pre-check) to return 100 seconds
        mock_estimate.return_value = 100
        
        # Mock actual audio duration to return 120 seconds
        mock_get_duration.return_value = 120
        
        # Get initial quota
        quota = UserQuota.objects.get(user=self.user)
        initial_quota = quota.remaining_audio_duration
        
        # Create a temporary file to simulate audio output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b'fake audio data')
        
        try:
            # Mock the temporary file creation in the view
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = temp_path
                
                # Make request to synthesize audio
                response = self.client.post(reverse('synthesize_audio'), {
                    'text': 'This is a test text for audio synthesis.',
                    'voice_name': 'zh-CN-YunxiNeural',
                    'book_id': self.book.id,
                    'title': 'Test Audio'
                })
                
                self.assertEqual(response.status_code, 200)
                
                # Check that quota was deducted by actual duration (120 seconds)
                quota.refresh_from_db()
                self.assertEqual(quota.remaining_audio_duration, initial_quota - 120)
                
                # Check that audio segment was created
                self.assertTrue(AudioSegment.objects.filter(book=self.book, user=self.user).exists())
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    @patch('book2tts.audio_utils.estimate_audio_duration_from_text')
    def test_insufficient_quota_rejection_before_synthesis(self, mock_estimate):
        """Test that synthesis is rejected when estimated quota is insufficient (before synthesis)"""
        # Mock estimated duration to return 3700 seconds (more than default 3600)
        mock_estimate.return_value = 3700
        
        # Set quota to default value (3600 seconds)
        quota = UserQuota.objects.get(user=self.user)
        self.assertEqual(quota.remaining_audio_duration, 3600)
        
        # Try to synthesize audio (estimated duration exceeds quota)
        response = self.client.post(reverse('synthesize_audio'), {
            'text': 'This is a test text.',
            'voice_name': 'zh-CN-YunxiNeural',
            'book_id': self.book.id,
            'title': 'Test Audio'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('配额不足', response_data['message'])
        self.assertIn('预估需要', response_data['message'])
        
    def test_insufficient_quota_rejection(self):
        """Test that synthesis is rejected when quota is insufficient"""
        # Set quota to very low value
        quota = UserQuota.objects.get(user=self.user)
        quota.remaining_audio_duration = 10  # Only 10 seconds
        quota.save()
        
        # Try to synthesize audio (will estimate more than 10 seconds)
        response = self.client.post(reverse('synthesize_audio'), {
            'text': 'This is a very long text that would require much more than 10 seconds to synthesize into audio. ' * 10,
            'voice_name': 'zh-CN-YunxiNeural',
            'book_id': self.book.id,
            'title': 'Test Audio'
        })
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('配额不足', response_data['message'])
        
    @patch('book2tts.audio_utils.get_audio_duration')
    def test_delete_audio_segment_quota_return(self, mock_get_duration):
        """Test that deleting audio segment returns quota to user"""
        # Mock audio duration to return 180 seconds
        mock_get_duration.return_value = 180
        
        # Create an audio segment
        segment = AudioSegment.objects.create(
            book=self.book,
            user=self.user,
            title='Test Audio',
            text='Test text content',
            book_page='1'
        )
        
        # Get initial quota and consume some
        quota = UserQuota.objects.get(user=self.user)
        initial_quota = quota.remaining_audio_duration
        quota.consume_audio_duration(180)  # Simulate the quota was consumed when creating
        
        # Verify quota was consumed
        self.assertEqual(quota.remaining_audio_duration, initial_quota - 180)
        
        # Delete the audio segment
        response = self.client.delete(f'/workbench/audio/delete/{segment.id}/')
        
        # Check that quota was returned
        quota.refresh_from_db()
        self.assertEqual(quota.remaining_audio_duration, initial_quota)  # Should be back to original
        
        # Check that segment was deleted
        self.assertFalse(AudioSegment.objects.filter(id=segment.id).exists())
        
    @patch('book2tts.audio_utils.get_audio_duration')
    @patch('book2tts.audio_utils.estimate_audio_duration_from_text')
    @patch('book2tts.edgetts.EdgeTTS.synthesize_long_text')
    def test_synthesize_audio_quota_force_deduction(self, mock_synthesize, mock_estimate, mock_get_duration):
        """Test that audio synthesis force deducts quota even if actual duration exceeds remaining quota"""
        # Mock successful audio synthesis
        mock_synthesize.return_value = True
        
        # Mock estimated duration (used for pre-check) to return 100 seconds
        mock_estimate.return_value = 100
        
        # Mock actual audio duration to return 4000 seconds (more than default 3600)
        mock_get_duration.return_value = 4000
        
        # Get initial quota (should be 3600 seconds by default)
        quota = UserQuota.objects.get(user=self.user)
        initial_quota = quota.remaining_audio_duration
        self.assertEqual(initial_quota, 3600)
        
        # Create a temporary file to simulate audio output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b'fake audio data')
        
        try:
            # Mock the temporary file creation in the view
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = temp_path
                
                # Make request to synthesize audio
                response = self.client.post(reverse('synthesize_audio'), {
                    'text': 'This is a test text for audio synthesis.',
                    'voice_name': 'zh-CN-YunxiNeural',
                    'book_id': self.book.id,
                    'title': 'Test Audio'
                })
                
                self.assertEqual(response.status_code, 200)
                
                # Check that quota was reduced to 0 (since actual duration 4000 > remaining 3600)
                quota.refresh_from_db()
                self.assertEqual(quota.remaining_audio_duration, 0)
                
                # Check that audio segment was still created
                self.assertTrue(AudioSegment.objects.filter(book=self.book, user=self.user).exists())
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def tearDown(self):
        """Clean up after tests"""
        # Clean up any created audio segments and their files
        for segment in AudioSegment.objects.filter(user=self.user):
            if segment.file and os.path.exists(segment.file.path):
                os.remove(segment.file.path)
            segment.delete()
