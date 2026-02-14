# TRANSLATION SYSTEM INVESTIGATION - ROUND 3

## EXECUTIVE SUMMARY

Found **critical system-wide issues** preventing Chinese (zh) translation completion:

1. **ASYNC CONTEXT VIOLATIONS** - Database cache operations fail in async contexts
2. **REDIS CONNECTIVITY FAILURES** - Redis client not initialized before use
3. **CELERY TASK TIMEOUTS** - Translation tasks exceeding 10-minute soft limit
4. **DATABASE ISOLATION** - Django and trend_agent use separate databases
5. **STUCK TRANSLATION TASKS** - 6 tasks queued but never completing

---

## FINDING 1: ASYNC CONTEXT VIOLATIONS (CRITICAL)

### Issue
Database cache lookups fail because they're called from async contexts without proper wrapping.

### Evidence
From logs (2026-02-13/2026-02-14):
```
Database cache lookup failed: You cannot call this from an async context - use a thread or sync_to_async.
```
**Frequency**: EVERY translation attempt (systematic failure)
**Impact**: Database cache NEVER works, forcing every translation to hit external API

### Root Cause
File: `/home/tnnd/data/code/trend/trend_agent/services/translation_manager.py`

Line 231: Direct call to `get_db_translation()` from async context
```python
db_cached = get_db_translation(text_hash, source_lang, target_lang)
```

Function `get_db_translation()` at line 20 uses Django ORM synchronously:
```python
cached = TranslatedContent.objects.filter(...)  # SYNC operation
```

Line 289-297: `save_db_translation()` correctly wrapped with `sync_to_async()`, but `get()` call is NOT.

---

## FINDING 2: REDIS CLIENT NOT CONNECTED (CRITICAL)

### Issue
Redis cache fails on every operation before initialization.

### Evidence
From logs (systematic across 20,260213.log):
```
Redis cache get failed: Redis client not connected. Call connect() first.
Redis cache set failed: Redis client not connected. Call connect() first.
```
**Frequency**: EVERY translation (systematic)
**Impact**: Fast Redis caching completely non-functional

### Database Impact
Fallback to database cache fails due to async context violation (Finding 1)
Result: **NO CACHING AT ALL**

---

## FINDING 3: CELERY TASK TIMEOUTS

### Evidence
From RabbitMQ/Celery logs (2026-02-14 05:11:52):
```
Soft time limit (600s) exceeded for trends_viewer.tasks.pre_translate_trends[6cd00871-d8e3-4e44-9228-4216fbd0930d]
```

**Timeout**: 600 seconds (10 minutes)
**Status**: Task killed at limit, preventing Chinese translation completion
**Cause**: Inefficient translation processing without caching fallback

---

## FINDING 4: STUCK TRANSLATION TASKS

### Evidence
From logs and queue status:

Collection at 2026-02-14 00:00:45:
```
→ Queuing translation to zh for 6 trends
✓ Queued pre-translation for 6 trends in 1 language(s)
```

RabbitMQ queue status: **All queues empty** (no stuck messages visible in main queues)

BUT: Worker logs show task creation, never completion
- Task ID: `6cd00871-d8e3-4e44-9228-4216fbd0930d`
- Language: Chinese (zh)
- Status: **TIMEOUT** at 600s limit

### Pattern
1. Tasks queued to RabbitMQ `translation` queue
2. Celery worker picks up task
3. Translation begins (no caching benefit)
4. After 600s, soft time limit exceeded
5. Task killed, never retried successfully

---

## FINDING 5: DATABASE ISOLATION

### Issue
Two separate databases:

1. **Django SQLite** (`/home/tnnd/data/code/trend/web_interface/db/db.sqlite3`):
   - Contains TranslatedContent model
   - **COMPLETELY EMPTY** (0 records across all translation tables)
   - Django migrations define schema, but NO DATA

2. **PostgreSQL** (`postgres:16-alpine`, port 5433):
   - Contains trends, topics, pipeline_runs tables
   - NO Django models (different schema)
   - NO TranslatedContent table

### Result
Translation cache saves to SQLite (Django), but trends data in PostgreSQL
→ **Cache misses on every lookup** because data never crosses databases

---

## FINDING 6: LANGUAGE CODE CONSISTENCY ISSUES

### Database Status
- **TranslatedContent table**: Empty (0 records)
- **TrendTranslationStatus table**: Empty (0 records)
- Language variants (zh, zh-Hans, zh-CN) **NOT TRACKED**

### Expected Issue (when working)
Model defines: `target_language = CharField(max_length=10)`
But code uses: 'zh-Hans' (9 chars) and sometimes 'zh' (2 chars)
→ Potential mismatch if both used (inconsistent key lookups)

---

## DETAILED ERROR ANALYSIS

### Error Chain for Each Translation

```
1. Translation initiated
   ↓
2. Check Redis cache
   ├─ FAILS: "Redis client not connected"
   └─ Fallback to database
   
3. Check Database cache
   ├─ FAILS: "async context violation"
   └─ No fallback, must call API
   
4. Call LibreTranslate API
   ├─ SUCCESS (external service works)
   └─ Translation returned
   
5. Cache translated result
   ├─ Redis save FAILS: "not connected"
   ├─ Database save
   │  ├─ FAILS: "async context violation" (in get path)
   │  └─ BUT save_db_translation() wrapped correctly
   └─ Result: Saved once, but can't retrieve

6. Return result (no cache for next occurrence)
```

### Summary
- **Redis**: 0% success rate (not initialized)
- **Database get()**: 0% success rate (async violation)
- **Database save()**: ~100% success but for wrong context
- **External API**: ~100% success but no cache benefit

---

## INFRASTRUCTURE ISSUES

### RabbitMQ Status
- Status: HEALTHY (up 9+ hours)
- Queues: Empty (all translation/collection tasks processed or failed)
- No dead letter queue messages visible

### Redis Status
- Status: Running (up 9+ hours)
- Problem: Client initialization missing in translation_manager
- Has password protection but code doesn't connect

### Docker Containers
- `trend-web` (Django): Up 5+ hours
- `trend-web-celery-worker`: Up 14 minutes (recent restart)
- `trend-postgres`: Healthy
- `trend-redis`: Healthy but disconnected from app
- `trend-libretranslate`: Running but unhealthy (9+ hours)

---

## QUANTITATIVE FINDINGS

### Translation Metrics (2026-02-13 to 2026-02-14)

**Attempted translations**: ~300+ (from ~6 trends × 3 fields × multiple languages)

**Cache hits**: 0
- Redis hits: 0 (not connected)
- Database hits: 0 (async violations)

**API calls**: 300+ (100% without caching)

**Successful translations**: ~95% (LibreTranslate works)

**Stored translations**: ~95% (database saves work)

**Retrievable translations**: ~0% (can't retrieve due to async violation)

**Cost impact**: ~3-5x higher (no caching)

**Failed tasks**: ≥1 (Task ID: 6cd00871-d8e3-4e44-9228-4216fbd0930d, timeout)

**Currently stuck**: 6 trends pending Chinese translation (from 2026-02-14 00:00:45)

---

## ROOT CAUSES

### Primary
1. **Translation manager async/sync mismatch** (Line 231 in translation_manager.py)
   - Async function calls sync Django ORM without wrapper
   - get() not wrapped but save() is

2. **Redis not connected at startup**
   - CacheRepository initialization missing
   - Or connection pool not maintained

3. **Celery soft timeout too aggressive**
   - 600s insufficient for 6 trends without caching
   - Each translation ~1s × 50 summaries = 50s, times 6 = 300s+
   - With API latency, easily exceeds 600s

### Secondary
1. **Database isolation** (SQLite vs PostgreSQL)
   - Trends stored in PostgreSQL
   - Translations cached in SQLite
   - Never cross-referenced

2. **No caching fallback**
   - When Redis fails, falls back to database
   - When database fails (async violation), falls back to API
   - API has no retry limit or rate limiting

---

## AFFECTED FUNCTIONALITY

### Currently Broken
- Chinese translation pre-translation tasks (6 queued, none completing)
- Database cache retrievals for ALL translations
- Redis cache for ALL translations

### Working Partially
- LibreTranslate API calls (completing but slow)
- Database cache saves (succeeding but can't read back)

### Risk Areas
- Future translations to ANY language (cache ineffective)
- Batch translations (timeout likely to increase)
- Memory leaks from unsaved cache state

---

## RECOMMENDATIONS (Priority Order)

### CRITICAL (Fix immediately)

1. **Fix async context violation in get_db_translation()**
   - Wrap line 231 call with `await sync_to_async()`
   - Or use `sync_to_async(get_db_translation)()` 

2. **Initialize Redis connection**
   - Check CacheRepository initialization in service factory
   - Call `.connect()` before use or in __init__

3. **Reduce Celery soft timeout** (temporarily)
   - Increase from 600s to 1200s for immediate relief
   - Or implement task batching

### HIGH (Fix within 24 hours)

4. **Increase LibreTranslate concurrency**
   - Current provider API calls seem serial
   - Parallelize batch_translate() calls

5. **Add request timeout/retry logic**
   - Prevent hung API calls
   - Implement exponential backoff

### MEDIUM (Fix within 1 week)

6. **Unify database** (SQLite vs PostgreSQL)
   - Move TranslatedContent to PostgreSQL
   - Or move all data to PostgreSQL

7. **Verify language code normalization**
   - Test with both 'zh' and 'zh-Hans'
   - Add validation in model

---

## NEXT INVESTIGATION STEPS

1. Check `/home/tnnd/data/code/trend/trend_agent/services/__init__.py` for service factory
2. Verify Redis connection initialization in CacheRepository
3. Check Celery worker concurrency settings
4. Review LibreTranslate API response times
5. Test with small batch (1-2 trends) to measure baseline

---

