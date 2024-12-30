from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from planetarium.models import (
    ShowSession,
    Reservation,
    AstronomyShow,
    PlanetariumDome,
    ShowTheme,
    Ticket,
)
from planetarium.serializers import (
    ShowThemeSerializer,
    AstronomyShowSerializer,
    AstronomyShowListSerializer,
    TicketSerializer,
    ReservationSerializer,
)


User = get_user_model()


class SerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@user.com", password="testpass")
        self.show_theme = ShowTheme.objects.create(name="Space Exploration")
        self.dome = PlanetariumDome.objects.create(
            name="Main Dome", rows=10, seats_in_row=15
        )
        self.assertEqual(self.dome.capacity, 150)
        self.astronomy_show = AstronomyShow.objects.create(
            title="Journey to the Stars", description="A journey through the universe."
        )
        self.astronomy_show.show_theme.add(self.show_theme)
        self.show_session = ShowSession.objects.create(
            show_time="2024-12-31 20:00",
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
        )
        self.reservation = Reservation.objects.create(user=self.user)
        self.ticket = Ticket.objects.create(
            row=5, seat=10, show_session=self.show_session, reservation=self.reservation
        )

    def test_show_theme_serializer(self):
        serializer = ShowThemeSerializer(instance=self.show_theme)
        self.assertEqual(
            serializer.data, {"id": self.show_theme.id, "name": "Space Exploration"}
        )

    def test_astronomy_show_serializer(self):
        serializer = AstronomyShowSerializer(instance=self.astronomy_show)
        self.assertEqual(
            serializer.data,
            {
                "id": self.astronomy_show.id,
                "title": "Journey to the Stars",
                "description": "A journey through the universe.",
                "show_theme": [self.show_theme.id],
            },
        )

    def test_astronomy_show_list_serializer(self):
        serializer = AstronomyShowListSerializer(instance=self.astronomy_show)
        self.assertEqual(
            serializer.data,
            {
                "id": self.astronomy_show.id,
                "title": "Journey to the Stars",
                "show_theme": ["Space Exploration"],
                "image": None,
            },
        )

    def test_ticket_serializer(self):
        show_session = ShowSession.objects.create(
            show_time="2024-12-31 21:00",
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
        )
        data = {
            "row": 5,
            "seat": 10,
            "show_session": show_session.id,
        }
        serializer = TicketSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["row"], data["row"])
        self.assertEqual(serializer.validated_data["seat"], data["seat"])

    def test_ticket_serializer_validation_error(self):
        data = {
            "row": 11,
            "seat": 5,
            "show_session": self.show_session.id,
        }
        serializer = TicketSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_reservation_serializer(self):
        factory = APIRequestFactory()
        request = factory.post(reverse("planetarium:reservation-list"))
        request.user = self.user

        show_session = ShowSession.objects.create(
            show_time="2024-12-31 22:00",
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
        )

        data = {
            "tickets": [
                {"row": 5, "seat": 10, "show_session": show_session.id},
                {"row": 5, "seat": 11, "show_session": show_session.id},
            ]
        }

        serializer = ReservationSerializer(data=data, context={"request": request})
        self.assertTrue(serializer.is_valid())
        reservation = serializer.save(user=request.user)

        self.assertEqual(reservation.tickets.count(), 2)
        self.assertEqual(reservation.user, self.user)

    def test_reservation_serializer_validation_error(self):
        data = {
            "tickets": [
                {
                    "row": 11,
                    "seat": 10,
                    "show_session": self.show_session.id,
                },
            ]
        }
        serializer = ReservationSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
