from django.db import models

# SystemMetric model stores simulated system monitoring data
# This is academic/simulated data (not real system metrics)
class SystemMetric(models.Model):
	# Simulated CPU usage percentage
	cpu_usage = models.FloatField()

	# Simulated memory usage percentage
	memory_usage = models.FloatField()

	# Simulated network usage percentage
	network_usage = models.FloatField()

	# Flag for ML-detected anomaly (unsupervised demo)
	is_anomaly = models.BooleanField(default=False)

	# Timestamp when the metric was generated
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"CPU {self.cpu_usage}% | Memory {self.memory_usage}% | Network {self.network_usage}%"

	class Meta:
		ordering = ['-created_at']
