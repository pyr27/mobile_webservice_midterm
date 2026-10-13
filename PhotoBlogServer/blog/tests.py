from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Post


class PostAPITestCase(APITestCase):

    def setUp(self):
        # 실제 User를 먼저 만들고, 그 User를 author로 사용
        self.user = User.objects.create_user(username="testuser", password="testpass123")

        self.post = Post.objects.create(
            author=self.user,
            title="테스트 게시글",
            text="자동 테스트로 생성된 게시글입니다.",
            created_date=timezone.now(),
            published_date=timezone.now(),
        )

    def test_get_post_list(self):
        """GET /api_root/Post/ 요청 시 200 OK와 게시글 목록을 반환하는지 확인"""
        response = self.client.get('/api_root/Post/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_post_list_contains_title(self):
        """목록에 방금 만든 게시글의 title이 포함되어 있는지 확인"""
        response = self.client.get('/api_root/Post/')
        titles = [item['title'] for item in response.data]
        self.assertIn("테스트 게시글", titles)

    def test_create_post(self):
        """POST /api_root/Post/ 로 새 게시글 작성이 되는지 확인"""
        data = {
            "author": self.user.id,
            "title": "새 글",
            "text": "POST 테스트",
            "created_date": timezone.now().isoformat(),
            "published_date": timezone.now().isoformat(),
        }
        response = self.client.post('/api_root/Post/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)

    def test_api_root_allowed_methods(self):
        """OPTIONS 요청으로 GET, POST, HEAD, OPTIONS가 허용되는지 확인"""
        response = self.client.options('/api_root/Post/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('GET', response['Allow'])
        self.assertIn('POST', response['Allow'])