"""
FastAPI application for fermenter monitoring system.
Provides REST API endpoints for data ingestion and querying.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import os

from models import init_database, get_session, Measurement
from anomaly_detector import AnomalyDetector
from retry_handler import FailedOperationHandler, set_handler, get_handler

# Initialize FastAPI app
app = FastAPI(
    title="Fermenter Monitoring API",
    description="API for ingesting and querying fermenter sensor data with anomaly detection",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and anomaly detector
engine = init_database('sqlite:///sensor_data.db')
anomaly_detector = AnomalyDetector(window_size=50, std_threshold=3.0)

# Initialize retry handler for failed database operations
retry_handler = FailedOperationHandler(
    db_session_factory=lambda: get_session(engine),
    max_retries=3,
    dead_letter_path='backend/failed_measurements.jsonl'
)
set_handler(retry_handler)

# Startup event to recover failed measurements and start retry worker
@app.on_event("startup")
async def startup_event():
    """Recover failed measurements on startup and start retry worker."""
    retry_handler.recover_from_dead_letter_queue()
    retry_handler.start_retry_worker()

# Shutdown event to stop retry worker gracefully
@app.on_event("shutdown")
async def shutdown_event():
    """Stop retry worker on shutdown."""
    retry_handler.stop_retry_worker()


# Pydantic models for request/response validation
class MeasurementInput(BaseModel):
    timestamp: str = Field(..., description="ISO format timestamp")
    tag: str = Field(..., description="Tag name (fermenter_temp, fermenter_ph, agitator_rpm)")
    value: float = Field(..., description="Measurement value")


class MeasurementResponse(BaseModel):
    id: int
    timestamp: datetime
    tag: str
    value: float
    is_anomaly: bool
    
    class Config:
        from_attributes = True


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Fermenter Monitoring API",
        "version": "1.0.0",
        "endpoints": {
            "tags": "/tags",
            "data": "/data",
            "anomalies": "/anomalies",
            "dashboard": "/dashboard"
        }
    }


@app.get("/tags")
async def get_tags():
    """
    GET /tags
    Returns a list of available tags.
    """
    session = get_session(engine)
    try:
        # Get distinct tags from measurements table
        distinct_tags = session.query(Measurement.tag).distinct().all()
        tags = [tag[0] for tag in distinct_tags]
        
        # If no measurements yet, return the expected tags
        if not tags:
            tags = ['fermenter_temp', 'fermenter_ph', 'agitator_rpm']
        
        return {"tags": tags}
    finally:
        session.close()


@app.post("/ingest", status_code=201)
async def ingest_measurement(measurement: MeasurementInput):
    """
    Accept incoming readings from the simulator.
    Validates constraints and stores in database.
    """
    session = get_session(engine)
    try:
        # Validate tag name
        valid_tags = ['fermenter_temp', 'fermenter_ph', 'agitator_rpm']
        if measurement.tag not in valid_tags:
            raise HTTPException(status_code=400, detail=f"Invalid tag. Must be one of: {valid_tags}")
        
        # Validate value constraints
        if measurement.tag == 'fermenter_temp' and not (30.0 <= measurement.value <= 50.0):
            raise HTTPException(status_code=400, detail="fermenter_temp must be between 30.0 and 50.0°C")
        elif measurement.tag == 'fermenter_ph' and not (5.0 <= measurement.value <= 9.0):
            raise HTTPException(status_code=400, detail="fermenter_ph must be between 5.0 and 9.0")
        elif measurement.tag == 'agitator_rpm' and not (200.0 <= measurement.value <= 700.0):
            raise HTTPException(status_code=400, detail="agitator_rpm must be between 200.0 and 700.0 RPM")
        
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(measurement.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")
        
        # Detect anomaly
        is_anomaly = anomaly_detector.analyze_reading(measurement.tag, measurement.value)
        
        # Prepare measurement data
        measurement_data = {
            'timestamp': timestamp.isoformat(),
            'tag': measurement.tag,
            'value': measurement.value,
            'is_anomaly': is_anomaly
        }
        
        # Try to create and save measurement
        try:
            db_measurement = Measurement(
                timestamp=timestamp,
                tag=measurement.tag,
                value=measurement.value,
                is_anomaly=is_anomaly
            )
            session.add(db_measurement)
            session.commit()
            session.refresh(db_measurement)
            
            return {
                "status": "success",
                "id": db_measurement.id,
                "is_anomaly": is_anomaly
            }
        except Exception as db_error:
            session.rollback()
            # Add to retry queue instead of losing the data
            retry_handler.add_failed_measurement(measurement_data)
            
            # Still return success to client, but indicate it's queued
            return {
                "status": "queued_for_retry",
                "message": "Database temporarily unavailable. Measurement queued for retry.",
                "is_anomaly": is_anomaly,
                "error": str(db_error)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/ingest/batch", status_code=201)
async def ingest_batch(measurements: List[MeasurementInput]):
    """Ingest multiple measurements at once."""
    session = get_session(engine)
    results = []
    
    try:
        for measurement in measurements:
            # Validate tag name
            valid_tags = ['fermenter_temp', 'fermenter_ph', 'agitator_rpm']
            if measurement.tag not in valid_tags:
                results.append({
                    "tag": measurement.tag,
                    "status": "error",
                    "error": f"Invalid tag. Must be one of: {valid_tags}"
                })
                continue
            
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(measurement.timestamp.replace('Z', '+00:00'))
            except ValueError:
                results.append({
                    "tag": measurement.tag,
                    "status": "error",
                    "error": "Invalid timestamp format"
                })
                continue
            
            # Detect anomaly
            is_anomaly = anomaly_detector.analyze_reading(measurement.tag, measurement.value)
            
            # Prepare measurement data
            measurement_data = {
                'timestamp': timestamp.isoformat(),
                'tag': measurement.tag,
                'value': measurement.value,
                'is_anomaly': is_anomaly
            }
            
            # Try to create measurement
            try:
                db_measurement = Measurement(
                    timestamp=timestamp,
                    tag=measurement.tag,
                    value=measurement.value,
                    is_anomaly=is_anomaly
                )
                session.add(db_measurement)
                session.flush()
                
                results.append({
                    "tag": measurement.tag,
                    "status": "success",
                    "id": db_measurement.id,
                    "is_anomaly": is_anomaly
                })
            except Exception as db_error:
                # Add to retry queue if database save fails
                retry_handler.add_failed_measurement(measurement_data)
                results.append({
                    "tag": measurement.tag,
                    "status": "queued_for_retry",
                    "is_anomaly": is_anomaly,
                    "error": str(db_error)
                })
        
        try:
            session.commit()
        except Exception as commit_error:
            session.rollback()
            # If commit fails, queue all measurements that were added in this batch
            print(f"⚠ Batch commit failed: {commit_error}")
        
        return {
            "status": "success",
            "processed": len(results),
            "results": results
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/data", response_model=List[MeasurementResponse])
async def get_data(
    tag: str = Query(..., description="Tag name to query"),
    from_time: Optional[str] = Query(None, alias="from", description="Start timestamp (ISO format)"),
    to_time: Optional[str] = Query(None, alias="to", description="End timestamp (ISO format)")
):
    """
    GET /data
    Query time-series data points for a given tag and optional time range.
    """
    session = get_session(engine)
    try:
        # Build query
        query = session.query(Measurement).filter(Measurement.tag == tag)
        
        # Apply time filters if provided
        if from_time:
            try:
                from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
                query = query.filter(Measurement.timestamp >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'from' timestamp format")
        
        if to_time:
            try:
                to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
                query = query.filter(Measurement.timestamp <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'to' timestamp format")
        
        # Order by timestamp
        measurements = query.order_by(Measurement.timestamp.desc()).limit(1000).all()
        
        return measurements
    finally:
        session.close()


@app.get("/anomalies", response_model=List[MeasurementResponse])
async def get_anomalies(
    tag: str = Query(..., description="Tag name to query"),
    from_time: Optional[str] = Query(None, alias="from", description="Start timestamp (ISO format)"),
    to_time: Optional[str] = Query(None, alias="to", description="End timestamp (ISO format)")
):
    """
    GET /anomalies
    Returns only the records flagged as anomalies for the given tag and time range.
    """
    session = get_session(engine)
    try:
        # Build query - only anomalies
        query = session.query(Measurement).filter(
            and_(Measurement.tag == tag, Measurement.is_anomaly == True)
        )
        
        # Apply time filters if provided
        if from_time:
            try:
                from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
                query = query.filter(Measurement.timestamp >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'from' timestamp format")
        
        if to_time:
            try:
                to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
                query = query.filter(Measurement.timestamp <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'to' timestamp format")
        
        # Order by timestamp
        anomalies = query.order_by(Measurement.timestamp.desc()).limit(1000).all()
        
        return anomalies
    finally:
        session.close()


@app.get("/stats")
async def get_statistics():
    """Get overall system statistics."""
    session = get_session(engine)
    try:
        total_measurements = session.query(Measurement).count()
        total_anomalies = session.query(Measurement).filter(Measurement.is_anomaly == True).count()
        
        # Get distinct tags
        distinct_tags = session.query(Measurement.tag).distinct().count()
        
        # Get retry queue status
        retry_queue_size = retry_handler.retry_queue.qsize()
        
        return {
            "total_tags": distinct_tags,
            "total_measurements": total_measurements,
            "total_anomalies": total_anomalies,
            "anomaly_rate": round(total_anomalies / total_measurements * 100, 2) if total_measurements > 0 else 0,
            "retry_queue_size": retry_queue_size,
            "retry_queue_status": "pending" if retry_queue_size > 0 else "clear"
        }
    finally:
        session.close()


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns system health including retry queue status.
    """
    try:
        # Check database connectivity
        session = get_session(engine)
        session.execute("SELECT 1")
        session.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    retry_queue_size = retry_handler.retry_queue.qsize()
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "retry_queue_size": retry_queue_size,
        "timestamp": datetime.utcnow().isoformat()
    }


# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the dashboard HTML page."""
        dashboard_file = os.path.join(frontend_path, "dashboard.html")
        if os.path.exists(dashboard_file):
            return FileResponse(dashboard_file)
        raise HTTPException(status_code=404, detail="Dashboard not found")


if __name__ == "__main__":
    import uvicorn
    print("Starting Fermenter Monitoring API...")
    print("API documentation available at: http://localhost:8000/docs")
    print("Dashboard available at: http://localhost:8000/dashboard")
    uvicorn.run(app, host="0.0.0.0", port=8000)

