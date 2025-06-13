# quiz_project/quiz_app/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Count, Sum, Case, When, Q, Avg
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from .models import (
    TopicGroup,
    Topic,
    Question,
    Quiz,
    UserAttempt,
    Answer,
    AttemptAnswer,
    DynamicQuizRule,
)
from .forms import (
    TopicGroupForm,
    TopicForm,
    QuestionForm,
    CreateAnswerFormSet,
    EditAnswerFormSet,
    QuizForm,
    UploadFileForm,
    QuestionSearchForm,
    SignUpForm,
    EnrollmentForm,
    CustomAuthenticationForm,
)
from io import BytesIO
from datetime import timedelta
import math
import string
import random
import pandas as pd
import os
import json

# --- Hàm helper giúp tạo nhóm chủ đề mặc định ---


def _get_or_create_default_group(user):
    default_group, created = TopicGroup.objects.get_or_create(
        user=user,
        group_name="Các chủ đề khác",
        defaults={
            "group_description": "Nhóm mặc định cho các chủ đề chưa được phân loại."
        },
    )
    return default_group


# --- Hàm helper giúp đọc dữ liệu file excel khi Nhập ---


def _process_question_dataframe(df, topic_instance):
    """
    Hàm helper nhận một DataFrame và một đối tượng Topic,
    sau đó xử lý và tạo các câu hỏi, câu trả lời.
    Trả về số lượng câu hỏi đã được thêm.
    """
    questions_added_count = 0
    if df.empty:
        return 0

    current_question_text = None
    current_answers = []
    # Thêm một dòng trống vào cuối DataFrame để đảm bảo câu hỏi cuối cùng được xử lý
    df.loc[len(df)] = [None] * len(df.columns)

    for index, row in df.iterrows():
        # Một dòng được coi là trống nếu cột 'Nội dung' và 'Đáp án đúng?' đều trống
        is_content_empty = pd.isna(row.get("Nội dung"))
        is_correct_marker_empty = pd.isna(row.get("Đáp án đúng?"))
        is_empty_row = is_content_empty and is_correct_marker_empty

        # Nếu là dòng trống và chúng ta đang có dữ liệu câu hỏi -> Lưu câu hỏi lại
        if is_empty_row and current_question_text:
            if current_answers:
                correct_answers_count = sum(
                    1 for ans in current_answers if ans["is_correct"]
                )
                if correct_answers_count > 0:
                    q_type = (
                        "multiple_choice"
                        if correct_answers_count > 1
                        else "single_choice"
                    )
                    new_q = Question.objects.create(
                        topic=topic_instance,
                        question_text=str(current_question_text),
                        question_type=q_type,
                    )
                    for ans_data in current_answers:
                        Answer.objects.create(
                            question=new_q,
                            answer_text=str(ans_data["text"]),
                            is_correct=ans_data["is_correct"],
                        )
                    questions_added_count += 1
            # Reset để chuẩn bị cho câu hỏi tiếp theo
            current_question_text = None
            current_answers = []

        # Nếu là dòng có nội dung
        elif not is_content_empty:
            if current_question_text is None:
                # Bắt đầu một câu hỏi mới
                current_question_text = row.get("Nội dung")
                current_answers = []  # Reset lại mảng đáp án
            else:
                # Đây là dòng của một câu trả lời
                answer_text = row.get("Nội dung")
                is_correct = str(row.get("Đáp án đúng?")).strip().upper() == "X"
                current_answers.append({"text": answer_text, "is_correct": is_correct})

    return questions_added_count


# --- Hàm Trang chủ ---


@login_required
def dashboard_view(request):
    user = request.user

    # 1. Thống kê cho thẻ "Quản lý nội dung"
    content_stats = {
        'topic_groups': TopicGroup.objects.filter(user=user).count(),
        'topics': Topic.objects.filter(user=user).count(),
        'questions': Question.objects.filter(topic__user=user).count(),
    }

    # 2. Thống kê cho thẻ "Danh sách đề thi"
    quiz_stats = {
        'static': Quiz.objects.filter(user=user, quiz_type='static', is_snapshot=False).count(),
        'dynamic': Quiz.objects.filter(user=user, quiz_type='dynamic', is_snapshot=False).count(),
    }

    # 3. Lấy danh sách đề thi công khai (GIỚI HẠN HIỂN THỊ)
    # Sắp xếp theo ngày tạo mới nhất và chỉ lấy 4 đề thi đầu tiên
    public_quizzes = Quiz.objects.filter(is_public=True, is_snapshot=False).annotate(
        question_count=Count('questions')
    ).order_by('-created_at')[:4]

    # 4. Form tham gia bằng mã
    enrollment_form = EnrollmentForm()

    # 5. Hoạt động gần đây: Lấy 5 lượt làm bài cuối cùng của người dùng
    recent_attempts = UserAttempt.objects.filter(user=user, end_time__isnull=False).select_related(
        'quiz'
    ).order_by('-start_time')[:5]

    # 6. Đưa tất cả vào context để gửi sang template
    context = {
        'content_stats': content_stats,
        'quiz_stats': quiz_stats,
        'public_quizzes': public_quizzes,
        'enrollment_form': enrollment_form,
        'recent_attempts': recent_attempts,
    }
    
    return render(request, "quiz_app/dashboard.html", context)


# --- Hàm Trang Nhóm chủ đề ---


@login_required
def topic_group_list_view(request):
    """
    View này bây giờ chỉ chịu trách nhiệm hiển thị danh sách các nhóm chủ đề.
    """
    groups = (
        TopicGroup.objects.filter(user=request.user)
        .prefetch_related("topic_set")
        .order_by("group_name")
    )
    context = {"topic_groups": groups}
    return render(request, "quiz_app/topic_group_list.html", context)


# --- Hàm hiện câu hỏi trong chủ đề ---


@login_required
def question_list_in_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)

    # Logic lấy câu hỏi và phân trang vẫn giữ nguyên
    all_questions = Question.objects.filter(topic=topic).order_by("id")
    paginator = Paginator(all_questions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ===== BẮT ĐẦU LOGIC MỚI ĐỂ XỬ LÝ YÊU CẦU AJAX =====
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if is_ajax:
        # Nếu là AJAX, đóng gói dữ liệu và trả về dưới dạng JSON
        questions_data = []
        for q in page_obj.object_list:
            questions_data.append(
                {
                    "id": q.id,
                    "text": q.question_text,
                    "type": q.get_question_type_display(),
                }
            )

        return JsonResponse(
            {
                "questions": questions_data,
                "has_previous": page_obj.has_previous(),
                "previous_page_number": (
                    page_obj.previous_page_number() if page_obj.has_previous() else None
                ),
                "has_next": page_obj.has_next(),
                "next_page_number": (
                    page_obj.next_page_number() if page_obj.has_next() else None
                ),
                "current_page": page_obj.number,
                "total_pages": page_obj.paginator.num_pages,
            }
        )

    # Nếu không phải AJAX, render trang HTML như bình thường
    # (phần này vẫn cần để trang tải lần đầu)
    question_instance_for_form = Question(topic=topic)
    form = QuestionForm()
    formset = CreateAnswerFormSet(instance=question_instance_for_form, prefix="form")

    context = {"topic": topic, "page_obj": page_obj, "form": form, "formset": formset}
    return render(request, "quiz_app/question_list.html", context)


# --- Hàm hiện đáp án trong câu hỏi ---


@login_required
def question_detail(request, question_id):
    question = get_object_or_404(Question, id=question_id, topic__user=request.user)
    context = {"question": question}

    return render(request, "quiz_app/question_detail.html", context)


# --- Hàm tạo Nhóm chủ đề ---


@login_required
@permission_required("quiz_app.add_topicgroup", raise_exception=True)
def create_topic_group(request):
    # Xử lý cho yêu cầu POST (dù là AJAX hay không)
    if request.method == "POST":
        # Kiểm tra xem có phải là yêu cầu AJAX không
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            data = json.loads(request.body)
            form = TopicGroupForm(data)
            if form.is_valid():
                new_group = form.save(commit=False)
                new_group.user = request.user
                new_group.save()
                return JsonResponse(
                    {
                        "success": True,
                        "new_group": {
                            "id": new_group.id,
                            "name": new_group.group_name,
                            "description": new_group.group_description,
                        },
                    }
                )
            else:
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )
    # Xử lý cho yêu cầu GET (khi người dùng truy cập trang form trực tiếp)
    else:
        form = TopicGroupForm()

    context = {"form": form}
    return render(request, "quiz_app/topic_group_form.html", context)


# --- Hàm chỉnh sửa Nhóm chủ đề ---


@login_required
@permission_required("quiz_app.change_topicgroup", raise_exception=True)
def update_topic_group(request, group_id):
    group = get_object_or_404(TopicGroup, id=group_id, user=request.user)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # Nhánh xử lý cho các yêu cầu POST
    if request.method == "POST":
        # Trường hợp 1: POST từ AJAX
        if is_ajax:
            data = json.loads(request.body)
            form = TopicGroupForm(data, instance=group)
            if form.is_valid():
                updated_group = form.save()
                return JsonResponse(
                    {
                        "success": True,
                        "group": {
                            "id": updated_group.id,
                            "name": updated_group.group_name,
                        },
                    }
                )
            else:
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )
    # Nhánh xử lý cho các yêu cầu GET
    else:
        # Trường hợp 3: GET từ AJAX
        if is_ajax:
            data = {
                "id": group.id,
                "name": group.group_name,
                "description": group.group_description,
            }
            return JsonResponse(data)
        # Trường hợp 4: GET từ trình duyệt thông thường (khối else bị thiếu)
        else:
            return redirect("topic_group_list")


# --- Hàm xóa Nhóm chủ đề ---


@login_required
@permission_required("quiz_app.delete_topicgroup", raise_exception=True)
def delete_topic_group(request, group_id):
    # Chỉ cho phép phương thức POST để bảo mật
    if request.method == "POST":
        group = get_object_or_404(TopicGroup, id=group_id, user=request.user)

        # Vẫn giữ logic không cho xóa nhóm mặc định
        if group.group_name == "Các chủ đề khác":
            return JsonResponse(
                {"success": False, "message": "Bạn không thể xóa nhóm mặc định."},
                status=400,
            )

        # Logic di chuyển các chủ đề con
        default_group = _get_or_create_default_group(request.user)
        group.topic_set.all().update(group=default_group)

        # Xóa nhóm
        group.delete()

        # Trả về tín hiệu thành công dạng JSON
        return JsonResponse({"success": True, "message": "Đã xóa nhóm thành công."})

    # Nếu không phải POST, không làm gì cả hoặc trả về lỗi
    return JsonResponse(
        {"success": False, "message": "Yêu cầu không hợp lệ."}, status=405
    )


# --- Hàm tạo Chủ đề ---


@login_required
@permission_required("quiz_app.add_topic", raise_exception=True)
def create_topic(request):
    if request.method == "POST":
        # Xử lý cho yêu cầu AJAX
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            data = json.loads(request.body)
            # Truyền user vào form để validate tên chủ đề không bị trùng
            form = TopicForm(data, user=request.user)
            if form.is_valid():
                new_topic = form.save(commit=False)
                new_topic.user = request.user

                # Gán nhóm chủ đề từ dữ liệu gửi lên
                group_id = data.get("group")
                if group_id:
                    # Lấy đúng đối tượng TopicGroup từ id
                    new_topic.group = get_object_or_404(
                        TopicGroup, id=group_id, user=request.user
                    )
                else:
                    # Nếu không chọn nhóm, gán vào nhóm mặc định
                    new_topic.group = _get_or_create_default_group(request.user)

                new_topic.save()

                # Trả về dữ liệu của topic vừa tạo để frontend cập nhật
                return JsonResponse(
                    {
                        "success": True,
                        "topic": {
                            "id": new_topic.id,
                            "name": new_topic.topic_name,
                            "description": new_topic.description,
                            "group_id": new_topic.group.id,
                            "question_count": 0,  # Topic mới chưa có câu hỏi
                            # Dùng reverse() sẽ tốt hơn
                            "update_url": f"/topic/{new_topic.id}/edit/",
                            "delete_url": f"/topic/{new_topic.id}/delete/",
                            "question_list_url": f"/topic/{new_topic.id}/",
                        },
                    }
                )
            else:
                # Trả về lỗi nếu form không hợp lệ
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )
    # Xử lý cho yêu cầu GET thông thường (vẫn cần cho trang chỉnh sửa)
    else:
        form = TopicForm(user=request.user)

    context = {"form": form}
    return render(request, "quiz_app/topic_form.html", context)


# --- Hàm sửa Chủ đề ---


@login_required
@permission_required("quiz_app.change_topic", raise_exception=True)
def update_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # Nhánh xử lý cho các yêu cầu POST
    if request.method == "POST":
        if is_ajax:
            data = json.loads(request.body)
            form = TopicForm(data, instance=topic, user=request.user)
            if form.is_valid():
                updated_topic = form.save(commit=False)
                updated_topic.save(update_fields=["topic_name", "description"])
                return JsonResponse(
                    {
                        "success": True,
                        "topic": {
                            "id": updated_topic.id,
                            "name": updated_topic.topic_name,
                            "description": updated_topic.description,
                        },
                    }
                )
            else:
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )

    # Nhánh xử lý cho các yêu cầu GET
    else:
        # Trường hợp 3: GET từ AJAX
        if is_ajax:
            data = {
                "id": topic.id,
                "name": topic.topic_name,
                "description": topic.description,
                "group_id": topic.group.id,
            }
            return JsonResponse(data)
        # Trường hợp 4: GET thông thường
        else:
            return redirect("topic_group_list")


# --- Hàm xóa Chủ đề ---
@login_required
@permission_required("quiz_app.delete_topic", raise_exception=True)
def delete_topic(request, topic_id):
    # Từ giờ, view này sẽ chỉ chấp nhận yêu cầu POST từ AJAX của chúng ta
    if request.method == "POST":
        topic = get_object_or_404(Topic, id=topic_id, user=request.user)

        # Nếu mọi thứ đều ổn, tiến hành xóa
        topic_name = topic.topic_name
        topic.delete()

        # Và trả về thông báo thành công dạng JSON
        return JsonResponse(
            {"success": True, "message": f"Đã xóa thành công chủ đề '{topic_name}'."}
        )

    return redirect("topic_group_list")


# --- Hàm tạo Câu hỏi ---
@login_required
@permission_required("quiz_app.add_question", raise_exception=True)
@transaction.atomic
def create_question(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)

    # Tạo một đối tượng Question rỗng để làm instance cho formset
    question_instance_for_formset = Question(topic=topic)

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES)
        formset = CreateAnswerFormSet(
            request.POST,
            request.FILES,
            instance=question_instance_for_formset,
            prefix="form",
        )

        if form.is_valid() and formset.is_valid():
            new_question = form.save(commit=False)
            new_question.topic = topic

            correct_answers_count = sum(
                1
                for f_data in formset.cleaned_data
                if f_data and f_data.get("is_correct")
            )
            new_question.question_type = (
                "multiple_choice" if correct_answers_count > 1 else "single_choice"
            )

            new_question.save()
            formset.instance = new_question
            formset.save()

            # Trả về tín hiệu để htmx tải lại toàn bộ trang
            response = HttpResponse(status=204)  # Status 204: No Content
            # Header đặc biệt htmx sẽ nhận diện
            response["HX-Refresh"] = "true"
            return response
    else:  # Nếu là yêu cầu GET
        form = QuestionForm()
        formset = CreateAnswerFormSet(
            instance=question_instance_for_formset, prefix="form"
        )

    # Context để render template
    context = {"topic": topic, "form": form, "formset": formset}

    # Nếu là POST không hợp lệ, render lại form với các lỗi
    # htmx sẽ nhận HTML này và thay thế form cũ trong modal
    return render(request, "quiz_app/_create_question_form.html", context)


# --- Hàm sửa Câu hỏi ---


@login_required
@permission_required("quiz_app.change_question", raise_exception=True)
@transaction.atomic
def update_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, topic__user=request.user)

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES, instance=question)
        formset = EditAnswerFormSet(
            request.POST, request.FILES, instance=question, prefix="form"
        )

        if form.is_valid() and formset.is_valid():
            question_instance = form.save()
            formset.save()

            correct_answers_count = question_instance.answers.filter(
                is_correct=True
            ).count()
            question_instance.question_type = (
                "multiple_choice" if correct_answers_count > 1 else "single_choice"
            )
            question_instance.save(update_fields=["question_type"])

            # Tạo một response đặc biệt để htmx có thể nhận diện và tải lại trang
            response = HttpResponse(status=204)  # 204 No Content
            response["HX-Refresh"] = "true"  # Header đặc biệt của htmx
            return response
    else:  # request.method == 'GET'
        form = QuestionForm(instance=question)
        formset = EditAnswerFormSet(instance=question, prefix="form")

    # DÙ LÀ GET HAY POST THẤT BẠI, CŨNG CHỈ CẦN RENDER TEMPLATE NÀY
    return render(
        request,
        "quiz_app/_edit_question_form_body.html",
        {
            "form": form,
            "formset": formset,
            # quan trọng: truyền request.path_info để form biết post đi đâu
            "post_url": request.path_info,
        },
    )


# --- Hàm Xóa 1 câu hỏi ---


@login_required
@permission_required("quiz_app.delete_question", raise_exception=True)
def delete_question(request, question_id):
    # View này chỉ chấp nhận yêu cầu POST từ AJAX
    if request.method == "POST":
        # Tìm câu hỏi và đảm bảo nó thuộc về người dùng đang đăng nhập
        question = get_object_or_404(Question, id=question_id, topic__user=request.user)

        question_text = question.question_text
        question.delete()

        return JsonResponse(
            {"success": True, "message": f"Đã xóa câu hỏi '{question_text[:30]}...'."}
        )

    # Nếu không phải POST, chuyển hướng về trang chủ
    return redirect("dashboard")


# --- Hàm Danh sách Đề thi ---
@login_required
@login_required
def quiz_list(request):
    # Sử dụng Q object để tạo truy vấn OR phức tạp:
    # Lấy các quiz mà user là người tạo HOẶC user có trong danh sách enrolled_users
    user_quizzes_filter = Q(user=request.user) | Q(enrolled_users=request.user)

    # Lấy danh sách đề thi tĩnh
    static_quizzes = (
        Quiz.objects.filter(user_quizzes_filter, is_snapshot=False, quiz_type="static")
        .distinct()
        .annotate(question_count=Count("questions"))
        .order_by("-created_at")
    )

    # Lấy danh sách các mẫu đề thi động
    dynamic_quizzes = (
        Quiz.objects.filter(user_quizzes_filter, is_snapshot=False, quiz_type="dynamic")
        .distinct()
        .annotate(question_count=Sum("rules__question_count"))
        .order_by("-created_at")
    )

    context = {
        "static_quizzes": static_quizzes,
        "dynamic_quizzes": dynamic_quizzes,
    }
    return render(request, "quiz_app/quiz_list.html", context)


# --- Hàm tạo Đề thi ---
@login_required
@permission_required("quiz_app.add_quiz", raise_exception=True)
@transaction.atomic  # Thêm transaction để đảm bảo toàn vẹn dữ liệu
def create_quiz(request):
    if request.method == "POST":
        # Truyền user vào form để __init__ có thể hoạt động
        form = QuizForm(request.POST, user=request.user)
        if form.is_valid():
            quiz_type = form.cleaned_data.get("quiz_type")
            new_quiz = form.save(commit=False)
            new_quiz.user = request.user
            new_quiz.save()  # Lưu quiz object trước để có ID

            if quiz_type == "static":
                # Lấy danh sách câu hỏi đã chọn và gán cho đề thi
                questions = form.cleaned_data.get("questions")
                new_quiz.questions.set(questions)

            elif quiz_type == "dynamic":
                # === BẮT ĐẦU LOGIC MỚI CHO ĐỀ THI ĐỘNG ===
                # Lặp qua tất cả các trường trong form đã được validate
                for field_name, count in form.cleaned_data.items():
                    # Nếu trường có tên bắt đầu là 'dynamic_topic_' và có số lượng > 0
                    if field_name.startswith("dynamic_topic_") and count > 0:
                        # Lấy ID của chủ đề từ tên trường
                        topic_id = int(field_name.split("_")[-1])
                        try:
                            # Lấy đối tượng Topic tương ứng
                            topic = Topic.objects.get(id=topic_id, user=request.user)
                            # Tạo một quy tắc mới và lưu lại
                            DynamicQuizRule.objects.create(
                                quiz=new_quiz, topic=topic, question_count=count
                            )
                        except Topic.DoesNotExist:
                            # Bỏ qua nếu có lỗi không tìm thấy topic, hoặc có thể báo lỗi
                            continue
                # === KẾT THÚC LOGIC MỚI ===

            return redirect("quiz_list")
    else:
        form = QuizForm(user=request.user)

    # Chuẩn bị dữ liệu cho cây thư mục (giữ nguyên)
    topic_groups = (
        TopicGroup.objects.filter(user=request.user, topic__questions__isnull=False)
        .distinct()
        .prefetch_related("topic_set")
    )

    groups_with_questions = []
    for group in topic_groups:
        topics_with_q = (
            group.topic_set.filter(questions__isnull=False)
            .distinct()
            .prefetch_related("questions")
        )
        if topics_with_q.exists():
            group.topics_with_questions = topics_with_q
            groups_with_questions.append(group)

    context = {"form": form, "topic_groups_with_questions": groups_with_questions}
    return render(request, "quiz_app/quiz_form.html", context)


# --- Hàm xóa Đề thi ---
@login_required
@permission_required("quiz_app.delete_quiz", raise_exception=True)
def delete_quiz_view(request, quiz_id):
    if request.method == "POST":
        quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)
        quiz.delete()
        return JsonResponse({"success": True, "message": "Đã xóa đề thi thành công."})
    return JsonResponse(
        {"success": False, "message": "Yêu cầu không hợp lệ."}, status=400
    )


# --- Hàm chia sẻ đề thi ---


@login_required
@permission_required("quiz_app.change_quiz", raise_exception=True)
def generate_quiz_code(request, quiz_id):
    if request.method == "POST":
        quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user)

        # Nếu quiz đã có mã, trả về mã cũ
        if quiz.access_code:
            return JsonResponse({"success": True, "code": quiz.access_code})

        # Tạo mã mới ngẫu nhiên và đảm bảo nó là duy nhất
        while True:
            # Tạo một mã 6 ký tự ngẫu nhiên (chữ hoa và số)
            new_code = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            # Kiểm tra xem mã đã tồn tại chưa
            if not Quiz.objects.filter(access_code=new_code).exists():
                break  # Nếu chưa, thoát khỏi vòng lặp

        quiz.access_code = new_code
        quiz.save(update_fields=["access_code"])

        return JsonResponse({"success": True, "code": new_code})

    return JsonResponse(
        {"success": False, "message": "Yêu cầu không hợp lệ"}, status=400
    )


# --- Hàm nhập mã đề thi ---


@login_required
def enroll_in_quiz(request):
    # View này chỉ xử lý yêu cầu POST từ form nhập mã
    if request.method == "POST":
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["access_code"].upper()
            try:
                # Tìm đề thi có mã tương ứng
                quiz_to_enroll = Quiz.objects.get(access_code=code)

                # Kiểm tra các trường hợp đặc biệt
                if quiz_to_enroll.user == request.user:
                    messages.info(
                        request, "Bạn không cần tham gia đề thi do chính mình tạo."
                    )
                elif request.user in quiz_to_enroll.enrolled_users.all():
                    messages.info(
                        request,
                        f"Bạn đã tham gia đề thi '{quiz_to_enroll.quiz_name}' từ trước.",
                    )
                else:
                    # Thêm người dùng vào danh sách và báo thành công
                    quiz_to_enroll.enrolled_users.add(request.user)
                    messages.success(
                        request,
                        f"Bạn đã tham gia thành công đề thi '{quiz_to_enroll.quiz_name}'.",
                    )

            except Quiz.DoesNotExist:
                messages.error(
                    request, "Mã tham gia không hợp lệ. Vui lòng kiểm tra lại."
                )

        else:
            messages.error(request, "Vui lòng nhập một mã tham gia.")

    return redirect("quiz_list")


# --- Hàm Bắt đầu bài thi ---
@login_required
@transaction.atomic
def start_quiz(request, quiz_id):
    # Bước 1: Lấy đề thi chỉ bằng ID
    try:
        template_quiz = Quiz.objects.get(id=quiz_id, is_snapshot=False)
    except Quiz.DoesNotExist:
        raise Http404("Không tìm thấy đề thi này.")

    # === BƯỚC 2: KIỂM TRA QUYỀN TRUY CẬP MỚI ===
    # Người dùng có quyền nếu họ là chủ sở hữu HOẶC có trong danh sách tham gia
    is_owner = template_quiz.user == request.user
    is_enrolled = request.user in template_quiz.enrolled_users.all()

    if not (is_owner or is_enrolled):
        # Nếu không có cả hai quyền trên, báo lỗi cấm truy cập
        raise PermissionDenied("Bạn không có quyền làm bài thi này.")
    # ===============================================

    quiz_for_attempt = template_quiz
    question_ids_for_attempt = []

    if template_quiz.quiz_type == "static":
        question_ids_for_attempt = list(
            template_quiz.questions.all().values_list("id", flat=True)
        )

    elif template_quiz.quiz_type == "dynamic":
        rules = template_quiz.rules.all()
        final_question_ids = []
        for rule in rules:
            available_ids = list(
                Question.objects.filter(topic=rule.topic).values_list("id", flat=True)
            )
            count = min(rule.question_count, len(available_ids))
            if count > 0:
                final_question_ids.extend(random.sample(available_ids, count))

        if not final_question_ids:
            messages.error(
                request,
                "Đề thi động này không thể tạo vì các chủ đề đã chọn không có câu hỏi nào.",
            )
            return redirect("quiz_list")

        # Tạo snapshot
        snapshot_quiz = Quiz.objects.create(
            user=request.user,
            quiz_name=f"{template_quiz.quiz_name} - Lượt thi lúc {timezone.now().strftime('%H:%M %d/%m')}",
            quiz_type="static",
            time_limit_minutes=template_quiz.time_limit_minutes,
            scoring_scale_max=template_quiz.scoring_scale_max,
            is_snapshot=True,
            template_for=template_quiz,
        )
        snapshot_quiz.questions.set(final_question_ids)

        quiz_for_attempt = snapshot_quiz
        question_ids_for_attempt = final_question_ids

    # Xáo trộn và tạo lượt làm bài
    random.shuffle(question_ids_for_attempt)

    new_attempt = UserAttempt.objects.create(
        user=request.user,
        quiz=quiz_for_attempt,
        question_order=json.dumps(question_ids_for_attempt),
    )

    return redirect("take_quiz", attempt_id=new_attempt.id)


# --- Hàm hiện trang làm bài thi ---
@transaction.atomic
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(UserAttempt, id=attempt_id)
    # KIỂM TRA QUYỀN TRUY CẬP MỚI
    # Hoặc là chủ sở hữu, hoặc là khách đang làm đúng bài của mình
    is_owner = request.user.is_authenticated and attempt.user == request.user
    is_guest_on_this_attempt = (
        not request.user.is_authenticated
        and request.session.get("guest_attempt_id") == attempt.id
    )
    if not (is_owner or is_guest_on_this_attempt):
        raise PermissionDenied("Bạn không có quyền truy cập vào bài thi này.")
    quiz = attempt.quiz

    if attempt.end_time:
        return redirect("attempt_result", attempt_id=attempt.id)

    # === BẮT ĐẦU LOGIC MỚI: TÍNH TOÁN THỜI GIAN PHÍA SERVER ===
    expiration_time = attempt.start_time + timedelta(minutes=quiz.time_limit_minutes)
    remaining_seconds = int((expiration_time - timezone.now()).total_seconds())

    # Nếu hết giờ, tự động nộp bài
    if remaining_seconds <= 0:
        # (Bạn có thể sao chép logic chấm điểm từ khối POST vào đây để xử lý
        # các câu đã trả lời trước khi hết giờ, hoặc đơn giản là cho 0 điểm)
        attempt.score_achieved = 0  # Hoặc tính điểm các câu đã làm
        attempt.end_time = expiration_time
        attempt.save()
        messages.warning(
            request, "Đã hết thời gian làm bài. Bài của bạn đã được tự động nộp."
        )
        return redirect("attempt_result", attempt_id=attempt.id)
    # === KẾT THÚC LOGIC MỚI ===

    # === LOGIC MỚI: LẤY CÂU HỎI THEO THỨ TỰ ĐÃ LƯU ===
    ordered_ids = json.loads(attempt.question_order)
    # Xây dựng một truy vấn để sắp xếp các câu hỏi theo đúng thứ tự trong list ordered_ids
    preserved_order = Case(
        *[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)]
    )
    # Lấy các câu hỏi và sắp xếp chúng
    ordered_questions = Question.objects.filter(pk__in=ordered_ids).order_by(
        preserved_order
    )
    # === KẾT THÚC LOGIC MỚI ===

    if request.method == "POST":
        total_score = 0
        # Lưu ý: quiz.questions.count() vẫn đúng vì số lượng không đổi
        points_per_question = quiz.scoring_scale_max / quiz.questions.count()
        for question in quiz.questions.all():
            correct_answer_ids = set(
                question.answers.filter(is_correct=True).values_list("id", flat=True)
            )
            user_selected_ids_str = request.POST.getlist(f"question_{question.id}")
            user_selected_ids = {int(sid) for sid in user_selected_ids_str}
            is_correct = user_selected_ids == correct_answer_ids
            points_earned = points_per_question if is_correct else 0
            total_score += points_earned
            attempt_answer = AttemptAnswer.objects.create(
                attempt=attempt,
                question=question,
                is_correct=is_correct,
                points_earned=points_earned,
            )
            attempt_answer.selected_answers.set(user_selected_ids)
        attempt.score_achieved = round(total_score, 2)
        attempt.end_time = timezone.now()
        attempt.save()
        return redirect("attempt_result", attempt_id=attempt.id)

    context = {
        "attempt": attempt,
        "quiz": attempt.quiz,
        "ordered_questions": ordered_questions,  # <-- Đổi tên biến context
        "remaining_seconds": remaining_seconds,
    }
    return render(request, "quiz_app/take_quiz.html", context)


# --- Hàm thông báo kết quả bài thi ---
def attempt_result(request, attempt_id):
    try:
        attempt = (
            UserAttempt.objects.select_related("quiz", "quiz__template_for", "user")
            .prefetch_related(
                "answered_questions__question__answers",
                "answered_questions__selected_answers",
            )
            .get(id=attempt_id)
        )
    except UserAttempt.DoesNotExist:
        raise Http404("Không tìm thấy lượt làm bài này.")

    # === LOGIC KIỂM TRA QUYỀN TRUY CẬP TƯƠNG TỰ TAKE_QUIZ ===
    is_owner = request.user.is_authenticated and attempt.user == request.user
    is_valid_guest = (
        not request.user.is_authenticated
        and request.session.get("guest_attempt_id") == attempt.id
    )

    # Chỉ Creator của đề thi gốc mới có quyền xem kết quả của người khác
    is_quiz_creator = False
    if request.user.is_authenticated and attempt.quiz:
        quiz_owner = (
            attempt.quiz.template_for.user
            if attempt.quiz.is_snapshot
            else attempt.quiz.user
        )
        if request.user == quiz_owner:
            is_quiz_creator = True

    if not (is_owner or is_valid_guest or is_quiz_creator):
        raise PermissionDenied("Bạn không có quyền xem kết quả của bài thi này.")
    # ==========================================================

    # === BẮT ĐẦU PHẦN LOGIC SẮP XẾP ===
    # 1. Lấy lại thứ tự ID câu hỏi đã được lưu
    ordered_ids = json.loads(attempt.question_order)
    # 2. Tạo một biểu thức Case...When để sắp xếp các câu trả lời theo `question_id`
    preserved_order = Case(
        *[When(question_id=pk, then=pos) for pos, pk in enumerate(ordered_ids)]
    )
    # 3. Lấy queryset các câu trả lời và sắp xếp nó
    ordered_answered_questions = attempt.answered_questions.all().order_by(
        preserved_order
    )
    # === KẾT THÚC PHẦN SỬA ĐỔI LOGIC SẮP XẾP ===
    homepage_url = request.build_absolute_uri(reverse('guest_homepage'))

    share_quiz_name = attempt.quiz.quiz_name
    if attempt.quiz.is_snapshot and attempt.quiz.template_for:
        share_quiz_name = attempt.quiz.template_for.quiz_name

    share_access_code = None
    if attempt.quiz.is_snapshot and attempt.quiz.template_for:
        share_access_code = attempt.quiz.template_for.access_code
    elif not attempt.quiz.is_snapshot:
        share_access_code = attempt.quiz.access_code

    context = {
        "attempt": attempt,
        "ordered_answered_questions": ordered_answered_questions,
        "homepage_url": homepage_url,
        "share_quiz_name": share_quiz_name,
        "share_access_code": share_access_code,
    }
    return render(request, "quiz_app/attempt_result.html", context)


# --- Hàm Lịch sử làm bài thi ---
@login_required
def history_list(request):
    # Lấy tất cả các lượt làm bài của người dùng
    all_attempts = (
        UserAttempt.objects.filter(user=request.user, end_time__isnull=False)
        .select_related("quiz", "quiz__template_for")
        .order_by("-start_time")
    )

    # Logic phân trang (giữ nguyên)
    paginator = Paginator(all_attempts, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Kiểm tra nếu là yêu cầu AJAX
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if is_ajax:
        attempts_data = []
        for attempt in page_obj.object_list:
            display_name = ""
            scoring_scale = 100
            if attempt.quiz:  # Nếu quiz chưa bị xóa
                # Nếu đây là một bản snapshot, lấy tên của template gốc
                if attempt.quiz.is_snapshot and attempt.quiz.template_for:
                    display_name = attempt.quiz.template_for.quiz_name
                    scoring_scale = attempt.quiz.template_for.scoring_scale_max
                else:  # Nếu không, lấy tên của chính nó
                    display_name = attempt.quiz.quiz_name
                    scoring_scale = attempt.quiz.scoring_scale_max
            else:
                display_name = "Đề thi đã bị xóa"

            attempts_data.append(
                {
                    "id": attempt.id,
                    "quiz_name": display_name,  # <-- Sử dụng tên hiển thị đúng
                    "start_time": attempt.start_time.isoformat(),
                    "duration": attempt.duration,
                    "score_achieved": attempt.score_achieved,
                    "scoring_scale_max": scoring_scale,  # <-- Sử dụng thang điểm đúng
                }
            )

        return JsonResponse(
            {
                "attempts": attempts_data,
                "has_previous": page_obj.has_previous(),
                "previous_page_number": (
                    page_obj.previous_page_number() if page_obj.has_previous() else None
                ),
                "has_next": page_obj.has_next(),
                "next_page_number": (
                    page_obj.next_page_number() if page_obj.has_next() else None
                ),
                "current_page": page_obj.number,
                "total_pages": page_obj.paginator.num_pages,
            }
        )

    # Nếu là yêu cầu thông thường, render trang HTML
    context = {"page_obj": page_obj}
    return render(request, "quiz_app/history_list.html", context)


# --- Xóa Lịch sử làm bài ---


@login_required
def delete_attempt_view(request, attempt_id):
    """
    View để xử lý việc xóa một lượt làm bài (UserAttempt).
    Chỉ chấp nhận yêu cầu POST.
    """
    if request.method == "POST":
        # Tìm đúng lượt làm bài và đảm bảo nó thuộc về người dùng đang đăng nhập
        attempt = get_object_or_404(UserAttempt, id=attempt_id, user=request.user)

        # Xóa đối tượng
        attempt.delete()

        # Trả về tín hiệu thành công
        return JsonResponse(
            {"success": True, "message": "Đã xóa lượt làm bài thành công."}
        )

    # Nếu không phải là POST, trả về lỗi
    return JsonResponse(
        {"success": False, "message": "Yêu cầu không hợp lệ."}, status=400
    )


# --- Hàm helper để xử lý logic file Excel ---


def _handle_excel_import(uploaded_file, target_topic):
    """
    Hàm xử lý file excel được tải lên.
    Hàm này giờ sẽ gọi hàm helper chung.
    """
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        return (
            False,
            f"Lỗi không thể đọc file Excel. Đảm bảo file đúng định dạng. Lỗi: {e}",
        )

    target_topic_name = target_topic.topic_name
    if target_topic_name not in xls.sheet_names:
        return (
            False,
            f"Không tìm thấy sheet nào có tên '{target_topic_name}' trong file Excel. Vui lòng kiểm tra lại.",
        )

    df = xls.parse(target_topic_name)
    # GỌI HÀM HELPER MỚI ĐỂ THỰC HIỆN TOÀN BỘ LOGIC XỬ LÝ
    questions_added_count = _process_question_dataframe(df, target_topic)

    if questions_added_count > 0:
        return (
            True,
            f"Nhập thành công! Đã thêm {questions_added_count} câu hỏi vào chủ đề '{target_topic_name}'.",
        )
    else:
        return (
            True,
            f"Sheet '{target_topic_name}' không có dữ liệu hoặc không có câu hỏi hợp lệ. Không có câu hỏi nào được thêm.",
        )


# --- Hàm import ---
@login_required
@permission_required("quiz_app.add_question", raise_exception=True)
@transaction.atomic
def import_questions_to_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES["file"]
            success, message = _handle_excel_import(uploaded_file, topic)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect("question_list_in_topic", topic_id=topic.id)
    else:
        form = UploadFileForm()

    context = {"form": form, "topic": topic}
    return render(request, "quiz_app/import_form.html", context)


# --- Hàm export ---
@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def export_questions_from_topic(request, topic_id):
    """
    Xuất tất cả các câu hỏi và câu trả lời của một chủ đề cụ thể ra file Excel.
    """
    topic = get_object_or_404(Topic, id=topic_id, user=request.user)
    questions = Question.objects.filter(topic=topic).prefetch_related("answers")

    if not questions.exists():
        messages.warning(
            request, f"Chủ đề '{topic.topic_name}' không có câu hỏi nào để xuất."
        )
        return redirect("question_list_in_topic", topic_id=topic.id)

    data_for_excel = []
    for q_idx, question in enumerate(questions):
        # BỎ CỘT 'Mức độ khó'
        data_for_excel.append(
            {
                "Nội dung": question.question_text,
                "Đáp án đúng?": "",
                "Đường dẫn ảnh": "",
            }
        )

        for answer in question.answers.all():
            # BỎ CỘT 'Mức độ khó'
            data_for_excel.append(
                {
                    "Nội dung": answer.answer_text,
                    "Đáp án đúng?": "X" if answer.is_correct else "",
                    "Đường dẫn ảnh": "",
                }
            )

        if q_idx < questions.count() - 1:
            # BỎ CỘT 'Mức độ khó'
            data_for_excel.append(
                {"Nội dung": "", "Đáp án đúng?": "", "Đường dẫn ảnh": ""}
            )

    # DataFrame bây giờ sẽ chỉ có 3 cột
    df = pd.DataFrame(data_for_excel)

    output = BytesIO()
    # Chỉ định các cột cần xuất để đảm bảo đúng thứ tự
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            sheet_name=topic.topic_name,
            index=False,
            columns=["Nội dung", "Đáp án đúng?", "Đường dẫn ảnh"],
        )

    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{topic.topic_name}.xlsx"'

    return response


# --- Xuất Nhóm chủ đề ---
# VIEW 1: HIỂN THỊ TRANG LỰA CHỌN FILE ĐỂ XUẤT


@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def export_all_select_view(request):
    # Lấy tất cả các nhóm chủ đề của người dùng mà có chứa ít nhất một chủ đề
    groups = TopicGroup.objects.filter(
        user=request.user, topic__isnull=False
    ).distinct()

    context = {"topic_groups": groups}
    return render(request, "quiz_app/export_select.html", context)


# VIEW 2: XỬ LÝ VIỆC TẠO VÀ TRẢ VỀ FILE EXCEL CHO MỘT NHÓM
@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def export_topic_group_view(request, group_id):
    group = get_object_or_404(TopicGroup, id=group_id, user=request.user)

    # Lấy tất cả các chủ đề thuộc nhóm này
    topics_in_group = group.topic_set.all()

    # Tạo file Excel trong bộ nhớ
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Lặp qua từng chủ đề và tạo một sheet cho mỗi chủ đề
        for topic in topics_in_group:
            questions = Question.objects.filter(topic=topic).prefetch_related("answers")

            if not questions.exists():
                continue  # Bỏ qua nếu chủ đề không có câu hỏi

            data_for_sheet = []
            for q_idx, question in enumerate(questions):
                data_for_sheet.append(
                    {
                        "Nội dung": question.question_text,
                        "Đáp án đúng?": "",
                        "Đường dẫn ảnh": "",
                    }
                )
                for answer in question.answers.all():
                    data_for_sheet.append(
                        {
                            "Nội dung": answer.answer_text,
                            "Đáp án đúng?": "X" if answer.is_correct else "",
                            "Đường dẫn ảnh": "",
                        }
                    )
                if q_idx < questions.count() - 1:
                    data_for_sheet.append(
                        {"Nội dung": "", "Đáp án đúng?": "", "Đường dẫn ảnh": ""}
                    )

            df_sheet = pd.DataFrame(data_for_sheet)
            df_sheet.to_excel(
                writer,
                sheet_name=topic.topic_name,
                index=False,
                columns=["Nội dung", "Đáp án đúng?", "Đường dẫn ảnh"],
            )

    output.seek(0)

    # Trả về response để tải file
    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{group.group_name}.xlsx"'
    return response


# --- Hàm helper cho việc Import Toàn Bộ ---


def _handle_global_excel_import(uploaded_file, user):
    """
    Hàm xử lý file excel được tải lên cho chức năng Import Toàn Bộ.
    Hàm này giờ sẽ gọi hàm helper chung.
    """
    try:
        file_name_without_ext = os.path.splitext(uploaded_file.name)[0]
        group_name = file_name_without_ext.strip()
        topic_group, created = TopicGroup.objects.get_or_create(
            user=user,
            group_name=group_name,
            defaults={
                "group_description": f"Nhóm được nhập từ file {uploaded_file.name}"
            },
        )
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        return (False, f"Lỗi không thể đọc file hoặc tên file. Lỗi: {e}")

    total_questions_added = 0
    # Lặp qua từng sheet trong file
    for sheet_name in xls.sheet_names:
        topic_name = sheet_name.strip()
        if not topic_name:
            continue  # Bỏ qua các sheet không có tên

        # Lấy hoặc tạo Topic trong TopicGroup vừa có
        topic, created = Topic.objects.get_or_create(
            user=user, topic_name=topic_name, group=topic_group
        )

        # Đọc dữ liệu từ sheet
        df = xls.parse(sheet_name)
        # GỌI HÀM HELPER MỚI CHO TỪNG SHEET
        questions_added = _process_question_dataframe(df, topic)
        total_questions_added += questions_added

    return (True, f"Nhập toàn bộ thành công! Đã thêm {total_questions_added} câu hỏi.")


# --- View cho việc Import Toàn Bộ ---


@login_required
@permission_required("quiz_app.add_question", raise_exception=True)
@transaction.atomic
def import_all_data_view(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES["file"]
            success, message = _handle_global_excel_import(uploaded_file, request.user)

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

            # Chuyển về trang Bảng điều khiển
            return redirect("topic_group_list")
    else:
        form = UploadFileForm()

    context = {
        "form": form,
        # 'topic' sẽ là None, chúng ta sẽ xử lý trong template
    }
    return render(request, "quiz_app/import_form.html", context)


# --- Tìm kiếm ---


@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def question_search_view(request):
    # Bắt đầu với một queryset rỗng
    question_list = Question.objects.none()
    form = QuestionSearchForm(request.GET, user=request.user)

    # Chỉ thực hiện tìm kiếm NẾU có dữ liệu được gửi lên (người dùng đã bấm nút tìm)
    # request.GET sẽ chứa dữ liệu khi form được submit bằng phương thức GET
    if request.GET:
        if form.is_valid():
            # Bắt đầu truy vấn từ tất cả câu hỏi của người dùng
            question_list = Question.objects.filter(
                topic__user=request.user
            ).select_related("topic", "topic__group")

            keyword = form.cleaned_data.get("keyword")
            topic_group = form.cleaned_data.get("topic_group")
            topic = form.cleaned_data.get("topic")
            question_type = form.cleaned_data.get("question_type")

            if keyword:
                question_list = question_list.filter(question_text__icontains=keyword)
            if topic_group:
                question_list = question_list.filter(topic__group=topic_group)
            if topic:
                question_list = question_list.filter(topic=topic)
            if question_type:
                question_list = question_list.filter(question_type=question_type)

            # Sắp xếp kết quả
            question_list = question_list.order_by("-id")

    paginator = Paginator(question_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]

    context = {
        "form": form,
        "page_obj": page_obj,
        "query_params": query_params.urlencode(),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "quiz_app/_question_search_results.html", context)

    return render(request, "quiz_app/question_search.html", context)


# --- Lấy danh sách chủ đề cho Nhóm chủ đề trong Tìm kiếm ---


@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def get_topics_for_group_view(request):
    """
    Một API view để lấy danh sách các chủ đề (Topic)
    dựa trên group_id được gửi lên.
    """
    group_id = request.GET.get("group_id")

    # Nếu không có group_id, trả về một danh sách rỗng
    if not group_id:
        return JsonResponse({"topics": []})

    # Truy vấn các chủ đề thuộc nhóm đó VÀ của người dùng hiện tại
    try:
        topics = Topic.objects.filter(group_id=int(group_id), user=request.user).values(
            "id", "topic_name"
        )  # Chỉ lấy id và tên cho hiệu quả

        # Chuyển QuerySet thành một list để trả về JSON
        topics_list = list(topics)

        return JsonResponse({"topics": topics_list})
    except (ValueError, TypeError):
        # Xử lý trường hợp group_id không phải là số
        return JsonResponse({"topics": []})


# --- Xem nội dung câu hỏi trong kết quả Tìm kiếm ---
@login_required
@permission_required("quiz_app.view_question", raise_exception=True)
def get_question_details_view(request, question_id):
    """
    API view để trả về chi tiết của một câu hỏi, bao gồm các đáp án của nó.
    """
    try:
        # Đảm bảo câu hỏi tồn tại và thuộc về người dùng đang đăng nhập
        question = Question.objects.prefetch_related("answers").get(
            id=question_id, topic__user=request.user
        )

        # Lấy danh sách các đáp án
        answers = []
        for answer in question.answers.all():
            answers.append(
                {"text": answer.answer_text, "is_correct": answer.is_correct}
            )

        # Tạo dữ liệu để trả về
        data = {
            "success": True,
            "question_text": question.question_text,
            "answers": answers,
        }
        return JsonResponse(data)

    except Question.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Câu hỏi không tồn tại hoặc bạn không có quyền truy cập.",
            },
            status=404,
        )


# --- Đăng ký tài khoản ---
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Tự động thêm user mới vào nhóm 'Members'
            try:
                group = Group.objects.get(name="Members")
                user.groups.add(group)
            except Group.DoesNotExist:
                # Có thể thêm xử lý lỗi ở đây nếu nhóm chưa được tạo
                pass

            login(request, user)  # Tự động đăng nhập cho user sau khi đăng ký
            return redirect("dashboard")  # Chuyển hướng đến trang chủ
    else:
        form = SignUpForm()
    return render(request, "quiz_app/signup.html", {"form": form})

# --- Báo cáo kết quả tổng quát ---
@login_required
@permission_required("quiz_app.view_quiz", raise_exception=True)
def quiz_report_list_view(request):
    quizzes = (
        Quiz.objects.filter(user=request.user, is_snapshot=False)
        .annotate(
            # THAY ĐỔI: Thêm điều kiện filter vào trong Count
            # để chỉ đếm các lượt làm bài đã có end_time (đã hoàn thành)
            dynamic_attempt_count=Count(
                "snapshots__userattempt",
                filter=Q(snapshots__userattempt__end_time__isnull=False),
                distinct=True,
            ),
            static_attempt_count=Count(
                "userattempt",
                filter=Q(userattempt__end_time__isnull=False),
                distinct=True,
            ),
            dynamic_avg_score=Avg("snapshots__userattempt__score_achieved"),
            static_avg_score=Avg("userattempt__score_achieved"),
        )
        .order_by("-created_at")
    )

    for quiz in quizzes:
        if quiz.quiz_type == "static":
            quiz.total_attempts = quiz.static_attempt_count
            quiz.average_score = quiz.static_avg_score
        else:  # dynamic
            quiz.total_attempts = quiz.dynamic_attempt_count
            quiz.average_score = quiz.dynamic_avg_score

    context = {"quizzes": quizzes}
    return render(request, "quiz_app/quiz_report_list.html", context)

# --- Báo cáo kết quả chi tiết ---
@login_required
@permission_required("quiz_app.view_quiz", raise_exception=True)
def quiz_detail_report_view(request, quiz_id):
    # Lấy đề thi gốc, đảm bảo nó thuộc về người dùng
    quiz = get_object_or_404(Quiz, id=quiz_id, user=request.user, is_snapshot=False)

    # Lấy tất cả các lượt làm bài liên quan đến đề thi này (bao gồm cả các snapshot)
    attempts_filter = Q(quiz=quiz) | Q(quiz__template_for=quiz)
    attempts = (
        UserAttempt.objects.filter(attempts_filter, end_time__isnull=False)
        .select_related("user")
        .order_by("-score_achieved")
    )

    # --- CHUẨN BỊ DỮ LIỆU CHO BIỂU ĐỒ (PHIÊN BẢN TỐI ƯU HƠN) ---
    # Định nghĩa các nhãn và khởi tạo dữ liệu
    chart_labels = [
        "0-10%",
        "11-20%",
        "21-30%",
        "31-40%",
        "41-50%",
        "51-60%",
        "61-70%",
        "71-80%",
        "81-90%",
        "91-100%",
    ]
    # Khởi tạo một danh sách 10 số 0, tương ứng với 10 nhãn
    chart_data = [0] * 10

    for attempt in attempts:
        if attempt.quiz and attempt.quiz.scoring_scale_max > 0:
            percentage_score = (
                attempt.score_achieved / attempt.quiz.scoring_scale_max
            ) * 100
        else:
            percentage_score = 0

        # Dùng công thức toán học để xác định vị trí của điểm số trong các "rổ"
        if percentage_score == 0:
            bin_index = 0
        else:
            bin_index = math.ceil(percentage_score / 10) - 1
            bin_index = max(0, bin_index)

        # Tăng số đếm cho "rổ" tương ứng
        if bin_index < len(chart_data):
            chart_data[bin_index] += 1
    # --- KẾT THÚC CHUẨN BỊ DỮ LIỆU BIỂU ĐỒ ---

    context = {
        "quiz": quiz,
        "attempts": attempts,
        # Chuyển dữ liệu biểu đồ sang template dưới dạng chuỗi JSON an toàn
        "chart_labels": json.dumps(chart_labels),
        "chart_data": json.dumps(chart_data),
    }
    return render(request, "quiz_app/quiz_detail_report.html", context)

# --- Trang Khách ---
def guest_homepage_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == 'POST':
        login_form = CustomAuthenticationForm(request, data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        login_form = CustomAuthenticationForm

    # Lấy dữ liệu cho trang (giữ nguyên)
    public_quizzes = Quiz.objects.filter(is_public=True, is_snapshot=False).annotate(
        question_count=Count('questions')
    ).order_by('-created_at')[:4]
    enroll_form = EnrollmentForm()

    context = {
        "public_quizzes": public_quizzes,
        "login_form": login_form, # form này có thể trống hoặc chứa lỗi
        "enroll_form": enroll_form,
    }
    return render(request, "quiz_app/guest_homepage.html", context)

# --- Danh sách đề thi công khai ---
def public_quiz_list_view(request):
    # Lấy tất cả các đề thi được đánh dấu công khai và không phải là bản snapshot
    public_quizzes_list = Quiz.objects.filter(is_public=True, is_snapshot=False).annotate(
        question_count=Count('questions')
    ).order_by('-created_at')

    # Phân trang, hiển thị 10 đề thi mỗi trang
    paginator = Paginator(public_quizzes_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Lấy form nhập mã để hiển thị (tùy chọn, nhưng tiện lợi cho người dùng)
    enrollment_form = EnrollmentForm()

    context = {
        'page_obj': page_obj,
        'enrollment_form': enrollment_form,
    }
    return render(request, 'quiz_app/public_quiz_list.html', context)

# --- Bài thi của Khách ---
@transaction.atomic
def guest_start_quiz(request):
    if request.method != "POST":
        return redirect("guest_homepage")

    quiz_id = request.POST.get("quiz_id")
    access_code = request.POST.get("access_code")
    guest_name = request.POST.get("guest_name", "Khách").strip()

    if not guest_name:
        messages.error(request, "Vui lòng nhập tên của bạn.")
        return redirect("guest_homepage")

    template_quiz = None

    # Tìm đề thi dựa trên ID (từ modal) hoặc mã truy cập (từ form)
    if quiz_id:
        try:
            template_quiz = Quiz.objects.get(
                id=quiz_id, is_public=True, is_snapshot=False
            )
        except Quiz.DoesNotExist:
            raise Http404("Không tìm thấy đề thi công khai này.")
    elif access_code:
        try:
            template_quiz = Quiz.objects.get(
                access_code=access_code.upper(), is_snapshot=False
            )
        except Quiz.DoesNotExist:
            messages.error(request, "Mã tham gia không hợp lệ. Vui lòng kiểm tra lại.")
            return redirect("guest_homepage")
    else:
        messages.error(request, "Không có thông tin đề thi. Vui lòng thử lại.")
        return redirect("guest_homepage")

    # ------ Bắt đầu logic tạo snapshot (tương tự view start_quiz) ------
    quiz_for_attempt = template_quiz
    question_ids_for_attempt = []

    if template_quiz.quiz_type == "static":
        question_ids_for_attempt = list(
            template_quiz.questions.all().values_list("id", flat=True)
        )

    elif template_quiz.quiz_type == "dynamic":
        rules = template_quiz.rules.all()
        final_question_ids = []
        for rule in rules:
            available_ids = list(
                Question.objects.filter(topic=rule.topic).values_list("id", flat=True)
            )
            count = min(rule.question_count, len(available_ids))
            if count > 0:
                final_question_ids.extend(random.sample(available_ids, count))

        if not final_question_ids:
            messages.error(
                request,
                "Đề thi này hiện không có câu hỏi để làm bài. Vui lòng thử lại sau.",
            )
            return redirect("guest_homepage")

        # Tạo snapshot
        snapshot_quiz = Quiz.objects.create(
            user=template_quiz.user,  # Snapshot vẫn thuộc về Creator
            quiz_name=f"{template_quiz.quiz_name} - Lượt thi của khách",
            quiz_type="static",
            time_limit_minutes=template_quiz.time_limit_minutes,
            scoring_scale_max=template_quiz.scoring_scale_max,
            is_snapshot=True,
            template_for=template_quiz,
        )
        snapshot_quiz.questions.set(final_question_ids)

        quiz_for_attempt = snapshot_quiz
        question_ids_for_attempt = final_question_ids
    # ------ Kết thúc logic tạo snapshot ------

    # Xáo trộn thứ tự câu hỏi
    random.shuffle(question_ids_for_attempt)

    # Tạo một lượt làm bài mới với user=None và có guest_name
    new_attempt = UserAttempt.objects.create(
        user=None,
        guest_name=guest_name,
        quiz=quiz_for_attempt,
        question_order=json.dumps(question_ids_for_attempt),
    )

    # Lưu attempt_id của khách vào session để xác thực ở trang làm bài
    request.session["guest_attempt_id"] = new_attempt.id

    # Chuyển hướng đến trang làm bài
    return redirect("take_quiz", attempt_id=new_attempt.id)

# --- Yêu cầu đăng nhập ---
def ajax_login_view(request):
    """
    Xử lý yêu cầu đăng nhập từ HTMX.
    - Nếu thành công: Trả về một response đặc biệt để HTMX tự chuyển hướng trang.
    - Nếu thất bại: Render lại chỉ form đăng nhập với lỗi và trả về.
    """
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Tạo một response trống và đặt header HX-Redirect
            # HTMX sẽ nhận diện header này và tự động chuyển hướng đến dashboard
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('dashboard')
            return response
        else:
            # Nếu form không hợp lệ, render lại chỉ phần form với các lỗi
            # và trả về cho HTMX để thay thế vào trang
            return render(request, 'quiz_app/_login_form.html', {'login_form': form})
    # Trả về lỗi nếu không phải là POST request
    return HttpResponse("Yêu cầu không hợp lệ", status=400)
