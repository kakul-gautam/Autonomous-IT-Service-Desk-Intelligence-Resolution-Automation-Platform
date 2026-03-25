import random
from .models import SystemMetric

# Simulated monitoring generator
# This produces random values for academic/demo purposes only
# No real system metrics are collected

def generate_metrics():
    """
    Generates a single set of simulated system metrics and saves to database.
    CPU: 10-100
    Memory: 20-100
    Network: 5-100
    """
    cpu_usage = random.uniform(10, 100)
    memory_usage = random.uniform(20, 100)
    network_usage = random.uniform(5, 100)

    # Save simulated metrics to database
    metric = SystemMetric.objects.create(
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        network_usage=network_usage,
        is_anomaly=False  # Simplified: no anomaly detection for core functionality
    )

    return metric
