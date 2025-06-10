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
    DynamicQuizRule,
)

# Tạo một lớp tùy chỉnh cho việc hiển thị Quiz trong trang Admin
class QuizAdmin(admin.ModelAdmin):
    # Các trường sẽ được hiển thị trên trang danh sách
    list_display = ('quiz_name', 'user', 'quiz_type', 'is_public', 'created_at')
    
    # Cho phép lọc theo các trường này
    list_filter = ('is_public', 'quiz_type', 'user')
    
    # Cho phép sửa nhanh trường 'is_public' ngay trên danh sách
    list_editable = ('is_public',)
    
    # Thêm ô tìm kiếm
    search_fields = ('quiz_name', 'user__username')

# Đăng ký các model của bạn ở đây để chúng xuất hiện trên trang admin
admin.site.register(TopicGroup)
admin.site.register(Topic)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Quiz, QuizAdmin)
admin.site.register(QuizQuestion)
admin.site.register(UserAttempt)
admin.site.register(AttemptAnswer)
admin.site.register(DynamicQuizRule)