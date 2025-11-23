# Fermenter Monitoring System

A complete end-to-end system for simulating, ingesting, storing, and monitoring fermenter sensor data with real-time anomaly detection.

## 🏗️ System Architecture

This system consists of the following components:

1. **Data Simulator** (`backend/simulator.py`) - Generates realistic time-series fermenter sensor data once per second
2. **Database Layer** (`backend/models.py`) - Simple `measurements` table with SQLAlchemy ORM
3. **Anomaly Detection** (`backend/anomaly_detector.py`) - Uses rolling mean ± 3σ and threshold rules
4. **REST API** (`backend/api.py`) - FastAPI backend with endpoints: `/tags`, `/data`, `/anomalies`
5. **Ingestion Service** (`backend/ingestion_service.py`) - Continuously runs simulator and pushes data to API
6. **Frontend Dashboard** (`frontend/dashboard.html`) - Simple single-page app with time-series visualization

## 📋 Features

- **Real-time Data Simulation**: Simulates 3 fermenter sensors with realistic patterns
  - `fermenter_temp`: 35-40°C with occasional noise
  - `fermenter_ph`: 6.5-7.5 pH
  - `agitator_rpm`: 300-600 RPM
- **Data Validation**: Validates values within reasonable bounds, non-empty timestamps
- **Anomaly Detection**: 
  - Rolling mean ± 3 standard deviations per tag
  - Simple threshold rules (e.g., fermenter_temp > 45°C)
  - Clearly separated in dedicated module
- **Reliability & Fault Tolerance**: 
  - **Retry Queue**: Failed database operations are automatically retried
  - **Dead Letter Queue**: Persistent backup ensures no data loss during outages
  - **Startup Recovery**: Failed measurements recovered on restart
  - See [RELIABILITY.md](RELIABILITY.md) for detailed architecture
- **REST API**: 
  - `GET /tags` - Returns list of available tags
  - `GET /data?tag=<name>&from=<time>&to=<time>` - Query time-series data
  - `GET /anomalies?tag=<name>&from=<time>&to=<time>` - Query anomalies only
  - `GET /health` - System health check with retry queue status
- **Interactive Dashboard**: 
  - Tag selection via dropdown
  - Time-series chart with Chart.js
  - Anomalies highlighted as red triangles
  - Auto-refresh every 5 seconds

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Navigate to the project directory**:
   ```powershell
   cd C:\industrial-sensor-monitor
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

### Running the System

You need to run two services in separate terminal windows:

#### Terminal 1: Start the API Server

```powershell
cd C:\industrial-sensor-monitor\backend
python api.py
```

The API will start on `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/dashboard`

#### Terminal 2: Start the Data Ingestion Service

```powershell
cd C:\industrial-sensor-monitor\backend
python ingestion_service.py
```

This will:
1. Start generating simulated sensor readings once per second
2. Push data to the ingestion API
3. Automatically detect and flag anomalies

### Accessing the Dashboard

Open your browser and navigate to:
```
http://localhost:8000/dashboard
```

The dashboard shows:
- System statistics (total tags, measurements, anomalies)
- Time-series chart of sensor readings
- Anomaly highlights on the chart (red triangles)
- List of recent anomalies with details

## 📊 Simulated Sensors

The system simulates 3 fermenter process tags:

1. **fermenter_temp**: Temperature around 35-40°C with occasional noise
2. **fermenter_ph**: pH level around 6.5-7.5
3. **agitator_rpm**: Rotation speed around 300-600 RPM

Each sensor generates realistic data with:
- Sinusoidal patterns
- Random noise
- Occasional anomalies (5% probability per reading)

## 🔍 API Endpoints

### GET /tags
Returns a list of available tags.

**Response:**
```json
{
  "tags": ["fermenter_temp", "fermenter_ph", "agitator_rpm"]
}
```

### GET /data
Query time-series data points for a given tag and optional time range.

**Parameters:**
- `tag` (required): Tag name
- `from` (optional): Start timestamp (ISO format)
- `to` (optional): End timestamp (ISO format)

**Example:**
```
GET /data?tag=fermenter_temp&from=2025-11-22T10:00:00
```

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-11-22T10:05:30",
    "tag": "fermenter_temp",
    "value": 37.5,
    "is_anomaly": false
  }
]
```

### GET /anomalies
Returns only records flagged as anomalies for the given tag and time range.

**Parameters:**
- `tag` (required): Tag name
- `from` (optional): Start timestamp (ISO format)
- `to` (optional): End timestamp (ISO format)

**Example:**
```
GET /anomalies?tag=fermenter_temp
```

### POST /ingest
Accept incoming readings from the simulator.

**Request Body:**
```json
{
  "timestamp": "2025-11-22T10:05:30",
  "tag": "fermenter_temp",
  "value": 37.5
}
```

### POST /ingest/batch
Ingest multiple readings at once.

**Request Body:**
```json
[
  {
    "timestamp": "2025-11-22T10:05:30",
    "tag": "fermenter_temp",
    "value": 37.5
  }
]
```

Full API documentation available at: `http://localhost:8000/docs`

## 🧪 Testing Components Individually

### Test the Simulator
```powershell
cd C:\industrial-sensor-monitor\backend
python simulator.py
```

### Test the Anomaly Detector
```powershell
cd C:\industrial-sensor-monitor\backend
python anomaly_detector.py
```

## 📁 Project Structure

```
industrial-sensor-monitor/
├── backend/
│   ├── api.py                    # FastAPI application
│   ├── models.py                 # Database models (measurements table)
│   ├── simulator.py              # Data simulator
│   ├── anomaly_detector.py       # Anomaly detection logic (separate module)
│   ├── ingestion_service.py      # Data ingestion service
│   ├── retry_handler.py          # Failure recovery and retry logic
│   ├── sensor_data.db            # SQLite database (created on first run)
│   └── failed_measurements.jsonl # Dead letter queue (created if DB fails)
├── frontend/
│   └── dashboard.html            # Single-page dashboard
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── RELIABILITY.md                # Detailed reliability architecture
├── start.bat                     # Windows quick start script
└── start.sh                      # Linux/Mac quick start script
```

## 🗄️ Database Schema

### measurements table
```sql
CREATE TABLE measurements (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    tag VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_tag ON measurements(tag);
CREATE INDEX idx_timestamp ON measurements(timestamp);
```

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, FastAPI, SQLAlchemy
- **Database**: SQLite (simple, embedded, easy to run)
- **Analytics**: NumPy for statistical calculations
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **API**: RESTful with automatic OpenAPI documentation

## 🎯 Design Decisions

1. **Simple Schema**: Single `measurements` table with `is_anomaly` boolean field
2. **FastAPI**: Chosen for automatic API documentation and type validation
3. **SQLite**: Simple, embedded database - no setup required
4. **Anomaly Detection**: 
   - Rolling mean ± 3σ (statistical approach)
   - Simple threshold rules (e.g., temp > 45°C)
   - Separated into dedicated `anomaly_detector.py` module
5. **Push-based Ingestion**: Simulator pushes data to API endpoint
6. **Single-page Dashboard**: Simple HTML/JS with Chart.js for visualization
7. **Clear Separation**: Simulator, ingestion, storage, analytics, and presentation are separate modules

## 🔄 Stopping the System

Press `Ctrl+C` in each terminal window to stop the services.

## 📝 Notes

- The database file `sensor_data.db` is created automatically in the backend directory
- Anomaly detection becomes more accurate as more data is collected (needs ~10 readings minimum)
- The system is designed for clarity and ease of understanding, not production-scale performance
- All timestamps are in UTC
- Data is generated once per second as specified in requirements

## 🚀 Future Enhancements

Possible improvements for a production system:
- Switch to PostgreSQL for better concurrency
- Add authentication and authorization
- Implement more sophisticated ML-based anomaly detection
- Add alert notifications (email/SMS)
- Containerization with Docker
- Horizontal scaling with load balancer
- Time-series optimized database (InfluxDB/TimescaleDB)

## 📄 License

This is a demonstration project for educational purposes.

