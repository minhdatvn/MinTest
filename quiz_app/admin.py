# quiz_project/quiz_app/admin.py

from django.contrib import admin
from .models import (
    TopicGroup,
    Topic,
    Question,
    Answer,
    Quiz,
    QuizQuestion,
    UserAttempt,
    AttemptAnswer,
)

# Đăng ký các model của bạn ở đây để chúng xuất hiện trên trang admin
admin.site.register(TopicGroup)
admin.site.register(Topic)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Quiz)
admin.site.register(QuizQuestion)
admin.site.register(UserAttempt)
admin.site.register(AttemptAnswer)