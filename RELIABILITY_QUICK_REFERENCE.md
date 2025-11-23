# Anomaly Detection Failure Recovery - Quick Reference

## What Happens When Database Fails?

### ❌ WITHOUT Retry Handler (Old Approach)
```
┌──────────────┐
│   Anomaly    │
│   Detected   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Try to Save  │
│ to Database  │
└──────┬───────┘
       │
       ▼
    FAILS! 💥
       │
       ▼
┌──────────────┐
│   Data is    │
│   LOST! 😱   │
└──────────────┘

Result: Anomaly never saved, UI never updated
```

### ✅ WITH Retry Handler (New Approach)
```
┌──────────────────────────────────────────────────────────┐
│                     Anomaly Detected                      │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Try to Save to DB   │
              └──────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼ SUCCESS        ▼ FAILURE        │
┌──────────────┐  ┌──────────────────┐   │
│   Saved!     │  │ Add to Retry     │   │
│   Return ID  │  │ Queue (In-Memory)│   │
└──────────────┘  └──────────┬───────┘   │
                             │            │
                             ▼            │
                  ┌─────────────────────┐ │
                  │ Background Worker   │ │
                  │ Retries with        │ │
                  │ Exponential Backoff │ │
                  └──────────┬──────────┘ │
                             │            │
              ┌──────────────┼──────────┐ │
              │              │          │ │
              ▼ SUCCESS      ▼ FAIL    │ │
    ┌─────────────────┐  ┌──────────┐ │ │
    │  Saved to DB!   │  │  Try 2   │ │ │
    │  UI gets data   │  │  (2s)    │ │ │
    │  next refresh   │  └────┬─────┘ │ │
    └─────────────────┘       │       │ │
                              ▼       │ │
                         ┌──────────┐ │ │
                         │  Try 3   │ │ │
                         │  (4s)    │ │ │
                         └────┬─────┘ │ │
                              │       │ │
              ┌───────────────┼───────┘ │
              │               │         │
              ▼ SUCCESS       ▼ FAIL   │
    ┌─────────────────┐  ┌───────────────────┐
    │  Saved to DB!   │  │ Save to Dead      │
    │  UI gets data   │  │ Letter Queue      │
    │  next refresh   │  │ (Disk - JSONL)    │
    └─────────────────┘  └─────────┬─────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │ On Next Startup:    │
                         │ Recover & Save!     │
                         │ UI eventually sees  │
                         └─────────────────────┘

Result: ✅ NO DATA LOSS - Guaranteed!
```

## Key Components

### 1. In-Memory Retry Queue
- **Purpose**: Fast retry for transient failures
- **Lifespan**: Lost if system crashes
- **Max Retries**: 3 attempts with exponential backoff

### 2. Dead Letter Queue (Disk)
- **Purpose**: Persistent backup for extended outages
- **Lifespan**: Survives system crashes
- **Location**: `backend/failed_measurements.jsonl`
- **Format**: One JSON object per line

### 3. Background Worker
- **Purpose**: Automatic retry processing
- **Thread**: Runs in background, doesn't block API
- **Backoff**: 1s → 2s → 4s between retries

## Example Dead Letter Queue File

```jsonl
{"timestamp": "2025-11-22T10:30:45", "tag": "fermenter_temp", "value": 46.5, "is_anomaly": true, "retry_count": 3, "first_failed_at": "2025-11-22T10:30:45"}
{"timestamp": "2025-11-22T10:30:46", "tag": "fermenter_ph", "value": 8.1, "is_anomaly": true, "retry_count": 3, "first_failed_at": "2025-11-22T10:30:46"}
```

## Monitoring Commands

**Check if system is healthy:**
```bash
curl http://localhost:8000/health
```

**Check how many measurements are queued for retry:**
```bash
curl http://localhost:8000/stats
```

**View failed measurements on disk:**
```bash
cat backend/failed_measurements.jsonl
```

## Response Types

### Normal Success
```json
{
  "status": "success",
  "id": 12345,
  "is_anomaly": true
}
```

### Database Temporarily Unavailable
```json
{
  "status": "queued_for_retry",
  "message": "Database temporarily unavailable. Measurement queued for retry.",
  "is_anomaly": true
}
```

## Timeline Example

**Scenario: Database is down for 5 minutes**

```
10:00:00 - Anomaly detected (temp = 46.5°C)
10:00:00 - DB save fails → Added to retry queue
10:00:01 - Retry #1 fails
10:00:03 - Retry #2 fails (2s backoff)
10:00:07 - Retry #3 fails (4s backoff)
10:00:07 - Saved to dead_letter_queue.jsonl on disk
10:05:00 - Database comes back online
10:05:30 - System restarted (or manual recovery triggered)
10:05:30 - Recovery reads dead_letter_queue.jsonl
10:05:31 - Anomaly successfully saved to database!
10:05:35 - UI refresh picks up the anomaly
10:05:35 - Dead letter queue file deleted (success!)
```

**Result: Anomaly detected at 10:00:00, visible in UI at 10:05:35**
- **5 minute delay** but **ZERO data loss** ✅

## Benefits Summary

| Feature | Benefit |
|---------|---------|
| **Retry Queue** | Handles transient failures automatically |
| **Exponential Backoff** | Prevents overwhelming recovering database |
| **Dead Letter Queue** | Survives crashes and long outages |
| **Startup Recovery** | Automatically processes failed measurements |
| **Health Endpoint** | Monitor system status in real-time |
| **Client Transparency** | API tells client when data is queued |

## When to Check Logs

**Check logs if:**
- ⚠️ `/health` returns `degraded`
- ⚠️ `/stats` shows `retry_queue_size > 0`
- ⚠️ `failed_measurements.jsonl` file exists
- ⚠️ UI shows data gaps or missing anomalies

**Log messages to look for:**
- `⚠ Measurement queued for retry:` - Database write failed
- `✓ Successfully retried:` - Retry succeeded
- `✗ Max retries exceeded` - Saved to dead letter queue
- `✓ Recovered X measurements` - Startup recovery succeeded
