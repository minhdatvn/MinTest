# Generated by Django 4.2.22 on 2025-06-06 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz_app', '0002_alter_answer_options_alter_attemptanswer_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='is_temporary',
            field=models.BooleanField(default=False),
        ),
    ]
