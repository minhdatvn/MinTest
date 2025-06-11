from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from quiz_app.models import Quiz, UserAttempt # Chú ý import model từ app

class UserAttemptModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.quiz = Quiz.objects.create(
            user=self.user, 
            quiz_name='Bài test về Model', 
            time_limit_minutes=10
        )

    def test_duration_property_calculates_correctly(self):
        start = timezone.now()
        end = start + timedelta(minutes=5, seconds=30)
        attempt = UserAttempt.objects.create(
            user=self.user,
            quiz=self.quiz,
            start_time=start,
            end_time=end
        )
        self.assertEqual(attempt.duration, "5 phút 30 giây")

    def test_duration_for_incomplete_attempt(self):
        attempt = UserAttempt.objects.create(
            user=self.user,
            quiz=self.quiz
        )
        self.assertEqual(attempt.duration, "Chưa hoàn thành")