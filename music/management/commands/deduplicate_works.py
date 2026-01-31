"""
Management command to remove duplicate work records from the database.
Keeps the oldest record (lowest ID) for each unique title+composer combination.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from music.models import Work


class Command(BaseCommand):
    help = 'Remove duplicate work records, keeping the oldest (lowest ID) for each title+composer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('Finding duplicate works...')
        
        # Find all works that have duplicates (same title + composer)
        duplicates = Work.objects.values('title', 'composer').annotate(
            count=Count('id'),
            min_id=Min('id')
        ).filter(count__gt=1)
        
        total_groups = duplicates.count()
        self.stdout.write(f'Found {total_groups} groups of duplicate works')
        
        total_deleted = 0
        
        for dup in duplicates:
            title = dup['title']
            composer_id = dup['composer']
            min_id = dup['min_id']
            count = dup['count']
            
            # Get all works with this title+composer except the oldest one
            works_to_delete = Work.objects.filter(
                title=title,
                composer_id=composer_id
            ).exclude(id=min_id)
            
            delete_count = works_to_delete.count()
            
            if delete_count > 0:
                if dry_run:
                    # Use ASCII representation to avoid encoding issues
                    safe_title = title[:50].encode('ascii', 'replace').decode('ascii')
                    self.stdout.write(
                        f'Would delete {delete_count} duplicate(s) of "{safe_title}" '
                        f'(keeping ID {min_id})'
                    )
                else:
                    works_to_delete.delete()
                    total_deleted += delete_count
                    
                    if total_deleted % 1000 == 0:
                        self.stdout.write(f'Deleted {total_deleted} duplicates so far...')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would delete {total_deleted} duplicate work records'
                )
            )
            self.stdout.write('Run without --dry-run to actually delete duplicates')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully deleted {total_deleted} duplicate work records'
                )
            )
            
            # Verify no duplicates remain
            remaining = Work.objects.values('title', 'composer').annotate(
                count=Count('id')
            ).filter(count__gt=1).count()
            
            if remaining == 0:
                self.stdout.write(self.style.SUCCESS('No duplicate works remain!'))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Warning: {remaining} groups of duplicates still exist'
                    )
                )
