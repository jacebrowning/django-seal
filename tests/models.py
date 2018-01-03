from django.db import models
from seal.models import SealableModel


class Location(SealableModel):
    latitude = models.FloatField()
    longitude = models.FloatField()


class SeaLion(SealableModel):
    height = models.PositiveIntegerField()
    weight = models.PositiveIntegerField()
    location = models.ForeignKey(Location, models.CASCADE, null=True)
