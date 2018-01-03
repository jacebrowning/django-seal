from django.test import TestCase
from seal.exceptions import SealedObject

from .models import Location, SeaLion


class SealableQuerySetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.create(latitude=51.585474, longitude=156.634331)
        cls.sealion = SeaLion.objects.create(height=1, weight=100, location=cls.location)
        cls.sealion.previous_locations.add(cls.location)

    def test_state_sealed_assigned(self):
        instance = SeaLion.objects.seal().get()
        self.assertTrue(instance._state.sealed)

    def test_sealed_deferred_field(self):
        instance = SeaLion.objects.seal().defer('weight').get()
        with self.assertRaisesMessage(SealedObject, 'Cannot fetch deferred fields weight on a sealed object.'):
            instance.weight

    def test_sealed_related_object(self):
        instance = SeaLion.objects.seal().get()
        with self.assertRaisesMessage(SealedObject, 'Cannot fetch related field location on a sealed object.'):
            instance.location

    def test_sealed_select_related(self):
        instance = SeaLion.objects.select_related('location').seal().get()
        self.assertEqual(instance.location, self.location)

    def test_sealed_many_to_many(self):
        instance = SeaLion.objects.seal().get()
        message = 'Cannot fetch many-to-many field previous_locations on a sealed object.'
        with self.assertRaisesMessage(SealedObject, message):
            instance.previous_locations.all()

    def test_sealed_prefetched_many_to_many(self):
        instance = SeaLion.objects.prefetch_related('previous_locations').seal().get()
        self.assertSequenceEqual(instance.previous_locations.all(), [self.location])
