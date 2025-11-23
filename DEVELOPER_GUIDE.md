# Industrial Sensor Monitor - Developer Guide

## 🎯 What is this Application?

This is a **real-time industrial sensor monitoring system** that simulates, collects, and visualizes data from industrial fermentation equipment. It demonstrates a production-grade data pipeline with anomaly detection, retry mechanisms, and a live dashboard.

---

## 🏗️ System Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌──────────┐
│  Simulator  │ ──────> │  Ingestion   │ ──────> │   API    │
│             │  HTTP   │   Service    │  HTTP   │  Server  │
│ (generates  │         │ (orchestrates│         │ (FastAPI)│
│   sensor    │         │  data flow)  │         │          │
│   readings) │         └──────────────┘         └─────┬────┘
└─────────────┘                                         │
                                                        │
                                                        ▼
                                            ┌───────────────────┐
                                            │    Database       │
                                            │   (SQLite)        │
                                            │                   │
                                            │ + Anomaly Detect  │
                                            │ + Retry Handler   │
                                            └───────────────────┘
                                                        │
                                                        │
                                                        ▼
                                            ┌───────────────────┐
                                            │   Dashboard       │
                                            │  (HTML + Chart.js)│
                                            │                   │
                                            │  Real-time Graphs │
                                            └───────────────────┘
```

---

## 📂 Project Structure

```
industrial-sensor-monitor/
│
├── backend/                      # Core application logic
│   ├── simulator.py              # 🎲 Generates fake sensor data
│   ├── ingestion_service.py      # 🔄 Orchestrates data flow
│   ├── api.py                    # 🌐 REST API (FastAPI)
│   ├── models.py                 # 💾 Database models (SQLAlchemy)
│   ├── anomaly_detector.py       # 🚨 Statistical anomaly detection
│   └── retry_handler.py          # 🔁 Handles failed operations
│
├── frontend/
│   └── dashboard.html            # 📊 Real-time visualization
│
├── requirements.txt              # Python dependencies
├── start.bat                     # Windows startup script
├── start.sh                      # Linux/Mac startup script
└── README.md                     # Project overview
```

---

## 🔄 Application Flow (Step by Step)

### **Entry Point: Where Everything Starts**

You start **TWO** separate Python processes:

1. **API Server** (`backend/api.py`) - Port 8000
2. **Ingestion Service** (`backend/ingestion_service.py`)

### **Detailed Flow:**

```
1. API SERVER STARTS (api.py)
   ├─> Initializes FastAPI application
   ├─> Creates SQLite database (sensor_data.db)
   ├─> Initializes AnomalyDetector (statistical analysis)
   ├─> Initializes RetryHandler (for reliability)
   ├─> Starts listening on http://localhost:8000
   └─> Serves dashboard.html at /dashboard endpoint

2. INGESTION SERVICE STARTS (ingestion_service.py)
   ├─> Waits for API to be ready (health check)
   ├─> Initializes SensorSimulator
   └─> Enters infinite loop (once per second):
       │
       ├─> simulator.py generates 3 readings:
       │   ├─> fermenter_temp (35-40°C + noise)
       │   ├─> fermenter_ph (6.5-7.5 + noise)
       │   └─> agitator_rpm (300-600 + noise)
       │
       ├─> Sends batch HTTP POST to /ingest/batch
       │
       └─> Repeats every 1 second

3. API RECEIVES DATA (/ingest/batch endpoint)
   ├─> Validates each measurement:
   │   ├─> Check tag is valid
   │   ├─> Check value is in range
   │   └─> Parse timestamp
   │
   ├─> Anomaly Detection:
   │   ├─> Feeds value to AnomalyDetector
   │   ├─> Uses rolling window statistics (50 points)
   │   ├─> Calculates Z-score (3 std deviations)
   │   └─> Flags if anomalous
   │
   ├─> Database Write:
   │   ├─> Try to save to SQLite
   │   ├─> If fails → add to retry queue
   │   └─> RetryHandler retries in background
   │
   └─> Returns success/queued response

4. DASHBOARD DISPLAYS DATA (dashboard.html)
   ├─> Loads at http://localhost:8000/dashboard
   ├─> Every 2 seconds:
   │   ├─> Fetches latest data via GET /data?tag=X
   │   ├─> Updates Chart.js graphs
   │   └─> Highlights anomalies in red
   │
   └─> Shows 3 real-time line charts

5. RETRY MECHANISM (retry_handler.py)
   ├─> Runs background worker thread
   ├─> Periodically checks retry queue
   ├─> Attempts to save failed measurements
   ├─> If still fails → writes to dead letter queue
   │   (failed_measurements.jsonl)
   └─> On startup, recovers from dead letter queue
```

---

## 🚀 How to Start the Application

### **Prerequisites:**
```bash
# You need Python 3.8+ installed
python --version
```

### **Option 1: Use Startup Scripts (Recommended)**

#### **Windows:**
```bash
# Double-click or run:
start.bat
```

This will:
- Install dependencies
- Start API server in new window
- Start ingestion service in new window
- Open dashboard in browser

#### **Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### **Option 2: Manual Start (for Development)**

#### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

#### **Step 2: Start API Server**
```bash
cd backend
python api.py
```

You should see:
```
Starting Fermenter Monitoring API...
API documentation available at: http://localhost:8000/docs
Dashboard available at: http://localhost:8000/dashboard
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### **Step 3: Start Ingestion Service (in another terminal)**
```bash
cd backend
python ingestion_service.py
```

You should see:
```
Starting ingestion service (interval: 1s)...
✓ API is ready
Starting continuous data ingestion (Ctrl+C to stop)...
✓ Ingested 3 measurements (0 anomalies detected)
✓ Ingested 3 measurements (1 anomalies detected)
...
```

#### **Step 4: Open Dashboard**
Navigate to: **http://localhost:8000/dashboard**

---

## 📊 What to Expect

### **Normal Operation:**

1. **Two console windows running** (API + Ingestion)
2. **Dashboard updates every 2 seconds** with new data points
3. **Three graphs showing:**
   - Fermenter Temperature (35-40°C)
   - Fermenter pH (6.5-7.5)
   - Agitator RPM (300-600)
4. **Anomalies appear as RED dots** on graphs
5. **Console shows ingestion logs** like:
   ```
   ✓ Ingested 3 measurements (0 anomalies detected)
   ✓ Ingested 3 measurements (1 anomalies detected)
   ```

### **Database File:**
- A file `sensor_data.db` will be created in the root directory
- Contains all measurements with timestamps and anomaly flags

### **API Documentation:**
- Visit **http://localhost:8000/docs** for interactive API docs
- Try endpoints like:
  - `GET /data?tag=fermenter_temp` - Get temperature data
  - `GET /anomalies?tag=fermenter_ph` - Get pH anomalies
  - `GET /stats` - Get system statistics

---

## 🔍 Key Components Explained

### **1. simulator.py - Data Generation**
```python
# Generates realistic sensor readings with Gaussian noise
# Also randomly injects anomalies (5% chance)
def generate_reading(self, tag_config):
    value = random.uniform(min_val, max_val)
    noise = random.gauss(0, noise_sigma)
    
    # 5% chance of anomaly
    if random.random() < 0.05:
        value += spike_magnitude
    
    return value
```

**Why it exists:** Simulates real industrial sensors without needing actual hardware.

### **2. ingestion_service.py - Orchestrator**
```python
# Runs simulator and sends data to API
def run(self, interval_seconds=1):
    while True:
        readings = self.simulator.generate_batch()
        self.ingest_readings(readings)  # HTTP POST
        time.sleep(interval_seconds)
```

**Why it exists:** Separates data generation from data storage/processing.

### **3. api.py - REST API**
- **FastAPI framework** for modern, async Python web API
- **Endpoints:**
  - `POST /ingest/batch` - Accept sensor data
  - `GET /data` - Query time-series data
  - `GET /anomalies` - Get flagged anomalies
  - `GET /stats` - System metrics
  - `GET /dashboard` - Serve HTML dashboard

**Why it exists:** Provides a standard interface for data ingestion and retrieval.

### **4. anomaly_detector.py - Statistical Analysis**
```python
# Uses Z-score method (standard deviations from mean)
def analyze_reading(self, tag, value):
    mean = np.mean(window)
    std = np.std(window)
    z_score = abs((value - mean) / std)
    
    return z_score > self.std_threshold  # Default: 3σ
```

**Why it exists:** Automatically detects unusual sensor readings that might indicate equipment problems.

### **5. retry_handler.py - Reliability**
```python
# Handles transient failures (network, disk, etc.)
# - Queues failed operations
# - Retries with exponential backoff
# - Persists to dead letter queue if all retries fail
```

**Why it exists:** Ensures no data loss even during temporary system issues.

### **6. models.py - Database Schema**
```python
class Measurement(Base):
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    tag = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, default=False)
```

**Why it exists:** Defines how data is stored in the database.

### **7. dashboard.html - Visualization**
- Uses **Chart.js** for real-time graphs
- Polls API every 2 seconds
- Color-codes anomalies
- Shows last 100 data points per tag

**Why it exists:** Provides human-readable, real-time monitoring interface.

---

## 🎓 Learning Path for New Developers

### **Day 1: Understand the Flow**
1. Start the application
2. Watch the console logs
3. Open the dashboard and observe data
4. Look at the database file (use SQLite browser)

### **Day 2: Explore the Code**
1. Read `simulator.py` - simplest component
2. Read `ingestion_service.py` - orchestration
3. Read `api.py` - REST endpoints
4. Open `http://localhost:8000/docs` - interactive API

### **Day 3: Make Changes**
1. Change sensor ranges in `simulator.py`
2. Adjust anomaly threshold in `anomaly_detector.py`
3. Add a new sensor tag
4. Modify dashboard colors

### **Day 4: Understand Reliability**
1. Read `retry_handler.py`
2. Simulate a failure (delete database while running)
3. Watch retry mechanism kick in
4. Inspect `failed_measurements.jsonl`

---

## 🐛 Troubleshooting

### **Problem: Port 8000 already in use**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### **Problem: Dashboard not loading**
- Check API server is running
- Visit http://localhost:8000/health
- Check browser console for errors

### **Problem: No data appearing**
- Check ingestion service is running
- Check for errors in ingestion service console
- Verify API health: `curl http://localhost:8000/health`

---

## 📚 Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python 3.11** | Programming language |
| **FastAPI** | Modern web framework |
| **SQLAlchemy** | ORM for database |
| **SQLite** | Lightweight database |
| **NumPy** | Statistical calculations |
| **Chart.js** | Frontend graphing |
| **Uvicorn** | ASGI server |

---

## 🎯 Next Steps

After understanding the flow, you can:

1. **Add new sensor types** (e.g., pressure, flow rate)
2. **Implement alerts** (email/SMS when anomalies detected)
3. **Add authentication** to API endpoints
4. **Export data** to CSV or cloud storage
5. **Improve anomaly detection** with ML models
6. **Add unit tests** for components
7. **Containerize** with Docker
8. **Deploy** to cloud (AWS, Azure, GCP)

---

## 💡 Key Concepts Demonstrated

✅ **Microservices pattern** (separate services)  
✅ **REST API design** (standard HTTP endpoints)  
✅ **Real-time data streaming** (continuous ingestion)  
✅ **Anomaly detection** (statistical methods)  
✅ **Retry/resilience patterns** (handling failures)  
✅ **Time-series data** (timestamp-based storage)  
✅ **Separation of concerns** (modular architecture)  

---

## ❓ Common Questions

**Q: Why two separate processes?**  
A: Simulates real-world where data sources (sensors) are separate from the backend system.

**Q: Can I use a different database?**  
A: Yes! Change the connection string in `api.py` to PostgreSQL, MySQL, etc.

**Q: Is this production-ready?**  
A: It's a learning project. For production, add: authentication, monitoring, load balancing, proper logging, and tests.

**Q: How do I stop the application?**  
A: Press `Ctrl+C` in both terminal windows or close them.

---

## 🤝 Need Help?

1. Check the logs in console windows
2. Visit API docs: http://localhost:8000/docs
3. Inspect database: Use DB Browser for SQLite
4. Read the code comments - they explain each function

Happy coding! 🚀
