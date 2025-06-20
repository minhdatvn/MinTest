# Generated by Django 4.2.22 on 2025-06-06 03:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('quiz_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='answer',
            options={'verbose_name': 'Đáp án', 'verbose_name_plural': 'Đáp án'},
        ),
        migrations.AlterModelOptions(
            name='attemptanswer',
            options={'verbose_name': 'Câu trả lời trong Lượt làm bài', 'verbose_name_plural': 'Câu trả lời trong Lượt làm bài'},
        ),
        migrations.AlterModelOptions(
            name='question',
            options={'verbose_name': 'Câu hỏi', 'verbose_name_plural': 'Câu hỏi'},
        ),
        migrations.AlterModelOptions(
            name='quiz',
            options={'verbose_name': 'Đề thi', 'verbose_name_plural': 'Đề thi'},
        ),
        migrations.AlterModelOptions(
            name='quizquestion',
            options={'ordering': ['order_in_quiz'], 'verbose_name': 'Câu hỏi trong Đề thi', 'verbose_name_plural': 'Câu hỏi trong Đề thi'},
        ),
        migrations.AlterModelOptions(
            name='topic',
            options={'verbose_name': 'Chủ đề', 'verbose_name_plural': 'Chủ đề'},
        ),
        migrations.AlterModelOptions(
            name='topicgroup',
            options={'verbose_name': 'Nhóm chủ đề', 'verbose_name_plural': 'Nhóm chủ đề'},
        ),
        migrations.AlterModelOptions(
            name='userattempt',
            options={'verbose_name': 'Lượt làm bài', 'verbose_name_plural': 'Lượt làm bài'},
        ),
        migrations.AlterField(
            model_name='topic',
            name='group',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='quiz_app.topicgroup'),
            preserve_default=False,
        ),
    ]
