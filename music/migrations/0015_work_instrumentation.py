"""Create the work_instrumentations table.

Schema only — no RunPython, and no ALTER on `works`, so CLAUDE.md's "never mix a
data change with a schema change on the same table" rule is satisfied by
construction. The ~665 derived rows are written afterwards by
`manage.py backfill_alternate_instrumentations`: web's entrypoint runs migrate on
every container start under `set -e`, so parsing 73k detail strings in-migration on
a t4g.micro would risk crash-looping the container and taking /api down. Until the
command runs, ?instrumentation= behaves exactly as it does today — degradation, not
an outage.

`Work.instrumentation_category` is untouched: it remains the primary. See SDD:
alternate-work-instrumentations.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0014_composer_eras'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkInstrumentation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('basis', models.CharField(choices=[('derived', 'Derived from the detail text'), ('suggested', 'Proposed by a user and approved by an admin'), ('manual', 'Set by an admin')], default='derived', max_length=10)),
                ('note', models.CharField(blank=True, help_text="e.g. 'playable as 5 guitars'", max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alternate_works', to='music.instrumentationcategory')),
                ('work', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alternate_instrumentations', to='music.work')),
            ],
            options={
                'db_table': 'work_instrumentations',
                'indexes': [models.Index(fields=['work'], name='idx_work_inst_work'), models.Index(fields=['category', 'work'], name='idx_work_inst_category')],
                'unique_together': {('work', 'category')},
            },
        ),
    ]
