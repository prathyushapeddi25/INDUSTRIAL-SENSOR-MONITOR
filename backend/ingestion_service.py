"""
Service to continuously run the simulator and ingest data into the API.
"""
import requests
import time
from simulator import SensorSimulator


class IngestionService:
    """Service that runs the simulator and ingests data to the backend API."""
    
    def __init__(self, api_base_url='http://localhost:8000'):
        self.api_base_url = api_base_url
        self.simulator = SensorSimulator()
    
    def ingest_readings(self, readings):
        """Send a batch of readings to the API."""
        try:
            response = requests.post(
                f'{self.api_base_url}/ingest/batch',
                json=readings,
                timeout=5
            )
            
            if response.status_code == 201:
                result = response.json()
                anomaly_count = sum(1 for r in result.get('results', []) if r.get('is_anomaly'))
                print(f"✓ Ingested {result.get('processed', 0)} measurements ({anomaly_count} anomalies detected)")
            else:
                print(f"✗ Failed to ingest readings: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"✗ Error ingesting readings: {e}")
    
    def run(self, interval_seconds=1):
        """Run the ingestion service continuously."""
        print(f"Starting ingestion service (interval: {interval_seconds}s)...")
        print(f"API endpoint: {self.api_base_url}")
        
        # Wait for API to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f'{self.api_base_url}/')
                if response.status_code == 200:
                    print("✓ API is ready")
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    print("✗ Could not connect to API. Make sure it's running on port 8000.")
                    return
                print(f"Waiting for API... ({i+1}/{max_retries})")
                time.sleep(2)
        
        print("\nStarting continuous data ingestion (Ctrl+C to stop)...")
        print("Generating readings once per second for:")
        print("  - fermenter_temp (35-40°C)")
        print("  - fermenter_ph (6.5-7.5)")
        print("  - agitator_rpm (300-600 RPM)")
        print("-" * 60)
        
        # Run simulator with ingestion callback
        self.simulator.simulate_continuous(
            callback=self.ingest_readings,
            interval_seconds=interval_seconds
        )


if __name__ == '__main__':
    service = IngestionService()
    service.run(interval_seconds=1)
