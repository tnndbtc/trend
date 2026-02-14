#!/usr/bin/env python
"""
Update language codes in database from 'zh' to 'zh-Hans'
"""
import sqlite3
import os

# Database path
DB_PATH = '/home/tnnd/data/code/trend/web_interface/db/db.sqlite3'

def main():
    print("=" * 70)
    print("Updating language codes from 'zh' to 'zh-Hans' in SQLite database")
    print("=" * 70)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Check current counts
        print("\n📊 Current state:")
        cursor.execute("SELECT COUNT(*) FROM trends_viewer_translatedcontent WHERE target_language = 'zh'")
        tc_target_count = cursor.fetchone()[0]
        print(f"   TranslatedContent with target_language='zh': {tc_target_count}")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_translatedcontent WHERE source_language = 'zh'")
        tc_source_count = cursor.fetchone()[0]
        print(f"   TranslatedContent with source_language='zh': {tc_source_count}")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_trendtranslationstatus WHERE language = 'zh'")
        tts_count = cursor.fetchone()[0]
        print(f"   TrendTranslationStatus with language='zh': {tts_count}")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_collectedtopic WHERE language = 'zh'")
        ct_count = cursor.fetchone()[0]
        print(f"   CollectedTopic with language='zh': {ct_count}")

        # 2. Execute updates
        print("\n🔄 Executing SQL updates...")

        # Update TranslatedContent target_language
        cursor.execute("UPDATE trends_viewer_translatedcontent SET target_language = 'zh-Hans' WHERE target_language = 'zh'")
        print(f"   ✅ Updated {cursor.rowcount} TranslatedContent.target_language records")

        # Update TranslatedContent source_language
        cursor.execute("UPDATE trends_viewer_translatedcontent SET source_language = 'zh-Hans' WHERE source_language = 'zh'")
        print(f"   ✅ Updated {cursor.rowcount} TranslatedContent.source_language records")

        # Update TrendTranslationStatus
        cursor.execute("UPDATE trends_viewer_trendtranslationstatus SET language = 'zh-Hans' WHERE language = 'zh'")
        print(f"   ✅ Updated {cursor.rowcount} TrendTranslationStatus records")

        # Update CollectedTopic
        cursor.execute("UPDATE trends_viewer_collectedtopic SET language = 'zh-Hans' WHERE language = 'zh'")
        print(f"   ✅ Updated {cursor.rowcount} CollectedTopic records")

        # Commit changes
        conn.commit()
        print("\n💾 Changes committed to database")

        # 3. Verify updates
        print("\n✅ Verification:")
        cursor.execute("SELECT COUNT(*) FROM trends_viewer_translatedcontent WHERE target_language = 'zh'")
        print(f"   TranslatedContent with target_language='zh': {cursor.fetchone()[0]} (should be 0)")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_translatedcontent WHERE target_language = 'zh-Hans'")
        print(f"   TranslatedContent with target_language='zh-Hans': {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_trendtranslationstatus WHERE language = 'zh'")
        print(f"   TrendTranslationStatus with language='zh': {cursor.fetchone()[0]} (should be 0)")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_trendtranslationstatus WHERE language = 'zh-Hans'")
        print(f"   TrendTranslationStatus with language='zh-Hans': {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_collectedtopic WHERE language = 'zh'")
        print(f"   CollectedTopic with language='zh': {cursor.fetchone()[0]} (should be 0)")

        cursor.execute("SELECT COUNT(*) FROM trends_viewer_collectedtopic WHERE language = 'zh-Hans'")
        print(f"   CollectedTopic with language='zh-Hans': {cursor.fetchone()[0]}")

        print("\n" + "=" * 70)
        print("✅ Database update complete! All 'zh' → 'zh-Hans'")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return 1
    finally:
        cursor.close()
        conn.close()

    return 0

if __name__ == '__main__':
    exit(main())
