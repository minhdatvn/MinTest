# quiz_project/quiz_app/forms.py

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.contrib.auth.forms import UserCreationForm, User, AuthenticationForm
from .models import TopicGroup, Topic, Question, Answer, Quiz

# --- Form Tìm kiếm ---
class QuestionSearchForm(forms.Form):
    # Ô nhập từ khóa, không bắt buộc
    keyword = forms.CharField(
        label="Từ khóa",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập nội dung câu hỏi...'})
    )

    # Danh sách chọn Nhóm chủ đề, không bắt buộc
    topic_group = forms.ModelChoiceField(
        label="Trong Nhóm chủ đề",
        queryset=TopicGroup.objects.none(), # Sẽ được cập nhật trong __init__
        required=False,
        empty_label="Tất cả các Nhóm", # Hiển thị khi không chọn gì
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Danh sách chọn Chủ đề, không bắt buộc
    topic = forms.ModelChoiceField(
        label="Trong Chủ đề",
        queryset=Topic.objects.none(), # Sẽ được cập nhật trong __init__
        required=False,
        empty_label="Tất cả các Chủ đề",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Lựa chọn loại câu hỏi, không bắt buộc
    question_type = forms.ChoiceField(
        label="Loại câu hỏi",
        choices=[('', 'Tất cả các loại')] + Question.QUESTION_TYPE_CHOICES, # Thêm lựa chọn "Tất cả"
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        # Lấy 'user' từ view truyền vào để lọc queryset
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Chỉ hiển thị các nhóm và chủ đề của người dùng đã đăng nhập
            self.fields['topic_group'].queryset = TopicGroup.objects.filter(user=user)
            self.fields['topic'].queryset = Topic.objects.filter(user=user)

# --- Form Nhóm chủ đề ---
class TopicGroupForm(forms.ModelForm):
    class Meta:
        # Cho Django biết form này được tạo ra cho model nào
        model = TopicGroup

        # Chỉ định những trường nào từ model sẽ được hiển thị trong form
        # Chúng ta không đưa trường 'user' vào đây vì nó sẽ được gán tự động
        # dựa trên người dùng đã đăng nhập.
        fields = ['group_name', 'group_description']

        # Tùy chỉnh nhãn hiển thị cho thân thiện hơn
        labels = {
            'group_name': 'Tên Nhóm chủ đề',
            'group_description': 'Mô tả (tùy chọn)',
        }

# --- Form Chủ đề ---
class TopicForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=TopicGroup.objects.none(),
        required=False,
        label="Thuộc Nhóm chủ đề"
    )

    class Meta:
        model = Topic
        fields = ['group', 'topic_name', 'description']
        labels = {
            'topic_name': 'Tên Chủ đề',
            'description': 'Mô tả (tùy chọn)',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        # --- DÒNG MỚI ---
        # Lưu user vào đối tượng form để có thể dùng trong các phương thức khác
        self.user = user 
        # --- KẾT THÚC DÒNG MỚI ---

        super().__init__(*args, **kwargs)

        if user:
            self.fields['group'].queryset = TopicGroup.objects.filter(user=user)

    # --- PHƯƠNG THỨC MỚI ĐỂ VALIDATE ---
    def clean(self):
        # Lấy dữ liệu đã được làm sạch bởi các bước validation mặc định
        cleaned_data = super().clean()
        topic_name = cleaned_data.get('topic_name')

        # Nếu tên chủ đề và user tồn tại, hãy kiểm tra
        if topic_name and self.user:
            # Kiểm tra xem có chủ đề nào của user này với tên y hệt (không phân biệt hoa thường) đã tồn tại chưa
            # Chúng ta loại trừ trường hợp đang chỉnh sửa chính nó
            query = Topic.objects.filter(user=self.user, topic_name__iexact=topic_name)
            if self.instance.pk: # Nếu đây là form chỉnh sửa (instance đã có primary key)
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                # Nếu tồn tại, tạo ra một lỗi validation
                raise forms.ValidationError(
                    "Bạn đã có một chủ đề với tên này. Vui lòng chọn một tên khác."
                )

        return cleaned_data
    # --- KẾT THÚC PHƯƠNG THỨC MỚI ---

# --- Form cho Thêm mới, chỉnh sửa câu hỏi ---
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'question_image']
        labels = {
            'question_text': 'Nội dung câu hỏi',
            'question_image': 'Ảnh cho câu hỏi (tùy chọn)',
        }
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'question_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

# LỚP MỚI: Chứa logic validation chung cho các formset đáp án
class BaseAnswerFormSet(BaseInlineFormSet):
    def clean(self):
        # Chạy hàm clean của lớp cha trước
        super().clean()

        # Đếm số đáp án hợp lệ và số đáp án đúng
        total_answers = 0
        correct_answers = 0
        for form in self.forms:
            # Bỏ qua các form trống hoặc các form được đánh dấu xóa
            if not form.is_valid() or not form.cleaned_data or form.cleaned_data.get('DELETE', False):
                continue

            total_answers += 1
            if form.cleaned_data.get('is_correct', False):
                correct_answers += 1

        # Kiểm tra các quy tắc
        if total_answers < 2:
            raise forms.ValidationError('Một câu hỏi phải có ít nhất 2 đáp án.')

        if correct_answers == 0:
            raise forms.ValidationError('Bạn phải chọn ít nhất một đáp án đúng cho câu hỏi.')

class BaseAnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['answer_text', 'answer_image', 'is_correct']

    def clean(self):
        # Lấy prefix của form để biết nó là form-0, form-1, v.v.
        form_prefix = self.prefix
        # Chạy clean của lớp cha trước để Django thực hiện validation cơ bản
        cleaned_data = super().clean()
        # Kiểm tra xem cờ DELETE có được check hay không
        is_marked_for_delete = self.data.get(f'{form_prefix}-DELETE')
        # Nếu form được đánh dấu xóa VÀ có lỗi (chứng tỏ nó bị rỗng)
        if is_marked_for_delete and self.errors:
            self.errors.clear()
            # Gọi lại super().clean() là cần thiết để làm mới cleaned_data sau khi xóa lỗi
            cleaned_data = super().clean()
        
        return cleaned_data

# FormSet cho việc TẠO câu hỏi
CreateAnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    form=BaseAnswerForm,
    formset=BaseAnswerFormSet,
    fields=('answer_text', 'answer_image', 'is_correct'),
    labels={
        'answer_text': 'Nội dung đáp án',
        'answer_image': 'Ảnh đáp án (tùy chọn)',
        'is_correct': 'Đây là đáp án đúng',
    },
    widgets={
        'answer_text': forms.TextInput(attrs={'class': 'form-control'}),
        'answer_image': forms.FileInput(attrs={'class': 'form-control'}),
        'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    },
    extra=2, # Số form trống khi TẠO MỚI
    max_num=7,
    can_delete=False # Không thể xóa form chưa được lưu
)

# FormSet cho việc SỬA câu hỏi
EditAnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    form=BaseAnswerForm,
    formset=BaseAnswerFormSet,
    fields=('answer_text', 'answer_image', 'is_correct'),
    labels={
        'answer_text': 'Nội dung đáp án',
        'answer_image': 'Ảnh đáp án (tùy chọn)',
        'is_correct': 'Đây là đáp án đúng',
    },
    widgets={
        'answer_text': forms.TextInput(attrs={'class': 'form-control'}),
        'answer_image': forms.FileInput(attrs={'class': 'form-control'}),
        'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    },
    extra=0, # KHÔNG có form trống khi SỬA
    max_num=7,
    can_delete=True # Cho phép xóa các đáp án hiện có
)

# --- Form Tạo đề thi để lưu vào Danh sách đề thi ---
class QuizForm(forms.ModelForm):
    # Định nghĩa trường 'questions' một cách tường minh để dùng Checkbox
    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.none(), 
        widget=forms.CheckboxSelectMultiple,
        label="Chọn các câu hỏi cho đề thi",
        required=False  # << THAY ĐỔI 1: Không còn bắt buộc
    )

    class Meta:
        model = Quiz
        fields = ['quiz_name', 'quiz_type', 'time_limit_minutes', 'scoring_scale_max', 'questions']
        labels = {
            'quiz_name': 'Tên Đề thi',
            'quiz_type': 'Loại Đề thi', # << THÊM MỚI
            'time_limit_minutes': 'Thời gian làm bài (phút)',
            'scoring_scale_max': 'Thang điểm',
        }
        widgets = {
            'quiz_type': forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Lọc danh sách câu hỏi cho phần Đề thi tĩnh
            self.fields['questions'].queryset = Question.objects.filter(topic__user=user).select_related('topic__group')

            # Tự động tạo các trường cho phần Đề thi động
            all_topics = Topic.objects.filter(user=user)
            for topic in all_topics:
                field_name = f'dynamic_topic_{topic.id}'
                self.fields[field_name] = forms.IntegerField(
                    label=f"Số câu hỏi cho chủ đề: '{topic.topic_name}'",
                    required=False,
                    min_value=0,
                    initial=0,
                    widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'})
                )

    # Thêm hàm clean để validate dựa trên quiz_type
    def clean(self):
        cleaned_data = super().clean()
        quiz_type = cleaned_data.get('quiz_type')

        if quiz_type == 'static':
            # Validation cho đề thi tĩnh (giữ nguyên)
            questions = cleaned_data.get('questions')
            if not questions:
                self.add_error('questions', 'Bạn phải chọn ít nhất một câu hỏi cho đề thi tĩnh.')

        elif quiz_type == 'dynamic':
            # === BẮT ĐẦU VALIDATION CHO ĐỀ THI ĐỘNG ===
            total_dynamic_questions = 0
            # Lặp qua các keys trong cleaned_data để tìm các trường của chúng ta
            for key, value in cleaned_data.items():
                if key.startswith('dynamic_topic_') and value:
                    total_dynamic_questions += value

            if total_dynamic_questions == 0:
                # Gắn lỗi này vào một trường chung, không cụ thể
                self.add_error(None, 'Bạn phải chọn ít nhất một câu hỏi từ một chủ đề cho đề thi động.')
            # === KẾT THÚC VALIDATION CHO ĐỀ THI ĐỘNG ===

        return cleaned_data

# --- Form Import ---
class UploadFileForm(forms.Form):
    file = forms.FileField(label="Chọn file Excel (.xlsx)")

# --- Form Đăng ký ---
class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

# === FORM MỚI CHO VIỆC NHẬP MÃ THAM GIA ===
class EnrollmentForm(forms.Form):
    access_code = forms.CharField(
        label="Mã tham gia",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mã...'})
    )

# --- Form Đăng nhập ---
class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Xóa thuộc tính autofocus khỏi widget của trường username một cách triệt để
        self.fields['username'].widget.attrs.pop('autofocus', None)