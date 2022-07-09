from django.test import Client, TestCase


class CorePagesTests(TestCase):
    def test_error_page(self):
        """URL-адрес использует соответствующий шаблон 404."""
        self.user_client = Client()
        response = self.user_client.get("/nonexist-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "core/404.html")
