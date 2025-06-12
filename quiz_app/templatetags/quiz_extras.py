# quiz_app/templatetags/quiz_extras.py
# Công dụng: Thêm kí tự A,B,C... trước đáp án trong giao diện làm bài
from django import template

# Tạo một đối tượng để đăng ký các filter và tag mới của chúng ta
register = template.Library()

@register.filter(name='to_char')
def to_char(value):
    """
    Đây là hàm sẽ chuyển một số nguyên (bắt đầu từ 0) 
    thành ký tự Alphabet tương ứng (0->'A', 1->'B', ...).
    """
    try:
        # Chuyển giá trị đầu vào (có thể là chuỗi hoặc số) thành số nguyên
        numeric_value = int(value)
        
        # 65 là mã ASCII cho ký tự 'A'.
        # Nếu value = 0, chr(65 + 0) sẽ là 'A'.
        # Nếu value = 1, chr(65 + 1) sẽ là 'B'.
        return chr(65 + numeric_value)
    except (ValueError, TypeError):
        # Nếu giá trị đầu vào không hợp lệ (ví dụ: một chuỗi text),
        # trả về một chuỗi rỗng để tránh gây lỗi trang web.
        return ''

@register.filter(name='percentage')
def percentage(value, max_value):
    """
    Chuyển đổi điểm số thành phần trăm.
    Ví dụ: {{ 80|percentage:100 }} -> 80.0
    """
    try:
        score = float(value)
        max_score = float(max_value)
        if max_score == 0:
            return 0
        return (score / max_score) * 100
    except (ValueError, TypeError):
        return 0