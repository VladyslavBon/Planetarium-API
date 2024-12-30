from django.core.exceptions import ValidationError
from django.test import TestCase

from planetarium.models import (
    ShowTheme,
    AstronomyShow,
    PlanetariumDome,
    ShowSession,
    Ticket,
    Reservation,
)
from django.contrib.auth import get_user_model


User = get_user_model()


class ModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@user.com", password="testpass")
        self.show_theme = ShowTheme.objects.create(name="Educational")
        self.astronomy_show = AstronomyShow.objects.create(
            title="The Wonders of Space",
            description="An amazing journey through the cosmos.",
        )
        self.astronomy_show.show_theme.add(self.show_theme)

        self.planetarium_dome = PlanetariumDome.objects.create(
            name="Main Dome", rows=10, seats_in_row=10
        )

        self.show_session = ShowSession.objects.create(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.planetarium_dome,
            show_time="2024-12-30 14:00:00",
        )
        self.reservation = Reservation.objects.create(user=self.user)

    def test_show_theme_str(self):
        self.assertEqual(str(self.show_theme), "Educational")

    def test_astronomy_show_str(self):
        self.assertEqual(str(self.astronomy_show), "The Wonders of Space")

    def test_show_session_str(self):
        self.assertEqual(
            str(self.show_session), "The Wonders of Space - 2024-12-30 14:00:00"
        )

    def test_planetarium_dome_capacity(self):
        self.assertEqual(self.planetarium_dome.capacity, 100)

    def test_ticket_validation(self):
        ticket = Ticket(
            row=5, seat=5, show_session=self.show_session, reservation=self.reservation
        )
        ticket.full_clean()

        with self.assertRaises(ValidationError):
            invalid_ticket = Ticket(
                row=15,
                seat=5,
                show_session=self.show_session,
                reservation=self.reservation,
            )
            invalid_ticket.full_clean()
