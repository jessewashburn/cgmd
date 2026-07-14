"""Backfill title_sort_key for every existing work.

Historically `Work.save()` only maintained `title_normalized`, so `title_sort_key`
was NULL on any work created/edited outside the one-off `update_sort_keys` command.
That broke the Works default (alphabetical) ordering. `Work.save()` now recomputes
the key on every save; this migration fixes the existing rows.

The NOT NULL / default / Meta.ordering changes live in the *next* migration
(0013): Postgres refuses to ALTER a table that has pending trigger events from
DML earlier in the same transaction, so the backfill must commit first.
"""
from django.db import migrations

from music.utils import generate_title_sort_key


def backfill_sort_keys(apps, schema_editor):
    Work = apps.get_model('music', 'Work')
    batch_size = 1000
    # Order by pk so the offset slices are stable — titles are not unique (many
    # "Trio" etc.), so an unordered/ambiguous slice would skip rows at batch
    # boundaries and leave them with an empty key.
    qs = Work.objects.order_by('pk').only('id', 'title', 'title_sort_key')
    total = qs.count()
    for start in range(0, total, batch_size):
        batch = list(qs[start:start + batch_size])
        for work in batch:
            work.title_sort_key = generate_title_sort_key(work.title or '')
        Work.objects.bulk_update(batch, ['title_sort_key'], batch_size=batch_size)


def noop_reverse(apps, schema_editor):
    # Recomputable from `title` at any time; nothing to undo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0011_worklink'),
    ]

    operations = [
        # Populate every existing row so no NULLs remain. The schema tightening
        # (NOT NULL / default / ordering) happens in 0013, in a fresh transaction.
        migrations.RunPython(backfill_sort_keys, noop_reverse),
    ]
