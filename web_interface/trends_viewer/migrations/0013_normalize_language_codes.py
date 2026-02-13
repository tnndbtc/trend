# Generated manually on 2026-02-14
# Migration to normalize language codes in TrendTranslationStatus

from django.db import migrations


def normalize_language_codes(apps, schema_editor):
    """
    Normalize language codes in TrendTranslationStatus to match the format
    used by the middleware and views (e.g., 'zh' -> 'zh-Hans', 'en' -> 'en-US').

    This fixes a bug where translations were being saved with unnormalized codes
    but queried with normalized codes, causing "Translation Not Available" errors.
    """
    TrendTranslationStatus = apps.get_model('trends_viewer', 'TrendTranslationStatus')

    # Language code normalization mapping (same as in middleware.py and views.py)
    LANG_CODE_MAP = {
        # Simplified codes -> Full locale codes
        'en': 'en-US',
        'zh': 'zh-Hans',  # Simplified Chinese
        'zh-cn': 'zh-Hans',
        'zh-tw': 'zh-Hant',  # Traditional Chinese
        'es': 'es-ES',
        'fr': 'fr-FR',
        'de': 'de-DE',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'ru': 'ru-RU',
        'pt': 'pt-BR',
        'it': 'it-IT',
        'ar': 'ar-SA',
        'hi': 'hi-IN',
    }

    # Track updates for logging
    updates = {}

    # Get all TrendTranslationStatus records
    all_statuses = TrendTranslationStatus.objects.all()

    for status in all_statuses:
        old_lang = status.language

        # Check if language needs normalization
        if old_lang in LANG_CODE_MAP:
            new_lang = LANG_CODE_MAP[old_lang]

            # Check if a record with the normalized language already exists
            # This prevents unique constraint violations
            existing = TrendTranslationStatus.objects.filter(
                trend=status.trend,
                language=new_lang
            ).exclude(id=status.id).first()

            if existing:
                # If a normalized version exists, delete the old unnormalized one
                # (keep the one that's more likely to be up-to-date)
                if existing.translated and not status.translated:
                    # Keep existing (it's translated), delete current (not translated)
                    status.delete()
                    updates[f"{old_lang} (deleted duplicate)"] = updates.get(f"{old_lang} (deleted duplicate)", 0) + 1
                elif status.translated and not existing.translated:
                    # Keep current (it's translated), delete existing (not translated)
                    existing.delete()
                    status.language = new_lang
                    status.save()
                    updates[old_lang] = updates.get(old_lang, 0) + 1
                else:
                    # Both have same translation status, keep existing, delete current
                    status.delete()
                    updates[f"{old_lang} (deleted duplicate)"] = updates.get(f"{old_lang} (deleted duplicate)", 0) + 1
            else:
                # No duplicate, safe to update
                status.language = new_lang
                status.save()
                updates[old_lang] = updates.get(old_lang, 0) + 1

    # Log the updates
    if updates:
        print("\n[MIGRATION 0013] Normalized language codes in TrendTranslationStatus:")
        for old_lang, count in updates.items():
            if "deleted" in old_lang:
                print(f"  - {old_lang}: {count} records")
            else:
                new_lang = LANG_CODE_MAP.get(old_lang, old_lang)
                print(f"  - '{old_lang}' -> '{new_lang}': {count} records")
    else:
        print("\n[MIGRATION 0013] No language codes needed normalization")


def reverse_normalize(apps, schema_editor):
    """
    Reverse migration: Convert normalized language codes back to simplified ones.
    Note: This may not be perfectly reversible if duplicate records were deleted.
    """
    TrendTranslationStatus = apps.get_model('trends_viewer', 'TrendTranslationStatus')

    # Reverse mapping
    REVERSE_MAP = {
        'en-US': 'en',
        'zh-Hans': 'zh',
        'zh-Hant': 'zh-tw',
        'es-ES': 'es',
        'fr-FR': 'fr',
        'de-DE': 'de',
        'ja-JP': 'ja',
        'ko-KR': 'ko',
        'ru-RU': 'ru',
        'pt-BR': 'pt',
        'it-IT': 'it',
        'ar-SA': 'ar',
        'hi-IN': 'hi',
    }

    for status in TrendTranslationStatus.objects.all():
        if status.language in REVERSE_MAP:
            old_lang = status.language
            new_lang = REVERSE_MAP[old_lang]

            # Check for duplicates (same as forward migration)
            existing = TrendTranslationStatus.objects.filter(
                trend=status.trend,
                language=new_lang
            ).exclude(id=status.id).first()

            if not existing:
                status.language = new_lang
                status.save()


class Migration(migrations.Migration):

    dependencies = [
        ('trends_viewer', '0012_add_celery_worker_concurrency'),
    ]

    operations = [
        migrations.RunPython(normalize_language_codes, reverse_normalize),
    ]
