# quiz_project/quiz_app/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.defaults import bad_request
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.guest_homepage_view, name='guest_homepage'), # TRANG CHỦ MỚI CHO KHÁCH
    path('guest/start/', views.guest_start_quiz, name='guest_start_quiz'), # Trang làm bài cho khách
    path('dashboard/', views.dashboard_view, name='dashboard'), # Dashboard cho người đã đăng nhập    
    path("search/", views.question_search_view, name="question_search"),  # Tìm kiếm
    path("groups/", views.topic_group_list_view, name="topic_group_list"),  # Nhóm chủ đề
    path("import-all/", views.import_all_data_view, name="import_all_data"),  # Import nhóm chủ đề
    path(
        "export-all/", views.export_all_select_view, name="export_all_select"
    ),  # Export nhóm chủ đề
    path(
        "export-group/<int:group_id>/",
        views.export_topic_group_view,
        name="export_topic_group",
    ),  # Export nhóm chủ đề
    path(
        "topic/<int:topic_id>/",
        views.question_list_in_topic,
        name="question_list_in_topic",
    ),  # Câu hỏi
    path(
        "group/add/", views.create_topic_group, name="create_topic_group"
    ),  # Tạo nhóm chủ đề
    path(
        "group/<int:group_id>/edit/",
        views.update_topic_group,
        name="update_topic_group",
    ),  # Sửa nhóm chủ đề
    path(
        "group/<int:group_id>/delete/",
        views.delete_topic_group,
        name="delete_topic_group",
    ),  # Xóa nhóm chủ đề
    path("topic/add/", views.create_topic, name="create_topic"),  # Tạo chủ đề
    path(
        "topic/<int:topic_id>/edit/", views.update_topic, name="update_topic"
    ),  # Sửa chủ đề
    path(
        "topic/<int:topic_id>/delete/", views.delete_topic, name="delete_topic"
    ),  # Xóa chủ đề
    path(
        "topic/<int:topic_id>/question/add/",
        views.create_question,
        name="create_question",
    ),  # Tạo câu hỏi
    path(
        "topic/<int:topic_id>/import/",
        views.import_questions_to_topic,
        name="import_questions_to_topic",
    ),  # Import nội dung
    path(
        "topic/<int:topic_id>/export/",
        views.export_questions_from_topic,
        name="export_questions_from_topic",
    ),  # Export nội dung
    path(
        "question/<int:question_id>/", views.question_detail, name="question_detail"
    ),  # Đáp án
    path(
        "question/<int:question_id>/edit/",
        views.update_question,
        name="update_question",
    ),  # Sửa câu hỏi
    path(
        "question/<int:question_id>/delete/",
        views.delete_question,
        name="delete_question",
    ),  # Xóa 1 câu hỏi
    path("quizzes/", views.quiz_list, name="quiz_list"),  # Danh sách đề thi
    path(
        "quizzes/add/", views.create_quiz, name="create_quiz"
    ),  # Tạo đề thi đưa vào danh sách
    path(
        "quizzes/enroll/", views.enroll_in_quiz, name="enroll_in_quiz"
    ),  # Nhập đề thi vào danh sách
    path(
        "quiz/<int:quiz_id>/start/", views.start_quiz, name="start_quiz"
    ),  # Bắt đầu bài thi
    path(
        "quizzes/<int:quiz_id>/delete/", views.delete_quiz_view, name="delete_quiz"
    ),  # Xóa đề thi đã tạo
    path(
        "quizzes/<int:quiz_id>/generate-code/",
        views.generate_quiz_code,
        name="generate_quiz_code",
    ),  # Tạo mã chia sẻ đề thi
    path(
        "attempt/<int:attempt_id>/", views.take_quiz, name="take_quiz"
    ),  # Trang làm bài thi
    path(
        "attempt/<int:attempt_id>/result/", views.attempt_result, name="attempt_result"
    ),  # Kết quả bài thi
    path(
        "quizzes/take-dynamic-now/",
        views.take_dynamic_quiz_now,
        name="take_dynamic_quiz_now",
    ),  # Làm bài ngay
    path(
        "api/get-topics/", views.get_topics_for_group_view, name="api_get_topics"
    ),  # Lấy thông tin chủ đề cho Nhóm chủ đề
    path(
        "api/question-details/<int:question_id>/",
        views.get_question_details_view,
        name="api_get_question_details",
    ),  # Xem câu hỏi trong trang Tìm kiếm
    path("history/", views.history_list, name="history_list"),  # Lịch sử làm bài
    path(
        "attempt/<int:attempt_id>/delete/",
        views.delete_attempt_view,
        name="delete_attempt",
    ),  # Xóa Lịch sử làm bài
    path("signup/", views.signup_view, name="signup"),  # Đăng ký
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="quiz_app/login.html"),
        name="login",
    ),  # Đăng nhập
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),  # Đăng xuất
    path(
        "reports/", views.quiz_report_list_view, name="quiz_report_list"
    ),  # Báo cáo tổng quát
    path(
        "reports/<int:quiz_id>/",
        views.quiz_detail_report_view,
        name="quiz_detail_report",
    ),  # Báo cáo chi tiết
]

handler400 = bad_request
