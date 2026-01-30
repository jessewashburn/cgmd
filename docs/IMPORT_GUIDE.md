# Data Import Guide

This guide explains how to import data into the Classical Guitar Music Database.

## Overview

The database supports importing data from CSV files, with built-in parsers for:
- **Sheerpluck** classical guitar repertoire database ✅
- **IMSLP** (deferred to future release)

## Sheerpluck Data Import

### Prerequisites

1. MySQL database created and configured in `.env`
2. Django migrations run: `python manage.py migrate`
3. Sheerpluck CSV file available (default: `sheerpluck_data.csv`)

### Import Command

```bash
python manage.py import_sheerpluck [path/to/csv] [options]
```

### Options

- **No arguments**: Uses default `sheerpluck_data.csv` in project root
- `--dry-run`: Validate data without saving to database
- `--skip-existing`: Skip works that already exist (by external_id)

### Examples

**Import from default location:**
```bash
python manage.py import_sheerpluck
```

**Dry run to validate data:**
```bash
python manage.py import_sheerpluck --dry-run
```

**Import from custom location:**
```bash
python manage.py import_sheerpluck /path/to/data.csv
```

**Skip existing works (for updates):**
```bash
python manage.py import_sheerpluck --skip-existing
```

## CSV Format

### Sheerpluck CSV Structure

The import expects a CSV file with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| ID | Unique identifier | 1 |
| Name | Composer name (Last, First) | "Mozart, Wolfgang Amadeus" |
| Birth Year | Birth year (YYYY) | 1756 |
| Death Year | Death year (YYYY) or empty | 1791 |
| Country | Country name | Austria |
| Work | Work title | "Eine kleine Nachtmusik" |
| Instrumentation | Instrumentation type | "Solo" |

### Data Cleaning

The import automatically handles:

- **Name normalization**: Removes accents, converts to lowercase for search
- **Name parsing**: Splits "Last, First" into separate fields
- **Year validation**: Handles approximate years (ca. 1500, 1750?)
- **Country normalization**: Maps USA → United States, UK → United Kingdom
- **Deduplication**: Checks for existing composers and works

## Import Process

### What Happens During Import

1. **Data Source Registration**
   - Creates or finds "Sheerpluck" data source record

2. **Batch Processing**
   - Processes CSV in batches of 100 rows
   - Uses database transactions for reliability

3. **Composer Processing**
   - Checks if composer exists (by name + birth year)
   - Creates new composer or updates existing
   - Parses name into first/last components
   - Links to country

4. **Work Creation**
   - Creates work record linked to composer
   - Links to instrumentation category
   - Marks as `needs_review=True` for manual verification
   - Stores original Sheerpluck ID as `external_id`

5. **Caching**
   - Caches composers, countries, and instrumentation categories
   - Reduces database queries for better performance

### Import Statistics

After import completes, you'll see statistics like:

```
==================================================
IMPORT COMPLETE
==================================================
Total rows processed: 67164
Composers created: 12543
Composers updated: 234
Works created: 67164
Works skipped: 0
Errors: 0
==================================================
```

## Data Quality

### Auto-Flagged for Review

Imported records are automatically marked with `needs_review=True`. This allows staff to:

1. Review composer biographies
2. Verify work metadata
3. Add missing information
4. Correct any import errors
5. Link to external resources (IMSLP, YouTube, scores)

### Admin Portal Review

Access the Django admin at `/admin/` to review imported data:

- **Composers**: Filter by `needs_review=True`
- **Works**: Filter by `needs_review=True`
- Bulk actions available for verification

## Deduplication Strategy

### Composer Deduplication

Composers are identified by:
- Full name (exact match)
- Birth year (exact match)

If both match, the existing composer is updated rather than creating a duplicate.

### Work Deduplication

When using `--skip-existing`:
- Works are identified by `external_id` + `data_source`
- Existing works are skipped
- Use this for incremental updates

## Error Handling

### Common Errors

**Missing required fields:**
- Composer name or work title missing
- Row is skipped, error logged

**Database connection issues:**
- Check `.env` configuration
- Verify MySQL is running
- Check database credentials

**Invalid data:**
- Years outside 1000-2100 range set to None
- Invalid characters are stripped
- Errors logged but import continues

### Error Logs

Errors are written to:
- Console output during import
- Django logs (if configured)
- Statistics show total error count

## Performance

### Import Speed

- Processes ~100 rows/second (typical)
- 67,000 rows complete in ~10-15 minutes
- Uses batch processing and caching for efficiency

### Optimization Tips

1. Ensure MySQL is properly indexed (migrations handle this)
2. Run import during off-hours for production
3. Use `--skip-existing` for updates to skip unchanged data

## Post-Import Tasks

### 1. Verify Data Quality

```bash
python manage.py shell
```

```python
from music.models import Composer, Work

# Check total counts
print(f"Composers: {Composer.objects.count()}")
print(f"Works: {Work.objects.count()}")

# Check works needing review
print(f"Needs review: {Work.objects.filter(needs_review=True).count()}")
```

### 2. Admin Review

1. Log into admin portal: `/admin/`
2. Review composers marked for review
3. Add biographies, photos, links
4. Verify work metadata
5. Mark as `is_verified=True` after review

### 3. Populate Search Index

The `WorkSearchIndex` table can be populated manually or via signals (future enhancement).

## Testing

### Run Unit Tests

```bash
python manage.py test music.tests.DataCleaningTests
```

### Test Import with Sample Data

1. Create a small test CSV
2. Run with `--dry-run` first
3. Check validation errors
4. Import to test database
5. Verify in admin portal

## Troubleshooting

### Import Fails Immediately

- Check database connection in `.env`
- Verify MySQL database exists
- Run `python manage.py check`

### Import Slow

- Check database indexes: `python manage.py showmigrations`
- Monitor MySQL performance
- Consider increasing batch_size in code

### Duplicate Data

- Use `--skip-existing` for updates
- Check deduplication logic in `_get_or_create_composer()`
- Review composer matching criteria

### Character Encoding Issues

- Ensure CSV is UTF-8 encoded
- Check for BOM (byte order mark) at file start
- Try opening/re-saving CSV in UTF-8

## Future Enhancements

- [ ] IMSLP data import
- [ ] Automatic search index population
- [ ] Progress bar for large imports
- [ ] Parallel processing for faster imports
- [ ] Web-based upload interface
- [ ] Scheduled incremental updates
- [ ] Data validation reports
- [ ] Duplicate detection improvements

## Support

For issues or questions:
- Check Django logs
- Review import statistics
- Consult admin portal for data quality
- See README.md for setup help
