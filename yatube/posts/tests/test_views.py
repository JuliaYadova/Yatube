import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test_group",
            description="Тестовое описание группы",
        )
        cls.group_two = Group.objects.create(
            title="Тестовая группа №2",
            slug="test_group_2",
            description="Тестовое описание группы №2",
        )
        cls.user = User.objects.create_user(username="HasNoName")
        cls.user_two = User.objects.create_user(username="TestUser2")
        cls.post = Post.objects.create(
            author=cls.user, text="Тестовый текст.", group=cls.group
        )
        # Создаем пулы постов для тестов контекста страниц.
        for i in range(1, 11):
            Post.objects.create(
                author=cls.user,
                text=f"Тестовый текст {1+i}",
                group=cls.group,
            )
        for i in range(6):
            Post.objects.create(
                author=cls.user_two,
                text=f"Тестовый текст (без группы) {1+i}",
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент
        self.auth_client = Client()
        self.auth_client.force_login(self.user)

    def cheking_context(self, expect_answer):
        """Проверка контекста страниц"""
        for obj, answer in expect_answer.items():
            with self.subTest(obj=obj):
                cache.clear()
                resp_context = obj
                self.assertEqual(resp_context, answer)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"

        templates_pages_names = {
            reverse("posts:posts_index"): "posts/index.html",
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group.slug}"}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": f"{PostPagesTests.user}"}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail",
                kwargs={"post_id": f"{int(PostPagesTests.post.pk)}"},
            ): "posts/post_detail.html",
            reverse("posts:post_create"): "posts/create_post.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": f"{int(PostPagesTests.post.pk)}"}
            ): "posts/create_post.html",
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                cache.clear()
                response = self.auth_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        cache.clear()
        response = self.auth_client.get(reverse("posts:posts_index"))
        # Проверяем что в контексте передается список из 10 постов
        # и работает паджинатор
        self.assertEqual(len(response.context["page_obj"]), settings.PER_PAGE_COUNT)
        cache.clear()
        response = self.client.get(reverse("posts:posts_index") + "?page=2")

        if Post.objects.count() - settings.PER_PAGE_COUNT < settings.PER_PAGE_COUNT:
            posts_for_two_page = Post.objects.count() - settings.PER_PAGE_COUNT
        else:
            posts_for_two_page = settings.PER_PAGE_COUNT
        self.assertEqual(len(response.context["page_obj"]), posts_for_two_page)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.auth_client.get(
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group.slug}"}
            )
        )
        # Проверяем наличие группы в контексте
        self.assertEqual(str(response.context["group"]), PostPagesTests.group.title)
        # Проверяем паджинатор
        self.assertEqual(len(response.context["page_obj"]), settings.PER_PAGE_COUNT)
        response = self.auth_client.get(
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group.slug}"}
            )
            + "?page=2"
        )
        if (
            Post.objects.filter(group=PostPagesTests.group).count()
            - settings.PER_PAGE_COUNT
            < settings.PER_PAGE_COUNT
        ):
            posts_for_two_page = (
                Post.objects.filter(group=PostPagesTests.group).count()
                - settings.PER_PAGE_COUNT
            )
        else:
            posts_for_two_page = settings.PER_PAGE_COUNT
        self.assertEqual(len(response.context["page_obj"]), posts_for_two_page)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.auth_client.get(
            reverse("posts:profile", kwargs={"username": f"{PostPagesTests.user}"})
        )
        # Проверяем автора
        self.assertEqual(response.context["author"], PostPagesTests.user)
        # Проверяем паджинатор
        self.assertEqual(len(response.context["page_obj"]), settings.PER_PAGE_COUNT)
        response = self.auth_client.get(
            reverse("posts:profile", kwargs={"username": f"{PostPagesTests.user}"})
            + "?page=2"
        )
        if (
            Post.objects.filter(author=PostPagesTests.user).count()
            - settings.PER_PAGE_COUNT
            < settings.PER_PAGE_COUNT
        ):
            posts_for_two_page = (
                Post.objects.filter(author=PostPagesTests.user).count()
                - settings.PER_PAGE_COUNT
            )
        else:
            posts_for_two_page = settings.PER_PAGE_COUNT
        self.assertEqual(len(response.context["page_obj"]), posts_for_two_page)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.auth_client.get(
            reverse(
                "posts:post_detail",
                kwargs={"post_id": f"{int(PostPagesTests.post.pk)}"},
            )
        )
        expect_answer = {
            response.context["post"].pk: PostPagesTests.post.pk,
            str(response.context["post"]): PostPagesTests.post.text,
            response.context["user"]: PostPagesTests.post.author,
        }
        self.cheking_context(expect_answer)

    def test_create_post__page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.auth_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        # Проверяем, что типы полей формы в context соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.auth_client.get(
            reverse(
                "posts:post_edit", kwargs={"post_id": f"{int(PostPagesTests.post.pk)}"}
            )
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        # Проверяем, что типы полей формы в context соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)
        # Проверяем что на странице указан пост для редактиврования
        expect_answer = {
            response.context["post"].pk: PostPagesTests.post.pk,
            str(response.context["post"]): PostPagesTests.post.text,
        }
        self.cheking_context(expect_answer)

    def test_new_post_create_correct(self):
        """Правильное отражение нового поста."""
        self.auth_client = Client()
        self.auth_client.force_login(self.user_two)
        post_new = Post.objects.create(
            author=PostPagesTests.user_two,
            text="Текст",
            group=PostPagesTests.group_two,
        )
        # Post_detail отображается корректно
        response = self.auth_client.get(
            reverse("posts:post_detail", kwargs={"post_id": f"{int(post_new.pk)}"})
        )
        expect_answer = {
            response.context["post"].pk: post_new.pk,
            str(response.context["post"]): post_new.text,
            response.context["user"]: post_new.author,
        }
        self.cheking_context(expect_answer)

        # Пост попал на главную страницу index
        cache.clear()
        response = self.auth_client.get(reverse("posts:posts_index"))
        first_obj = response.context["page_obj"][0]
        obj_auth_0 = first_obj.author
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_auth_0: post_new.author,
        }
        self.cheking_context(expect_answer)

        # Пост попал на страницу группы
        response = self.auth_client.get(
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group_two.slug}"}
            )
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
        }
        self.cheking_context(expect_answer)

        # Пост попал на страницу автора
        response = self.auth_client.get(
            reverse("posts:profile", kwargs={"username": f"{PostPagesTests.user_two}"})
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
        }
        self.cheking_context(expect_answer)

        # Пост не попал на страницу другой группы
        response = self.auth_client.get(
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group.slug}"}
            )
        )
        self.assertFalse("Тестовая группа №2" in str(response.context["group"]))

    def test_new_post_create_correct_with_img(self):
        """Правильное отражение нового поста с картинкой."""
        self.auth_client = Client()
        self.auth_client.force_login(self.user_two)
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
        post_new = Post.objects.create(
            author=PostPagesTests.user_two,
            text="Текст",
            group=PostPagesTests.group_two,
            image=uploaded,
        )

        # Post_detail отображается корректно
        response = self.auth_client.get(
            reverse("posts:post_detail", kwargs={"post_id": f"{int(post_new.pk)}"})
        )
        expect_answer = {
            response.context["post"].pk: post_new.pk,
            str(response.context["post"]): post_new.text,
            response.context["user"]: post_new.author,
            response.context["post"].image: post_new.image,
        }
        self.cheking_context(expect_answer)
        # Пост на index отображается корректно
        cache.clear()
        response = self.auth_client.get(reverse("posts:posts_index"))
        first_obj = response.context["page_obj"][0]
        obj_auth_0 = first_obj.author
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_auth_0: post_new.author,
            obj_img: post_new.image,
        }
        self.cheking_context(expect_answer)

        # Пост на странице группы отображается корректно
        response = self.auth_client.get(
            reverse(
                "posts:group_posts", kwargs={"slug": f"{PostPagesTests.group_two.slug}"}
            )
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_img: post_new.image,
        }
        self.cheking_context(expect_answer)

        # Пост на странице автора отображается корректно
        response = self.auth_client.get(
            reverse("posts:profile", kwargs={"username": f"{PostPagesTests.user_two}"})
        )
        first_obj = response.context["page_obj"][0]
        obj_text_0 = first_obj.text
        obj_id = first_obj.pk
        obj_img = first_obj.image
        expect_answer = {
            obj_id: post_new.pk,
            str(obj_text_0): post_new.text,
            obj_img: post_new.image,
        }
        self.cheking_context(expect_answer)

    def test_index_page_include_cash(self):
        """Шаблон index сформирован с кешем."""
        new_post = Post.objects.create(
            author=PostPagesTests.user,
            text="Текст для теста кеширования.",
        )
        # Проверка views на кеширование
        cache.clear()
        response_with = self.client.get(reverse("posts:posts_index"))
        self.assertIn(new_post, response_with.context["page_obj"])
        new_post.delete()
        response_without = self.client.get(reverse("posts:posts_index"))
        self.assertEqual(response_with.content, response_without.content)

    def test_follow_page_(self):
        """Авторизированный автор может подписаться на другого автора."""
        Follow_count = Follow.objects.count()
        self.auth_client.post(
            reverse(
                "posts:profile_follow",
                kwargs={"username": str(PostPagesTests.user_two)},
            )
        )
        self.assertEqual(Follow.objects.count(), Follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=PostPagesTests.user, author=PostPagesTests.user_two
            ).exists()
        )

    def test_unfollow_page_(self):
        """Авторизированный автор может отписаться от избранного автора."""
        self.auth_client.post(
            reverse(
                "posts:profile_follow",
                kwargs={"username": str(PostPagesTests.user_two)},
            )
        )
        Follow_count = Follow.objects.count()
        self.auth_client.post(
            reverse(
                "posts:profile_unfollow",
                kwargs={"username": str(PostPagesTests.user_two)},
            )
        )
        self.assertEqual(Follow.objects.count(), Follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=PostPagesTests.user, author=PostPagesTests.user_two
            ).exists()
        )

    def test_follow_index_page_(self):
        """Новая запись пользователя появляется в ленте followers
        и не появляется в ленте остальных.
        """
        new_user = User.objects.create_user(username="TestFollow")
        new_client = Client()
        new_client.force_login(new_user)
        new_client.post(
            reverse(
                "posts:profile_follow",
                kwargs={"username": str(PostPagesTests.user_two)},
            )
        )
        new_post = Post.objects.create(
            author=PostPagesTests.user_two,
            text="Текст для теста follow.",
        )
        response = self.auth_client.get(reverse("posts:follow_index"))
        response_new_user = new_client.get(reverse("posts:follow_index"))
        self.assertIn(new_post, response_new_user.context["page_obj"].object_list)
        self.assertNotIn(new_post, response.context["page_obj"].object_list)
