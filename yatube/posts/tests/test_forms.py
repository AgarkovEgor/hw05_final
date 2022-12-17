import shutil
import tempfile

from http import HTTPStatus

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Post, Group, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="egor")
        cls.user2 = User.objects.create_user(username="egor1")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user, text="Тестовый пост", group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post, author=cls.user, text="Тестовый комментарий"
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка создания новой записи в БД"""
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
            "text": "Тестовый пост",
            "image": uploaded,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        new_post = Post.objects.last()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertRedirects(
            response,
            reverse("posts:profile", kwargs={"username": self.user.username}),
        )
        self.assertTrue(Post.objects.filter(text=form_data["text"]).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            (new_post.author == self.user) and (new_post.group == self.group)
        )

    def test_post_edit(self):
        """Проверка изменения поста"""
        group_new = Group.objects.create(
            title="Тестовая группа 2",
            slug="test-slug2",
            description="Тестовое описание 2",
        )
        posts_count = Post.objects.count()
        small_gif1 = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded1 = SimpleUploadedFile(
            name="small.gif", content=small_gif1, content_type="image/gif"
        )
        form_data = {
            "text": "Измененный пост",
            "group": group_new.id,
            "image": uploaded1,
        }
        old_group_response1 = self.authorized_client.get(
            reverse("posts:group_posts", args=[self.group.slug])
        )
        posts_count_old_group = old_group_response1.context["page_obj"].paginator.count
        new_group_response2 = self.authorized_client.get(
            reverse("posts:group_posts", args=[group_new.slug])
        )
        posts_count_new_group = new_group_response2.context["page_obj"].paginator.count
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        old_group_response = self.authorized_client.get(
            reverse("posts:group_posts", args=[self.group.slug])
        )
        new_group_response = self.authorized_client.get(
            reverse("posts:group_posts", args=[group_new.slug])
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", args=[self.post.id])
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(text=form_data["text"], group=group_new.id).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            old_group_response.context["page_obj"].paginator.count,
            posts_count_old_group - 1,
        )
        self.assertEqual(
            new_group_response.context["page_obj"].paginator.count,
            posts_count_new_group + 1,
        )

    def test_add_comment(self):
        "Проверка, что комментарий появляется на странице"
        comment_count = self.post.comments.count()
        form_data = {"text": "Тест коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", args=[self.post.id])
        )
        self.assertEqual(self.post.comments.count(), comment_count + 1)
        self.assertEqual(self.post.comments.latest("id").text, form_data["text"])

    def test_add_comment_anon_user(self):
        """Проверка добавления поста неавторизованным пользователем"""
        comment_count = self.post.comments.count()
        form_data = {"text": "Тест коммент"}
        response = self.client.post(
            reverse("posts:add_comment", args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, f"/auth/login/?next=/posts/{self.post.id}/comment/"
        )
        self.assertEqual(self.post.comments.count(), comment_count)
