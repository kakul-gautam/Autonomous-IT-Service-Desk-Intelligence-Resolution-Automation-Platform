"""
Real anomaly detection module using statistical methods.

Detects actual anomalies based on:
- Mean + standard deviation for threshold detection
- Multi-variable approach (CPU, Memory, Network)
- Contextual patterns (unusual combinations)
"""

import statistics
from django.db.models import Avg, StdDev, Max, Min, Q


def calculate_statistics(metrics, field_name):
    """
    Calculate mean and standard deviation for a metric.
    
    Args:
        metrics: QuerySet of SystemMetric objects
        field_name: Name of the field to analyze (cpu_usage, memory_usage, etc)
    
    Returns:
        tuple: (mean, std_dev) or (None, None) if insufficient data
    """
    values = [getattr(m, field_name) for m in metrics]
    
    if len(values) < 3:
        return None, None
    
    try:
        mean = statistics.mean(values)
        if len(values) > 1:
            std_dev = statistics.stdev(values)
        else:
            std_dev = 0
        return mean, std_dev
    except Exception:
        return None, None


def is_anomaly_zscore(value, mean, std_dev, threshold=2.5):
    """
    Detect anomaly using Z-score method.
    
    Z-score tells us how many standard deviations away from mean.
    threshold=2.5 means approximately 98% of normal data
    
    Args:
        value: Current metric value
        mean: Mean of historical data
        std_dev: Standard deviation
        threshold: Z-score threshold (default 2.5)
    
    Returns:
        bool: True if anomaly detected
    """
    if mean is None or std_dev is None:
        return False
    
    if std_dev == 0:
        # If no variation, use absolute threshold fallback
        # Default threshold: 50% of mean, but if mean is near-zero use absolute 5%
        if abs(mean) < 0.5:  # mean is near-zero (< 0.5%)
            abs_threshold = 5  # absolute 5% deviation
            return abs(value - mean) > abs_threshold
        else:
            # Use relative threshold for normal cases
            return abs(value - mean) > mean * 0.5
    
    z_score = abs((value - mean) / std_dev)
    return z_score > threshold


def detect_anomalies_multivariate(metric):
    """
    Detect anomalies considering multiple variables together.
    
    Some combinations are unusual even if individual values are normal:
    - High CPU + Low Memory (unusual - usually both high together)
    - High Network + Low CPU (data not being processed)
    - All three very high (system stress)
    
    Args:
        metric: SystemMetric object to analyze
    
    Returns:
        tuple: (is_anomaly, reason)
    """
    from monitoring.models import SystemMetric
    
    # Get recent metrics for context (last 20), excluding current metric
    recent = SystemMetric.objects.exclude(pk=metric.pk).order_by('-created_at')[:20]
    
    if len(recent) < 5:
        return False, "Insufficient data"
    
    # Calculate statistics for each metric
    cpu_mean, cpu_std = calculate_statistics(recent, 'cpu_usage')
    mem_mean, mem_std = calculate_statistics(recent, 'memory_usage')
    net_mean, net_std = calculate_statistics(recent, 'network_usage')
    
    anomaly_reasons = []
    
    # Check individual metric anomalies
    if is_anomaly_zscore(metric.cpu_usage, cpu_mean, cpu_std, threshold=2.0):
        anomaly_reasons.append(f"CPU spike ({metric.cpu_usage:.1f}%)")
    
    if is_anomaly_zscore(metric.memory_usage, mem_mean, mem_std, threshold=2.0):
        anomaly_reasons.append(f"Memory spike ({metric.memory_usage:.1f}%)")
    
    if is_anomaly_zscore(metric.network_usage, net_mean, net_std, threshold=2.5):
        anomaly_reasons.append(f"Network spike ({metric.network_usage:.1f}%)")
    
    # Check for unusual combinations (multivariate anomalies)
    # High CPU + Low Memory is unusual
    high_cpu = metric.cpu_usage > (cpu_mean + cpu_std) if cpu_std else False
    low_mem = metric.memory_usage < (mem_mean - mem_std) if mem_std else False
    
    if high_cpu and low_mem:
        anomaly_reasons.append("High CPU with low memory (unusual pattern)")
    
    # All metrics high together (system stress)
    is_all_high = (
        (metric.cpu_usage > (cpu_mean + cpu_std * 1.5) if cpu_std else False) and
        (metric.memory_usage > (mem_mean + mem_std * 1.5) if mem_std else False) and
        (metric.network_usage > (net_mean + net_std * 1.5) if net_std else False)
    )
    
    if is_all_high:
        anomaly_reasons.append("System stress (all metrics elevated)")
    
    is_anomaly = len(anomaly_reasons) > 0
    reason = "; ".join(anomaly_reasons) if anomaly_reasons else "Normal"
    
    return is_anomaly, reason


def get_anomaly_score(metric):
    """
    Get a score 0-100 indicating how anomalous this metric is.
    
    Used for severity ranking.
    
    Args:
        metric: SystemMetric object
    
    Returns:
        int: Anomaly score 0-100
    """
    from monitoring.models import SystemMetric
    
    recent = SystemMetric.objects.exclude(pk=metric.pk).order_by('-created_at')[:20]
    
    if len(recent) < 5:
        return 0
    
    cpu_mean, cpu_std = calculate_statistics(recent, 'cpu_usage')
    mem_mean, mem_std = calculate_statistics(recent, 'memory_usage')
    net_mean, net_std = calculate_statistics(recent, 'network_usage')
    
    score = 0
    
    # CPU contribution (0-35)
    if cpu_std and cpu_std > 0:
        cpu_z = abs((metric.cpu_usage - cpu_mean) / cpu_std)
        score += min(cpu_z * 10, 35)
    
    # Memory contribution (0-35)
    if mem_std and mem_std > 0:
        mem_z = abs((metric.memory_usage - mem_mean) / mem_std)
        score += min(mem_z * 10, 35)
    
    # Network contribution (0-30)
    if net_std and net_std > 0:
        net_z = abs((metric.network_usage - net_mean) / net_std)
        score += min(net_z * 10, 30)
    
    return min(int(score), 100)
