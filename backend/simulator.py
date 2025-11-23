"""
Fermenter data simulator.
Generates realistic time-series data for fermenter process tags.
"""
import random
import time
import math
from datetime import datetime
from typing import Dict, List


class SensorSimulator:
    """Simulates fermenter sensor data with various patterns."""
    
    def __init__(self):
        self.tags_config = {
            'fermenter_temp': {
                'description': 'Fermenter temperature',
                'unit': 'Celsius',
                'base_value': 37.5,
                'variation': 1.5,
                'min_value': 35.0,
                'max_value': 40.0,
                'anomaly_probability': 0.05,
            },
            'fermenter_ph': {
                'description': 'Fermenter pH level',
                'unit': 'pH',
                'base_value': 7.0,
                'variation': 0.3,
                'min_value': 6.5,
                'max_value': 7.5,
                'anomaly_probability': 0.04,
            },
            'agitator_rpm': {
                'description': 'Agitator rotation speed',
                'unit': 'RPM',
                'base_value': 450.0,
                'variation': 50.0,
                'min_value': 300.0,
                'max_value': 600.0,
                'anomaly_probability': 0.03,
            },
        }
        self.time_step = 0
    
    def get_tags_metadata(self) -> List[Dict]:
        """Return metadata for all simulated tags."""
        return [
            {
                'name': name,
                'description': config['description'],
                'unit': config['unit'],
                'min_value': config['min_value'],
                'max_value': config['max_value'],
            }
            for name, config in self.tags_config.items()
        ]
    
    def generate_reading(self, tag_name: str) -> Dict:
        """Generate a single reading for a specific tag."""
        if tag_name not in self.tags_config:
            raise ValueError(f"Unknown tag: {tag_name}")
        
        config = self.tags_config[tag_name]
        
        # Base value with sinusoidal variation over time
        base = config['base_value']
        variation = config['variation']
        
        # Add time-based sine wave for realistic patterns
        sine_component = math.sin(self.time_step * 0.1) * variation * 0.5
        
        # Add random noise
        noise = random.gauss(0, variation * 0.2)
        
        # Calculate value
        value = base + sine_component + noise
        
        # Occasionally inject anomalies
        if random.random() < config['anomaly_probability']:
            # Create an anomaly (spike or drop)
            if random.random() < 0.5:
                value += variation * random.uniform(3, 5)  # Spike
            else:
                value -= variation * random.uniform(2, 4)  # Drop
        
        # Clamp to reasonable bounds (but allow some out-of-range for detection)
        min_bound = config['min_value'] - variation
        max_bound = config['max_value'] + variation
        value = max(min_bound, min(max_bound, value))
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'tag': tag_name,
            'value': round(value, 2),
        }
    
    def generate_batch(self) -> List[Dict]:
        """Generate readings for all tags."""
        self.time_step += 1
        return [self.generate_reading(tag_name) for tag_name in self.tags_config.keys()]
    
    def simulate_continuous(self, callback, interval_seconds=1, max_iterations=None):
        """
        Continuously generate readings and call the callback function.
        
        Args:
            callback: Function to call with each batch of readings
            interval_seconds: Time between readings
            max_iterations: Maximum number of iterations (None for infinite)
        """
        iteration = 0
        try:
            while max_iterations is None or iteration < max_iterations:
                readings = self.generate_batch()
                callback(readings)
                iteration += 1
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nSimulation stopped by user")


if __name__ == '__main__':
    # Test the simulator
    simulator = SensorSimulator()
    
    print("Testing sensor simulator...")
    print("\nTags metadata:")
    for tag in simulator.get_tags_metadata():
        print(f"  - {tag['name']}: {tag['description']} ({tag['unit']})")
    
    print("\nGenerating 5 sample readings:")
    for i in range(5):
        readings = simulator.generate_batch()
        print(f"\nBatch {i+1}:")
        for reading in readings:
            print(f"  {reading['tag']}: {reading['value']}")
        time.sleep(0.5)
