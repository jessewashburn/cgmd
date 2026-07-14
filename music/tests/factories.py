"""factory-boy factories for building test data."""
import factory
from factory.django import DjangoModelFactory

from music.models import (
    Country, InstrumentationCategory, DataSource, Composer, Work,
)


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Country {n}')


class InstrumentationCategoryFactory(DjangoModelFactory):
    class Meta:
        model = InstrumentationCategory
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Instrumentation {n}')


class DataSourceFactory(DjangoModelFactory):
    class Meta:
        model = DataSource
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Source {n}')


class ComposerFactory(DjangoModelFactory):
    class Meta:
        model = Composer

    full_name = factory.Sequence(lambda n: f'Composer {n}')
    last_name = factory.Sequence(lambda n: f'Last{n}')
    first_name = 'First'
    birth_year = 1850
    country = factory.SubFactory(CountryFactory)
    # name_normalized is auto-populated by Composer.save()


class WorkFactory(DjangoModelFactory):
    class Meta:
        model = Work

    title = factory.Sequence(lambda n: f'Work {n}')
    composer = factory.SubFactory(ComposerFactory)
    instrumentation_category = factory.SubFactory(InstrumentationCategoryFactory)
    is_public = True
    # title_normalized and title_sort_key are auto-populated by Work.save()
