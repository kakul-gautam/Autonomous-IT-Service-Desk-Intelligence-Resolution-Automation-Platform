import random
from .models import SystemMetric
from .anomaly_detector import detect_anomalies_multivariate


def generate_metrics():
    """
    Generates a single set of simulated system metrics and saves to database.
    
    Uses realistic data patterns:
    - Normal: CPU 20-70%, Memory 30-75%, Network 5-50%
    - Occasionally spikes: burst traffic, high load periods
    - Anomalies detected using statistical methods (Z-score, multivariate analysis)
    """
    # 90% of the time: normal operating conditions
    if random.random() < 0.9:
        cpu_usage = random.uniform(20, 70)
        memory_usage = random.uniform(30, 75)
        network_usage = random.uniform(5, 50)
    else:
        # 10% of the time: unusual patterns (spikes, stress)
        # Could be burst traffic, heavy processing, network saturation
        cpu_usage = random.uniform(70, 100)
        memory_usage = random.uniform(70, 100)
        network_usage = random.uniform(50, 100)

    # Create metric object
    metric = SystemMetric.objects.create(
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        network_usage=network_usage,
        is_anomaly=False  # Will be updated by anomaly detection
    )

    # Apply real anomaly detection based on statistical analysis
    is_anomaly, reason = detect_anomalies_multivariate(metric)
    metric.is_anomaly = is_anomaly
    metric.save()

    return metric

