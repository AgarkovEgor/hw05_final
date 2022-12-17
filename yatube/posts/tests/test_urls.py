from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.cache import cache
from ..models import Post, Group
from http import HTTPStatus

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="egor")
        cls.user2 = User.objects.create_user(username="egor1")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание"
        )
        cls.post = Post.objects.create(
            author=cls.user, text="Тестовый пост", group=cls.group
        )

        cls.templates = [
            "/",
            f"/group/{cls.group.slug}/",
            f"/profile/{cls.user}/",
            f"/posts/{cls.post.id}/",
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_url_exists_at_desired_location(self):
        """Проверяем доступность страниц"""
        for template in self.templates:
            with self.subTest(template):
                response = self.guest_client.get(template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_uses_correct_template(self):
        """Проверяет соотвествие ulr шаблонам"""
        cache.clear()
        templates_url_names = {
            "/": "posts/index.html",
            f"/group/{self.group.slug}/": "posts/group_list.html",
            f"/profile/{self.user.username}/": "posts/profile.html",
            f"/posts/{self.post.id}/": "posts/post_detail.html",
            f"/posts/{self.post.id}/edit/": "posts/post_create.html",
            "/create/": "posts/post_create.html",
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_404(self):
        """ "Проверка на ошибку 404"""
        response = self.guest_client.get("/404")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_create_redirect_anonymous_on_admin_login(self):
        """Проверка на редирект неавторизованного пользователя"""
        response = self.guest_client.get("/create/")
        self.assertRedirects(response, "/auth/login/?next=/create/")

    def test_post_edit_is_available_only_author(self):
        """Проверяем, что редактирование поста доступно только автору"""
        self.user = User.objects.get(username=self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        response = self.authorized_client.get(f"/posts/{self.post.id}/edit/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
