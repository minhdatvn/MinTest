from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class GuestHomepageTests(TestCase):
    def test_homepage_loads_correctly(self):
        url = reverse('guest_homepage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz_app/guest_homepage.html')

# Đặt tên cho nhóm các bài test liên quan đến trang Dashboard
class DashboardViewTests(TestCase):
    
    def setUp(self):
        """
        Tạo một user và mật khẩu để dùng cho các bài test cần đăng nhập.
        """
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.dashboard_url = reverse('dashboard')
        self.login_url = reverse('login')

    def test_guest_user_is_redirected_to_login(self):
        """
        Kiểm tra người dùng chưa đăng nhập bị chuyển hướng tới trang login.
        """
        # Gửi yêu cầu GET đến dashboard mà không đăng nhập
        response = self.client.get(self.dashboard_url)
        
        # 1. Khẳng định rằng server trả về status code 302 (Found/Redirect)
        self.assertEqual(response.status_code, 302)
        
        # 2. Khẳng định rằng nó chuyển hướng đúng đến trang đăng nhập
        #    với tham số 'next' trỏ về trang dashboard.
        expected_redirect_url = f'{self.login_url}?next={self.dashboard_url}'
        self.assertRedirects(response, expected_redirect_url)

    def test_logged_in_user_can_access_dashboard(self):
        """
        Kiểm tra người dùng đã đăng nhập có thể truy cập dashboard thành công.
        """
        # 1. Giả lập việc đăng nhập bằng thông tin đã tạo trong setUp
        self.client.login(username='testuser', password='password123')
        
        # 2. Gửi yêu cầu GET đến dashboard
        response = self.client.get(self.dashboard_url)
        
        # 3. Khẳng định rằng trang tải thành công (status code 200)
        self.assertEqual(response.status_code, 200)
        
        # 4. Khẳng định rằng trang sử dụng đúng template
        self.assertTemplateUsed(response, 'quiz_app/dashboard.html')
        
        # 5. (Nâng cao) Khẳng định rằng trang có chứa một nội dung cụ thể,
        #    ví dụ như lời chào mừng đúng tên người dùng.
        self.assertContains(response, f"Chào mừng, {self.user.username}!")
