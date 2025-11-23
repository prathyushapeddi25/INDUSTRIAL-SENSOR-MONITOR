# Anomaly Detection Reliability & Failure Handling

## Problem Statement

**What happens when an anomaly is detected but the database save fails?**

Without proper handling, the anomaly would be **lost forever** because:
1. Anomaly detection happens in-memory
2. If database commit fails, the transaction is rolled back
3. The simulator continues generating new data
4. The UI never sees the anomaly

## Solution Architecture

### Multi-Layer Reliability Strategy

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DETECT ANOMALY (In-Memory)                               │
│    ↓                                                         │
│ 2. TRY: Save to Database                                    │
│    ├─ SUCCESS → Return to client                            │
│    └─ FAILURE → Add to Retry Queue (continue below)         │
│                                                              │
│ 3. RETRY QUEUE (Background Worker)                          │
│    ├─ Exponential backoff (1s, 2s, 4s...)                   │
│    ├─ Max 3 retry attempts                                  │
│    └─ SUCCESS → Remove from queue                           │
│        FAILURE → Continue to Dead Letter Queue              │
│                                                              │
│ 4. DEAD LETTER QUEUE (Persistent Storage)                   │
│    ├─ Save to disk (failed_measurements.jsonl)              │
│    └─ Recover on next startup                               │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Retry Handler (`retry_handler.py`)

**Features:**
- Background worker thread for asynchronous retries
- Exponential backoff to avoid overwhelming the database
- Thread-safe queue for concurrent access
- Dead letter queue (JSONL file) for persistent backup

**Key Methods:**
- `add_failed_measurement()` - Add to retry queue
- `_retry_worker()` - Background thread processing retries
- `save_to_dead_letter_queue()` - Persistent backup
- `recover_from_dead_letter_queue()` - Startup recovery

### 2. API Integration (`api.py`)

**Changes to ingestion endpoints:**

```python
# Before: Fails and loses data
session.commit()  # If this fails, anomaly is lost!

# After: Graceful failure handling
try:
    session.commit()
    return {"status": "success", "id": db_measurement.id}
except Exception as db_error:
    retry_handler.add_failed_measurement(measurement_data)
    return {
        "status": "queued_for_retry",
        "message": "Database temporarily unavailable. Measurement queued."
    }
```

**Startup/Shutdown hooks:**
- On startup: Recover failed measurements from disk
- On shutdown: Stop retry worker gracefully

### 3. Monitoring Endpoints

**GET /health**
```json
{
  "status": "healthy",
  "database": "healthy",
  "retry_queue_size": 0,
  "timestamp": "2025-11-22T10:30:00"
}
```

**GET /stats**
```json
{
  "total_measurements": 1500,
  "total_anomalies": 45,
  "retry_queue_size": 2,
  "retry_queue_status": "pending"
}
```

## Failure Scenarios & Handling

### Scenario 1: Temporary Database Outage (30 seconds)

**Timeline:**
```
T+0s   : Anomaly detected, DB save fails
T+0s   : Added to retry queue, client gets "queued_for_retry"
T+1s   : First retry attempt (fails)
T+3s   : Second retry attempt (fails, 2s backoff)
T+7s   : Third retry attempt (fails, 4s backoff)
T+7s   : Saved to dead letter queue
T+30s  : Database comes back online
T+60s  : Admin checks /health, sees degraded status
T+60s  : Admin manually triggers recovery OR waits for next restart
T+61s  : Recovery process reads dead letter queue
T+61s  : Successfully saves measurement to database
T+61s  : UI updated with anomaly data
```

**Result:** ✅ **No data loss**

### Scenario 2: Database Connection Lost During Batch Insert

**What happens:**
1. Batch of 3 measurements arrives
2. First 2 save successfully
3. Database connection drops
4. Third measurement added to retry queue
5. Retry worker attempts to save in background
6. Client receives partial success response

**Result:** ✅ **Graceful degradation, no data loss**

### Scenario 3: Complete System Crash

**What happens:**
1. System crashes before retry worker processes queue
2. In-memory retry queue is lost
3. BUT: Dead letter queue is persisted to disk
4. On next startup: `recover_from_dead_letter_queue()` runs
5. All failed measurements are recovered and saved

**Result:** ✅ **Data persisted to disk, recovered on restart**

### Scenario 4: UI Not Updated

**What happens:**
1. Measurement saved to retry queue
2. UI polls `/data` and `/anomalies` endpoints
3. Data not yet in database (still in retry queue)
4. UI shows slightly stale data
5. Once retry succeeds, next UI refresh shows the anomaly

**Result:** ✅ **Eventual consistency, acceptable delay**

## Configuration Options

### Retry Settings
```python
retry_handler = FailedOperationHandler(
    db_session_factory=lambda: get_session(engine),
    max_retries=3,                    # How many retry attempts
    dead_letter_path='failed_measurements.jsonl'  # Where to save failed data
)
```

### Exponential Backoff
- Retry 1: 1 second delay
- Retry 2: 2 second delay
- Retry 3: 4 second delay
- After 3 failures: Save to dead letter queue

## Operational Procedures

### Monitoring

**Check system health:**
```bash
curl http://localhost:8000/health
```

**Check retry queue status:**
```bash
curl http://localhost:8000/stats
```

### Recovery

**Manual recovery from dead letter queue:**
```python
# In Python console or script
from retry_handler import get_handler
handler = get_handler()
handler.recover_from_dead_letter_queue()
```

**Check dead letter queue file:**
```bash
cat backend/failed_measurements.jsonl
```

### Alerts

**Set up monitoring for:**
- `retry_queue_size > 10` → Database might be slow
- `dead_letter_queue exists` → Past failures need recovery
- `/health status != "healthy"` → System degraded

## Benefits

1. **Zero Data Loss** - Even if database is down, data is preserved
2. **Graceful Degradation** - System continues operating during failures
3. **Automatic Recovery** - Background worker handles transient failures
4. **Persistence** - Dead letter queue survives crashes
5. **Observability** - Health checks show system status
6. **Client Transparency** - Client knows when data is queued vs. saved

## Trade-offs

1. **Eventual Consistency** - Small delay before UI shows retried data
2. **Additional Complexity** - More code to maintain
3. **Disk I/O** - Dead letter queue writes to disk
4. **Memory Usage** - Retry queue held in memory

## Testing Failure Scenarios

**Simulate database failure:**
```python
# In testing, temporarily disable database
import time
# Stop database service
time.sleep(30)  # Simulate 30s outage
# Restart database
# Check /health to see recovery
```

**Verify dead letter queue:**
```bash
# Force a failure by corrupting database
# Check if failed_measurements.jsonl is created
# Restart service
# Verify measurements recovered
```

## Future Enhancements

1. **Persistent Queue** - Use Redis or RabbitMQ instead of in-memory queue
2. **Circuit Breaker** - Stop retrying if database consistently fails
3. **Metrics** - Prometheus metrics for retry rates
4. **Admin UI** - Dashboard to view and manage retry queue
5. **Webhooks** - Alert administrators when anomalies can't be saved

## Conclusion

The retry handler ensures that **detected anomalies are never lost**, even during database failures. The multi-layer approach (in-memory queue → disk backup → startup recovery) provides robust data reliability while maintaining system availability.
