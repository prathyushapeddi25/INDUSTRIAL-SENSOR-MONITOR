"""
Anomaly detection logic for sensor readings.
Uses rolling mean ± 3 standard deviations and threshold rules.
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque


class AnomalyDetector:
    """Detects anomalies using rolling statistics and threshold rules."""
    
    # Threshold rules for each tag
    THRESHOLD_RULES = {
        'fermenter_temp': {'min': 35.0, 'max': 45.0},  # 45°C is anomaly threshold
        'fermenter_ph': {'min': 6.0, 'max': 8.0},
        'agitator_rpm': {'min': 250.0, 'max': 650.0},
    }
    
    def __init__(self, window_size=50, std_threshold=3.0):
        """
        Initialize the anomaly detector.
        
        Args:
            window_size: Number of historical readings to consider for rolling statistics
            std_threshold: Standard deviation threshold (default: 3.0)
        """
        self.window_size = window_size
        self.std_threshold = std_threshold
        self.history = {}  # tag -> deque of values
    
    def add_reading(self, tag: str, value: float):
        """Add a reading to the historical data."""
        if tag not in self.history:
            self.history[tag] = deque(maxlen=self.window_size)
        self.history[tag].append(value)
    
    def detect_anomaly(self, tag: str, value: float) -> bool:
        """
        Detect if a reading is anomalous.
        
        Uses two methods:
        1. Simple threshold rules (e.g., fermenter_temp > 45°C)
        2. Rolling mean ± 3 standard deviations
        
        Args:
            tag: Tag name
            value: Current reading value
        
        Returns:
            True if anomaly detected, False otherwise
        """
        # Method 1: Check threshold rules first
        if tag in self.THRESHOLD_RULES:
            rules = self.THRESHOLD_RULES[tag]
            if value < rules['min'] or value > rules['max']:
                return True
        
        # Need enough history for statistical analysis
        if tag not in self.history or len(self.history[tag]) < 10:
            return False
        
        # Method 2: Rolling mean ± 3 standard deviations
        historical_values = np.array(list(self.history[tag]))
        mean = np.mean(historical_values)
        std = np.std(historical_values)
        
        # Avoid division by zero
        if std < 1e-6:
            return False
        
        # Check if value is outside mean ± (std_threshold * std)
        lower_bound = mean - (self.std_threshold * std)
        upper_bound = mean + (self.std_threshold * std)
        
        if value < lower_bound or value > upper_bound:
            return True
        
        return False
    
    def analyze_reading(self, tag: str, value: float) -> bool:
        """
        Analyze a reading and return whether it's an anomaly.
        This method combines detection and history management.
        
        Args:
            tag: Tag name
            value: Current reading value
        
        Returns:
            True if anomaly detected, False otherwise
        """
        is_anomaly = self.detect_anomaly(tag, value)
        
        # Add to history regardless of anomaly status
        self.add_reading(tag, value)
        
        return is_anomaly

if __name__ == '__main__':
    # Test the anomaly detector
    detector = AnomalyDetector(window_size=20, std_threshold=3.0)
    
    print("Testing anomaly detector...")
    
    # Normal readings for fermenter_temp
    print("\nAdding normal readings for fermenter_temp (35-40°C):")
    for i in range(30):
        value = 37.5 + np.random.normal(0, 1.0)
        is_anomaly = detector.analyze_reading(tag='fermenter_temp', value=value)
        if is_anomaly:
            print(f"  Anomaly detected at value: {value:.2f}")
    
    # Add a spike above threshold
    print("\nAdding spike above 45°C threshold:")
    spike_value = 46.0
    is_anomaly = detector.analyze_reading(tag='fermenter_temp', value=spike_value)
    if is_anomaly:
        print(f"  ✓ Threshold anomaly detected: {spike_value:.2f}°C")
    
    # Add statistical outlier
    print("\nAdding statistical outlier:")
    outlier_value = 44.0
    is_anomaly = detector.analyze_reading(tag='fermenter_temp', value=outlier_value)
    if is_anomaly:
        print(f"  ✓ Statistical anomaly detected: {outlier_value:.2f}°C")

