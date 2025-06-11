from django.test import TestCase
from django.urls import reverse

class GuestHomepageTests(TestCase):
    def test_homepage_loads_correctly(self):
        url = reverse('guest_homepage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz_app/guest_homepage.html')