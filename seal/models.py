from __future__ import unicode_literals

from django.core import checks
from django.db import models
from django.db.models.fields.related import lazy_related_operation
from django.dispatch import receiver

from .descriptors import sealable_descriptor_classes
from .query import SealableQuerySet


class BaseSealableManager(models.manager.BaseManager):
    def check(self, **kwargs):
        errors = super(BaseSealableManager, self).check(**kwargs)
        if not issubclass(self.model, SealableModel):
            if getattr(self, '_built_with_as_manager', False):
                origin = '%s.as_manager()' % self._queryset_class.__name__
            else:
                origin = self.__class__.__name__
            errors.append(
                checks.Error(
                    '%s can only be used on seal.SealableModel subclasses.' % origin,
                    id='seal.E001',
                    hint='Make %s inherit from seal.SealableModel.' % self.model._meta.label,
                    obj=self,
                )
            )
        return errors


SealableQuerySet._base_manager_class = BaseSealableManager
SealableManager = BaseSealableManager.from_queryset(SealableQuerySet, str('SealableManager'))


class SealableModel(models.Model):
    """
    Abstract model class that turns deferred and related fields accesses that
    would incur a database query into exceptions once sealed.
    """

    objects = SealableManager()

    class Meta:
        abstract = True

    def seal(self):
        """
        Seal the instance to turn deferred and related fields access that would
        required fetching from the database into exceptions.
        """
        self._state.sealed = True


def make_descriptor_sealable(model, attname):
    """
    Make a descriptor sealable if a sealable class is defined.
    """
    try:
        descriptor = getattr(model, attname)
    except AttributeError:
        # Handle hidden reverse accessor case. e.g. related_name='+'
        return
    sealable_descriptor_class = sealable_descriptor_classes.get(descriptor.__class__)
    if sealable_descriptor_class:
        descriptor.__class__ = sealable_descriptor_class


def make_remote_field_descriptor_sealable(model, related_model, remote_field):
    """
    Make a remote field descriptor sealable if a sealable class is defined.
    """
    if not issubclass(related_model, SealableModel):
        return
    accessor_name = remote_field.get_accessor_name()
    make_descriptor_sealable(related_model, accessor_name)


@receiver(models.signals.class_prepared)
def make_field_descriptors_sealable(sender, **kwargs):
    """
    Replace SealableModel subclasses forward and reverse fields descriptors
    by sealable ones.
    """
    if not issubclass(sender, SealableModel):
        return
    opts = sender._meta
    if opts.abstract or opts.proxy:
        return
    for field in (opts.local_fields + opts.local_many_to_many + opts.private_fields):
        make_descriptor_sealable(sender, field.name)
        remote_field = field.remote_field
        if remote_field:
            # Use lazy_related_operation because lazy relationships might not
            # be resolved yet.
            lazy_related_operation(
                make_remote_field_descriptor_sealable, sender, remote_field.model, remote_field=remote_field
            )
