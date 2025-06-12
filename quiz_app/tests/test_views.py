# quiz_app/tests/test_views.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from quiz_app.models import TopicGroup, Topic # Import thêm TopicGroup và Topic

# Lớp test cho trang chủ (giữ nguyên)
class GuestHomepageTests(TestCase):
    def test_homepage_loads_correctly(self):
        url = reverse('guest_homepage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz_app/guest_homepage.html')

# Lớp test cho trang Dashboard (giữ nguyên)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.dashboard_url = reverse('dashboard')
        self.login_url = reverse('login')

    def test_guest_user_is_redirected_to_login(self):
        response = self.client.get(self.dashboard_url)
        expected_redirect_url = f'{self.login_url}?next={self.dashboard_url}'
        self.assertRedirects(response, expected_redirect_url)

    def test_logged_in_user_can_access_dashboard(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz_app/dashboard.html')
        self.assertContains(response, f"Chào mừng, {self.user.username}!")

# === THÊM LỚP TEST MỚI TỪ ĐÂY ===

class TopicGroupListViewTests(TestCase):
    def setUp(self):
        # Tạo 2 user khác nhau để đảm bảo test không bị lẫn dữ liệu
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        # Tạo 2 nhóm chủ đề cho user1
        self.group1 = TopicGroup.objects.create(group_name='Toán học', user=self.user1)
        self.group2 = TopicGroup.objects.create(group_name='Vật lý', user=self.user1)

        # Tạo 1 nhóm chủ đề cho user2
        self.group3 = TopicGroup.objects.create(group_name='Hóa học', user=self.user2)

    def test_view_displays_only_logged_in_user_groups(self):
        """
        Kiểm tra trang chỉ hiển thị các nhóm chủ đề của user đã đăng nhập.
        """
        # Đăng nhập bằng user1
        self.client.login(username='user1', password='password123')

        # Truy cập trang quản lý nội dung
        response = self.client.get(reverse('topic_group_list'))

        # Khẳng định rằng trang tải thành công
        self.assertEqual(response.status_code, 200)
        
        # Khẳng định rằng template đúng được sử dụng
        self.assertTemplateUsed(response, 'quiz_app/topic_group_list.html')
        
        # Khẳng định rằng trang có chứa tên các nhóm của user1
        self.assertContains(response, 'Toán học')
        self.assertContains(response, 'Vật lý')
        
        # Khẳng định rằng trang KHÔNG chứa tên nhóm của user2
        self.assertNotContains(response, 'Hóa học')