#!/usr/bin/env python
"""
Check what language codes exist in the database
"""
import sqlite3

# Database path
DB_PATH = '/home/tnnd/data/code/trend/web_interface/db/db.sqlite3'

def main():
    print("=" * 70)
    print("Checking language codes in database")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check TranslatedContent
        print("\n📊 TranslatedContent:")
        cursor.execute("SELECT DISTINCT target_language, COUNT(*) FROM trends_viewer_translatedcontent GROUP BY target_language")
        results = cursor.fetchall()
        if results:
            for lang, count in results:
                print(f"   target_language='{lang}': {count} records")
        else:
            print("   No records found")

        cursor.execute("SELECT DISTINCT source_language, COUNT(*) FROM trends_viewer_translatedcontent GROUP BY source_language")
        results = cursor.fetchall()
        if results:
            print("\n   Source languages:")
            for lang, count in results:
                print(f"   source_language='{lang}': {count} records")

        # Check TrendTranslationStatus
        print("\n📊 TrendTranslationStatus:")
        cursor.execute("SELECT DISTINCT language, COUNT(*) FROM trends_viewer_trendtranslationstatus GROUP BY language")
        results = cursor.fetchall()
        if results:
            for lang, count in results:
                print(f"   language='{lang}': {count} records")
        else:
            print("   No records found")

        # Check CollectedTopic
        print("\n📊 CollectedTopic:")
        cursor.execute("SELECT DISTINCT language, COUNT(*) FROM trends_viewer_collectedtopic GROUP BY language")
        results = cursor.fetchall()
        if results:
            for lang, count in results:
                print(f"   language='{lang}': {count} records")
        else:
            print("   No records found")

        # Total record counts
        print("\n📈 Total records:")
        cursor.execute("SELECT COUNT(*) FROM trends_viewer_translatedcontent")
        print(f"   TranslatedContent: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM trends_viewer_trendtranslationstatus")
        print(f"   TrendTranslationStatus: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM trends_viewer_collectedtopic")
        print(f"   CollectedTopic: {cursor.fetchone()[0]}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
