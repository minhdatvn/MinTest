# quiz_project/quiz_app/models.py

from django.db import models
from django.contrib.auth.models import User

class TopicGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group_name = models.CharField(max_length=255)
    group_description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Nhóm chủ đề"
        verbose_name_plural = "Nhóm chủ đề"
        unique_together = ('user', 'group_name')

    def __str__(self):
        return self.group_name

class Topic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    group = models.ForeignKey(TopicGroup, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Chủ đề"
        verbose_name_plural = "Chủ đề"
        unique_together = ('user', 'topic_name')

    def __str__(self):
        return self.topic_name

class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    QUESTION_TYPE_CHOICES = [
        ('single_choice', 'Một lựa chọn'),
        ('multiple_choice', 'Nhiều lựa chọn'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='single_choice')

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"

    def __str__(self):
        return f"{self.question_text[:50]}..."

    def get_question_type_display(self):
        return dict(self.QUESTION_TYPE_CHOICES).get(self.question_type)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    answer_image = models.ImageField(upload_to='answer_images/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Đáp án"
        verbose_name_plural = "Đáp án"

    def __str__(self):
        return f"{self.answer_text[:50]}..."

class Quiz(models.Model):
    QUIZ_TYPE_CHOICES = [
        ('static', 'Đề thi tĩnh'),
        ('dynamic', 'Đề thi động'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz_name = models.CharField(max_length=255)
    quiz_type = models.CharField(max_length=10, choices=QUIZ_TYPE_CHOICES, default='static')

    # Dành cho Đề thi tĩnh: danh sách câu hỏi cố định
    questions = models.ManyToManyField(Question, through='QuizQuestion', blank=True)

    # Dành cho cả hai loại: các cài đặt chung
    time_limit_minutes = models.IntegerField()
    scoring_scale_max = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    # Dành cho việc tạo snapshot từ đề thi động
    is_snapshot = models.BooleanField(default=False)
    template_for = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='snapshots')

    # === CÁC TRƯỜNG MỚI CHO TÍNH NĂNG CHIA SẺ BẰNG MÃ ===
    access_code = models.CharField(
        max_length=10, 
        unique=True,    # Đảm bảo mỗi mã là duy nhất
        blank=True, 
        null=True, 
        db_index=True   # Giúp việc tra cứu mã nhanh hơn
    )
    enrolled_users = models.ManyToManyField(
        User, 
        related_name='enrolled_quizzes', # Giúp truy vấn ngược từ User -> Quiz
        blank=True
    )
    # === TRƯỜNG MỚI CHO TÍNH NĂNG CÔNG KHAI ===
    is_public = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Đề thi"
        verbose_name_plural = "Đề thi"

    def __str__(self):
        return self.quiz_name

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Câu hỏi trong Đề thi"
        verbose_name_plural = "Câu hỏi trong Đề thi"
        unique_together = ('quiz', 'question')

class DynamicQuizRule(models.Model):
    """Lưu một quy tắc cho đề thi động, vd: Lấy 5 câu từ chủ đề 'Lịch sử'."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='rules')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    question_count = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Quy tắc Đề thi động"
        verbose_name_plural = "Quy tắc Đề thi động"
        unique_together = ('quiz', 'topic')

    def __str__(self):
        return f"{self.question_count} câu từ '{self.topic.topic_name}' cho đề '{self.quiz.quiz_name}'"

class UserAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, null=True)
    guest_name = models.CharField(max_length=100, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score_achieved = models.FloatField(null=True, blank=True)
    question_order = models.TextField(default='[]')

    class Meta:
        verbose_name = "Lượt làm bài"
        verbose_name_plural = "Lượt làm bài"

    def __str__(self):
        return f"Attempt by {self.user.username} on {self.quiz.quiz_name if self.quiz else 'Deleted Qiz'}"
    
    @property
    def duration(self):
        if self.end_time and self.start_time:
            # Tính khoảng thời gian giữa lúc bắt đầu và kết thúc
            delta = self.end_time - self.start_time

            # Chuyển đổi sang tổng số giây
            total_seconds = int(delta.total_seconds())

            # Chuyển đổi thành phút và giây
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            if minutes > 0:
                return f"{minutes} phút {seconds} giây"
            else:
                return f"{seconds} giây"
        return "Chưa hoàn thành" # Trả về nếu bài thi chưa được nộp

class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(UserAttempt, on_delete=models.CASCADE, related_name='answered_questions')
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True)
    selected_answers = models.ManyToManyField(Answer)
    is_correct = models.BooleanField(default=False)
    points_earned = models.FloatField(default=0)

    class Meta:
        verbose_name = "Câu trả lời trong Lượt làm bài"
        verbose_name_plural = "Câu trả lời trong Lượt làm bài"

    def __str__(self):
        return f"Answer for Q#{self.question.id if self.question else 'N/A'} in Attempt#{self.attempt.id}"