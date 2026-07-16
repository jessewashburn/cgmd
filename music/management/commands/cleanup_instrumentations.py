"""
Django management command to consolidate instrumentation categories.

Re-derives every work's instrumentation_category from its free-text
instrumentation_detail via music.utils.canonical_instrumentation — the same
mapping Work.save() applies — and drops any category left with no works. Safe to
re-run; it's the backfill for works whose category predates that shared mapping.
"""

from django.core.management.base import BaseCommand
from music.models import InstrumentationCategory, Work
from music.utils import canonical_instrumentation

BATCH_SIZE = 500


class Command(BaseCommand):
    help = 'Consolidate instrumentation categories from granular to broad categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        self.stdout.write('Analyzing works and their instrumentations...')
        
        # Get all works with instrumentation details
        works = Work.objects.select_related('instrumentation_category').all()
        total_works = works.count()
        self.stdout.write(f'Found {total_works} works to process')
        
        # Track category mappings
        category_cache = {}
        updates = []
        stats = {'updated': 0, 'unchanged': 0}
        
        def resolve(name):
            """get_or_create the category, memoized. None stays None (no category)."""
            if name is None:
                return None
            if name not in category_cache:
                category_cache[name], _ = InstrumentationCategory.objects.get_or_create(name=name)
            return category_cache[name]

        # .order_by('pk').iterator() so a 70k+ table streams instead of being loaded
        # whole, and flush in batches rather than holding every changed row until the
        # end — this runs against prod on a t4g.micro.
        for i, work in enumerate(works.order_by('pk').iterator(chunk_size=BATCH_SIZE), 1):
            if i % 1000 == 0:
                self.stdout.write(f'  Processed {i}/{total_works} works...')

            # Use instrumentation_detail (raw text) to determine category
            raw_inst = work.instrumentation_detail or ''
            if not raw_inst and work.instrumentation_category:
                raw_inst = work.instrumentation_category.name

            broad_category = canonical_instrumentation(raw_inst)
            current_category = work.instrumentation_category.name if work.instrumentation_category else None

            if current_category == broad_category:
                stats['unchanged'] += 1
                continue

            stats['updated'] += 1
            if dry_run:
                continue

            work.instrumentation_category = resolve(broad_category)
            updates.append(work)
            if len(updates) >= BATCH_SIZE:
                Work.objects.bulk_update(updates, ['instrumentation_category'])
                updates.clear()

        if updates:
            Work.objects.bulk_update(updates, ['instrumentation_category'])

        # Show statistics
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('CONSOLIDATION COMPLETE'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Works updated: {stats["updated"]}')
        self.stdout.write(f'Works unchanged: {stats["unchanged"]}')
        self.stdout.write(f'New broad categories: {len(category_cache)}')
        
        if not dry_run:
            # Show category breakdown
            self.stdout.write('\nCategory distribution:')
            from django.db.models import Count
            categories = InstrumentationCategory.objects.annotate(
                work_count=Count('work')
            ).filter(work_count__gt=0).order_by('-work_count')
            
            for cat in categories[:20]:
                self.stdout.write(f'  {cat.name}: {cat.work_count} works')
            
            # Delete unused categories
            unused = InstrumentationCategory.objects.annotate(
                work_count=Count('work')
            ).filter(work_count=0)
            unused_count = unused.count()
            if unused_count > 0:
                self.stdout.write(f'\nDeleting {unused_count} unused instrumentation categories...')
                unused.delete()
                self.stdout.write(self.style.SUCCESS('✓ Cleanup complete!'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were made'))
            self.stdout.write('Run without --dry-run to apply changes')
