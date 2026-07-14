"""Make title_sort_key NOT NULL and switch the default browse order to it.

Split from 0012 (the backfill): Postgres refuses `ALTER TABLE` while the table
has pending trigger events from DML earlier in the same transaction, so the
backfill must commit in its own migration before this one runs.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0012_backfill_title_sort_key'),
    ]

    operations = [
        # Forbid NULL and default new rows to '' (Work.save() always sets it).
        migrations.AlterField(
            model_name='work',
            name='title_sort_key',
            field=models.CharField(
                blank=True, db_index=True, default='',
                help_text='Normalized title for alphabetical sorting', max_length=1000,
            ),
        ),
        # Default browse order is now the alphabetical sort key, not raw `title`.
        migrations.AlterModelOptions(
            name='work',
            options={'ordering': ['title_sort_key']},
        ),
    ]
