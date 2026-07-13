"""
Add GIN trigram indexes on the remaining searched columns so the `%` operator
(trigram_similar lookup) is fully index-backed. Migration 0004 covered
works.title / works.title_normalized / composers.full_name / composers.last_name;
these are the columns still searched by TrigramSearchFilter that lacked an index:
works.opus_number, composers.first_name, composers.name_normalized.

Only runs on PostgreSQL.
"""
from django.db import migrations


INDEXES = [
    ("work_opus_trgm_idx", "works", "opus_number"),
    ("composer_firstname_trgm_idx", "composers", "first_name"),
    ("composer_namenorm_trgm_idx", "composers", "name_normalized"),
]


def create_trigram_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for name, table, column in INDEXES:
        schema_editor.execute(
            f"CREATE INDEX IF NOT EXISTS {name} "
            f"ON {table} USING gin({column} gin_trgm_ops);"
        )


def drop_trigram_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for name, _table, _column in INDEXES:
        schema_editor.execute(f"DROP INDEX IF EXISTS {name};")


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0009_usersuggestion'),
    ]

    operations = [
        migrations.RunPython(create_trigram_indexes, drop_trigram_indexes),
    ]
