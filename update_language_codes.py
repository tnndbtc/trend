#!/usr/bin/env python
"""
Update language codes in database from 'zh' to 'zh-Hans'
Run this from web_interface directory: python ../update_language_codes.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/tnnd/data/code/trend/web_interface')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
django.setup()

from trends_viewer.models import TranslatedContent, TrendTranslationStatus, CollectedTopic

def main():
    print("=" * 60)
    print("Updating language codes from 'zh' to 'zh-Hans'")
    print("=" * 60)

    # Update TranslatedContent
    print("\n1. Updating TranslatedContent...")
    tc_source = TranslatedContent.objects.filter(source_language='zh')
    tc_target = TranslatedContent.objects.filter(target_language='zh')

    print(f"   - Found {tc_source.count()} records with source_language='zh'")
    print(f"   - Found {tc_target.count()} records with target_language='zh'")

    tc_source_updated = tc_source.update(source_language='zh-Hans')
    tc_target_updated = tc_target.update(target_language='zh-Hans')

    print(f"   ✅ Updated {tc_source_updated} source_language records")
    print(f"   ✅ Updated {tc_target_updated} target_language records")

    # Update TrendTranslationStatus
    print("\n2. Updating TrendTranslationStatus...")
    tts = TrendTranslationStatus.objects.filter(language='zh')
    print(f"   - Found {tts.count()} records with language='zh'")

    tts_updated = tts.update(language='zh-Hans')
    print(f"   ✅ Updated {tts_updated} records")

    # Update CollectedTopic
    print("\n3. Updating CollectedTopic...")
    ct = CollectedTopic.objects.filter(language='zh')
    print(f"   - Found {ct.count()} records with language='zh'")

    ct_updated = ct.update(language='zh-Hans')
    print(f"   ✅ Updated {ct_updated} records")

    print("\n" + "=" * 60)
    print("✅ Database update complete!")
    print("=" * 60)

    # Verify
    print("\nVerification:")
    print(f"   TranslatedContent with 'zh': {TranslatedContent.objects.filter(target_language='zh').count()}")
    print(f"   TranslatedContent with 'zh-Hans': {TranslatedContent.objects.filter(target_language='zh-Hans').count()}")
    print(f"   TrendTranslationStatus with 'zh': {TrendTranslationStatus.objects.filter(language='zh').count()}")
    print(f"   TrendTranslationStatus with 'zh-Hans': {TrendTranslationStatus.objects.filter(language='zh-Hans').count()}")
    print(f"   CollectedTopic with 'zh': {CollectedTopic.objects.filter(language='zh').count()}")
    print(f"   CollectedTopic with 'zh-Hans': {CollectedTopic.objects.filter(language='zh-Hans').count()}")

if __name__ == '__main__':
    main()
