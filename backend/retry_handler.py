"""
Retry handler for failed database operations.
Implements retry logic with exponential backoff and dead letter queue.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import threading
import queue


class FailedOperationHandler:
    """
    Handles failed database operations with retry logic.
    Stores failed operations to disk as a backup (dead letter queue).
    """
    
    def __init__(self, db_session_factory, max_retries=3, dead_letter_path='failed_measurements.jsonl'):
        self.db_session_factory = db_session_factory
        self.max_retries = max_retries
        self.dead_letter_path = Path(dead_letter_path)
        self.retry_queue = queue.Queue()
        self.running = False
        self.retry_thread = None
        
    def start_retry_worker(self):
        """Start background worker to retry failed operations."""
        if self.running:
            return
        
        self.running = True
        self.retry_thread = threading.Thread(target=self._retry_worker, daemon=True)
        self.retry_thread.start()
        print("✓ Retry worker started")
    
    def stop_retry_worker(self):
        """Stop the retry worker."""
        self.running = False
        if self.retry_thread:
            self.retry_thread.join(timeout=5)
    
    def add_failed_measurement(self, measurement_data: Dict):
        """
        Add a failed measurement to the retry queue.
        
        Args:
            measurement_data: Dict with 'timestamp', 'tag', 'value', 'is_anomaly'
        """
        measurement_data['retry_count'] = 0
        measurement_data['first_failed_at'] = datetime.utcnow().isoformat()
        self.retry_queue.put(measurement_data)
        print(f"⚠ Measurement queued for retry: {measurement_data['tag']} = {measurement_data['value']}")
    
    def save_to_dead_letter_queue(self, measurement_data: Dict):
        """
        Save failed measurement to disk as a backup.
        This ensures no data is lost even if retries fail.
        """
        try:
            with open(self.dead_letter_path, 'a') as f:
                json.dump(measurement_data, f)
                f.write('\n')
            print(f"✓ Saved to dead letter queue: {self.dead_letter_path}")
        except Exception as e:
            print(f"✗ Failed to write to dead letter queue: {e}")
    
    def _retry_worker(self):
        """Background worker that processes the retry queue."""
        while self.running:
            try:
                # Wait for failed measurements (with timeout to allow shutdown)
                try:
                    measurement_data = self.retry_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Attempt to save to database
                success = self._retry_save(measurement_data)
                
                if success:
                    print(f"✓ Successfully retried: {measurement_data['tag']} = {measurement_data['value']}")
                else:
                    # Increment retry count
                    measurement_data['retry_count'] += 1
                    
                    if measurement_data['retry_count'] < self.max_retries:
                        # Exponential backoff
                        backoff = 2 ** measurement_data['retry_count']
                        time.sleep(backoff)
                        self.retry_queue.put(measurement_data)
                        print(f"⚠ Retry {measurement_data['retry_count']}/{self.max_retries} for {measurement_data['tag']}")
                    else:
                        # Max retries exceeded - save to dead letter queue
                        print(f"✗ Max retries exceeded for {measurement_data['tag']} - saving to dead letter queue")
                        self.save_to_dead_letter_queue(measurement_data)
                
                self.retry_queue.task_done()
                
            except Exception as e:
                print(f"✗ Error in retry worker: {e}")
    
    def _retry_save(self, measurement_data: Dict) -> bool:
        """
        Attempt to save a measurement to the database.
        
        Returns:
            True if successful, False otherwise
        """
        from models import Measurement
        
        session = None
        try:
            session = self.db_session_factory()
            
            # Create measurement
            measurement = Measurement(
                timestamp=datetime.fromisoformat(measurement_data['timestamp']),
                tag=measurement_data['tag'],
                value=measurement_data['value'],
                is_anomaly=measurement_data['is_anomaly']
            )
            
            session.add(measurement)
            session.commit()
            return True
            
        except Exception as e:
            if session:
                session.rollback()
            print(f"✗ Retry save failed: {e}")
            return False
        finally:
            if session:
                session.close()
    
    def recover_from_dead_letter_queue(self):
        """
        Attempt to recover measurements from the dead letter queue.
        Call this on startup to replay failed measurements.
        """
        if not self.dead_letter_path.exists():
            return
        
        print(f"\n📂 Recovering failed measurements from {self.dead_letter_path}...")
        
        recovered = 0
        failed = 0
        
        # Read all failed measurements
        with open(self.dead_letter_path, 'r') as f:
            for line in f:
                try:
                    measurement_data = json.loads(line.strip())
                    # Reset retry count
                    measurement_data['retry_count'] = 0
                    
                    # Try to save immediately
                    if self._retry_save(measurement_data):
                        recovered += 1
                    else:
                        # Add back to retry queue
                        self.retry_queue.put(measurement_data)
                        failed += 1
                except Exception as e:
                    print(f"✗ Error recovering measurement: {e}")
                    failed += 1
        
        # Clear the dead letter queue if all recovered
        if failed == 0:
            self.dead_letter_path.unlink()
            print(f"✓ Recovered {recovered} measurements and cleared dead letter queue")
        else:
            # Keep file but create backup
            backup_path = self.dead_letter_path.with_suffix('.jsonl.backup')
            self.dead_letter_path.rename(backup_path)
            print(f"✓ Recovered {recovered} measurements, {failed} still pending")
            print(f"  Original file backed up to: {backup_path}")


# Global handler instance (initialized in api.py)
_handler = None


def get_handler():
    """Get the global handler instance."""
    return _handler


def set_handler(handler):
    """Set the global handler instance."""
    global _handler
    _handler = handler
