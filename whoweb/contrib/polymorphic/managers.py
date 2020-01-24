from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet


class SoftDeletePolymorphicQuerySet(PolymorphicQuerySet):
    def delete(self):
        """
        Soft delete objects from queryset (set their ``is_removed``
        field to True)
        """
        self.update(is_removed=True)


class PolymorphicSoftDeletableManager(PolymorphicManager):
    queryset_class = SoftDeletePolymorphicQuerySet

    def get_queryset(self):
        qs = super().get_queryset().filter(is_removed=False)
        return qs
