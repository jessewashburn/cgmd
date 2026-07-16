"""Create the composer_eras table.

Schema only — no RunPython. The ~22k derived rows are written afterwards by
`manage.py backfill_composer_eras`, deliberately *not* here: web's entrypoint runs
migrate on every container start under `set -e`, so a backfill that fails or drags
crash-loops the container and takes /api down (see AWS_DEPLOYMENT.md). A new empty
table has no such urgency — until the command runs, the era filter simply matches
nothing, which degrades rather than breaks.

(0012_backfill_title_sort_key does backfill in-migration; it was populating a column
on an existing table and had no alternative. This one does.)
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0013_finalize_title_sort_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComposerEra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('era', models.CharField(choices=[('renaissance', 'Renaissance'), ('baroque', 'Baroque'), ('classical', 'Classical'), ('romantic', 'Romantic'), ('modern', 'Modern'), ('21st-century', '21st Century')], max_length=20)),
                ('basis', models.CharField(choices=[('dates', 'Derived from birth/death years'), ('source', 'Inferred from data source (no dates available)'), ('manual', 'Set by an admin')], default='dates', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('composer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eras', to='music.composer')),
            ],
            options={
                'db_table': 'composer_eras',
                'indexes': [models.Index(fields=['composer'], name='idx_composer_eras_composer'), models.Index(fields=['era', 'composer'], name='idx_composer_eras_era')],
                'unique_together': {('composer', 'era')},
            },
        ),
    ]
