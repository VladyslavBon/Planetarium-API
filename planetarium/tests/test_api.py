import os
import tempfile

from PIL import Image
from django.urls import reverse
from django_redis import get_redis_connection
from rest_framework_simplejwt.tokens import RefreshToken

from planetarium.models import (
    ShowTheme,
    AstronomyShow,
    PlanetariumDome,
    ShowSession,
)
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from planetarium.serializers import (
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
)


ASTRONOMY_SHOW_URL = reverse("planetarium:astronomyshow-list")


User = get_user_model()


def sample_astronomy_show(**params):
    defaults = {
        "title": "Sample astronomy show",
        "description": "Sample description",
    }
    defaults.update(params)

    return AstronomyShow.objects.create(**defaults)


def sample_show_session(**params):
    planetarium_dome = PlanetariumDome.objects.create(
        name="Small", rows=20, seats_in_row=20
    )

    defaults = {
        "astronomy_show": None,
        "planetarium_dome": planetarium_dome,
        "show_time": "2024-12-25 14:00:00",
    }
    defaults.update(params)

    return ShowSession.objects.create(**defaults)


class AuthenticatedAstronomyShowApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@user.com", password="testpass")

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_list_astronomy_shows(self):
        sample_astronomy_show()
        sample_astronomy_show()

        res = self.client.get(ASTRONOMY_SHOW_URL)

        astronomy_shows = AstronomyShow.objects.order_by("id")
        serializer = AstronomyShowListSerializer(astronomy_shows, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_astronomy_shows_by_show_themes(self):
        show_theme1 = ShowTheme.objects.create(name="Show Theme 1")
        show_theme2 = ShowTheme.objects.create(name="Show Theme 2")

        astronomy_show1 = sample_astronomy_show(title="Astronomy Show 1")
        astronomy_show2 = sample_astronomy_show(title="Astronomy Show 2")

        astronomy_show1.show_theme.add(show_theme1)
        astronomy_show2.show_theme.add(show_theme2)

        astronomy_show3 = sample_astronomy_show(
            title="Astronomy Show without show theme"
        )

        res = self.client.get(
            ASTRONOMY_SHOW_URL,
            {"show_theme": f"{show_theme1.id},{show_theme2.id}"},
        )

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_astronomy_show_by_title(self):
        astronomy_show1 = sample_astronomy_show(title="Astronomy Show")
        astronomy_show2 = sample_astronomy_show(title="Another Astronomy Show")
        astronomy_show3 = sample_astronomy_show(title="No match")

        res = self.client.get(ASTRONOMY_SHOW_URL, {"title": "astronomy show"})

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_astronomy_show_detail(self):
        astronomy_show = sample_astronomy_show()
        astronomy_show.show_theme.add(ShowTheme.objects.create(name="Show Theme"))

        res = self.client.get(
            reverse(
                "planetarium:astronomyshow-detail",
                args=[astronomy_show.id],
            )
        )

        serializer = AstronomyShowDetailSerializer(astronomy_show)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_astronomy_show_forbidden(self):
        payload = {
            "title": "Astronomy Show",
            "description": "Description",
        }
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAstronomyShowApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@admin.com", password="testpass"
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_create_astronomy_show(self):
        show_theme1 = ShowTheme.objects.create(name="Show Theme 1")
        show_theme2 = ShowTheme.objects.create(name="Show Theme 2")
        payload = {
            "title": "Astronomy Show",
            "description": "Description",
            "show_theme": [show_theme1.id, show_theme2.id],
        }

        res = self.client.post(ASTRONOMY_SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(id=res.data["id"])

        self.assertEqual(payload["title"], astronomy_show.title)
        self.assertEqual(payload["description"], astronomy_show.description)

        show_themes = astronomy_show.show_theme.all()
        self.assertEqual(show_themes.count(), 2)
        self.assertIn(show_theme1, show_themes)
        self.assertIn(show_theme2, show_themes)


class AstronomyShowImageUploadTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@admin.com", password="testpass"
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        self.astronomy_show = sample_astronomy_show()
        self.show_session = sample_show_session(astronomy_show=self.astronomy_show)

    def tearDown(self):
        get_redis_connection("default").flushall()
        self.astronomy_show.image.delete()

    def test_upload_image_to_astronomy_show(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                reverse(
                    "planetarium:astronomyshow-upload-image",
                    args=[self.astronomy_show.id],
                ),
                {"image": ntf},
                format="multipart",
            )
        self.astronomy_show.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.astronomy_show.image.path))

    def test_upload_image_bad_request(self):
        res = self.client.post(
            reverse(
                "planetarium:astronomyshow-upload-image",
                args=[self.astronomy_show.id],
            ),
            {"image": "not image"},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_astronomy_show_list_should_not_work(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            show_theme = ShowTheme.objects.create(name="Show Theme")
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                ASTRONOMY_SHOW_URL,
                {
                    "title": "Title",
                    "description": "Description",
                    "show_theme": [show_theme.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(title="Title")
        self.assertFalse(astronomy_show.image)

    def test_image_url_is_shown_on_astronomy_show_detail(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                reverse(
                    "planetarium:astronomyshow-upload-image",
                    args=[self.astronomy_show.id],
                ),
                {"image": ntf},
                format="multipart",
            )
        res = self.client.get(
            reverse(
                "planetarium:astronomyshow-detail",
                args=[self.astronomy_show.id],
            )
        )

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_astronomy_show_list(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                reverse(
                    "planetarium:astronomyshow-upload-image",
                    args=[self.astronomy_show.id],
                ),
                {"image": ntf},
                format="multipart",
            )
        res = self.client.get(ASTRONOMY_SHOW_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_astronomy_show_session_detail(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                reverse(
                    "planetarium:astronomyshow-upload-image",
                    args=[self.astronomy_show.id],
                ),
                {"image": ntf},
                format="multipart",
            )
        res = self.client.get(
            reverse(
                "planetarium:showsession-detail",
                args=[self.show_session.id],
            ),
        )

        self.assertIn("image", res.data["astronomy_show"].keys())
