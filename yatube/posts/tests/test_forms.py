import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.user_two = User.objects.create_user(username="Other")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test_group",
            description="Тестовое описание группы",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.other_user = Client()
        self.other_user.force_login(self.user_two)

    def cheking_context(self, expect_answer):
        """Проверка контекста страниц"""
        for obj, answer in expect_answer.items():
            with self.subTest(obj=obj):
                resp_context = obj
                self.assertEqual(resp_context, answer)

    def test_create_post_without_group(self):
        """Валидная форма создает запись в Post. Без группы"""
        # Создаем пост без группы
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст",
        }
        response = self.auth_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile", kwargs={"username": PostFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создалась запись
        self.assertEqual(Post.objects.order_by("-pk")[0].text, form_data["text"])

    def test_create_post_with_img(self):
        """Валидная форма создает запись в Post c img"""
        # Создаем пост c img
        post_count = Post.objects.count()
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name="small.gif", content=small_gif, content_type="image/gif"
        )
        form_data = {
            "text": "Тестовый текст",
            "image": uploaded,
        }
        response = self.auth_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile", kwargs={"username": PostFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создалась запись c img
        last_post = Post.objects.order_by("-pk")[0]
        expect_answer = {
            last_post.text: form_data["text"],
            str(last_post.image): str(last_post.image),
        }
        self.cheking_context(expect_answer)

    def test_create_post_with_group(self):
        """Валидная форма создает запись в Post. С группой"""
        # Создаем пост с группой
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст 2",
            "group": PostFormTests.group.pk,
        }
        response = self.auth_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile", kwargs={"username": PostFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создалась запись c группой
        last_post = Post.objects.order_by("-pk")[0]
        expect_answer = {
            last_post.group.pk: form_data["group"],
            last_post.text: form_data["text"],
        }
        self.cheking_context(expect_answer)

    def test_create_post_with_guest(self):
        """Валидная форма не создает запись в Post от гостя."""
        # Создаем пост гостем
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст 2",
            "group": PostFormTests.group.pk,
        }
        self.client.post(reverse("posts:post_create"), data=form_data, follow=True)
        # Проверяем что запись не создалась
        self.assertEqual(Post.objects.count(), post_count)

    def test_edit_post_without_group(self):
        """Валидная форма изменяет запись в Post."""
        # Редактируем пост без группы
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        form_data = {
            "text": "Тестовый текст правка",
        }
        response = self.auth_client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", kwargs={"post_id": post_new.pk})
        )
        # Проверяем, что запись изменилась
        self.assertTrue(
            Post.objects.filter(
                text=form_data["text"],
                id=post_new.pk,
            ).exists()
        )

    def test_edit_post_with_guest(self):
        """Валидная форма не изменяет запись в Post от имени гостя."""
        # Редактируем пост гостем
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        form_data = {
            "text": "Тестовый текст правка",
        }
        self.client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        # Проверяем, что запись не изменилась
        post_change = Post.objects.get(
            id=post_new.pk,
        )
        expect_answer = {
            post_new.pk: post_change.pk,
            post_new.text: post_change.text,
        }
        self.cheking_context(expect_answer)

    def test_edit_post_with_non_auth(self):
        """Валидная форма не изменяет запись в Post от имени не автора."""
        # Редактируем пост не автором
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        form_data = {
            "text": "Тестовый текст правка",
        }
        self.other_user.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        # Проверяем, что запись не изменилась
        post_change = Post.objects.get(
            id=post_new.pk,
        )
        expect_answer = {
            post_new.pk: post_change.pk,
            post_new.text: post_change.text,
        }
        self.cheking_context(expect_answer)

    def test_edit_post_with_group(self):
        """Валидная форма изменяет запись в Post с группой."""
        # Редактируем пост c группой
        post_new = Post.objects.create(
            author=PostFormTests.user, text="Текст", group=PostFormTests.group
        )
        form_data = {
            "text": "Тестовый текст правка",
            "group": post_new.group.pk,
        }
        response = self.auth_client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", kwargs={"post_id": post_new.pk})
        )
        # Проверяем, что запись изменилась
        post_change = Post.objects.get(id=post_new.pk)
        expect_answer = {
            post_new.pk: post_change.pk,
            form_data["text"]: post_change.text,
            form_data["group"]: post_change.group.pk,
        }
        self.cheking_context(expect_answer)

    def test_create_comment_auth(self):
        """Валидная форма создает комментарий."""
        # Создаем пост и комментарий
        # авторизированным пользователем
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        comments_count = Comment.objects.count()
        form_data = {
            "text": "Тестовый комментарий",
        }
        response = self.auth_client.post(
            reverse("posts:add_comment", kwargs={"post_id": post_new.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", kwargs={"post_id": post_new.pk})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        # Проверяем, что создался комментарий
        last_comment = Comment.objects.order_by("-pk")[0]
        self.assertEqual(last_comment.text, form_data["text"])
        response = self.auth_client.get(
            reverse("posts:post_detail", kwargs={"post_id": post_new.pk}),
        )
        self.assertEqual(response.context["comments"][0].text, form_data["text"])

    def test_create_comment_guest(self):
        """Валидная форма не создает комментарий от гостя."""
        # Создаем пост и комментарий
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        comments_count = Comment.objects.count()
        form_data = {
            "text": "Тестовый комментарий",
        }
        self.client.post(
            reverse("posts:add_comment", kwargs={"post_id": post_new.pk}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count)
