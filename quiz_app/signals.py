from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Question, Quiz

@receiver(pre_delete, sender=Question)
def deactivate_quizzes_on_question_delete(sender, instance, **kwargs):
    """
    Signal này sẽ được kích hoạt TRƯỚC KHI một câu hỏi (instance) bị xóa.
    """
    # Tìm tất cả các đề thi tĩnh có chứa câu hỏi sắp bị xóa
    quizzes_to_check = Quiz.objects.filter(
        questions=instance, 
        quiz_type='static',
        is_snapshot=False # Chỉ kiểm tra các đề thi gốc, không phải snapshot
    )

    for quiz in quizzes_to_check:
        # Nếu đề thi này chỉ còn duy nhất 1 câu hỏi (là câu sắp bị xóa)
        if quiz.questions.count() == 1:
            # Vô hiệu hóa đề thi này vì nó sẽ trở nên rỗng
            quiz.is_active = False
            quiz.save(update_fields=['is_active'])