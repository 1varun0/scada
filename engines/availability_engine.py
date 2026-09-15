class AvailabilityEngine:
    """
    Engine 4: Communication Integrity (Target: A2 Replay, A3 DoS)
    Monitors data freshness and packet arrival.
    """
    def __init__(self, tau_a_ms: float = 1500.0, tau_a_max_ms: float = 5000.0):
        """
        Args:
            tau_a_ms: Threshold for acceptable data age in ms (e.g., 1.5 seconds)
            tau_a_max_ms: Age at which anomaly score hits 1.0 (e.g., 5.0 seconds)
        """
        self.tau_a = tau_a_ms
        self.tau_a_max = tau_a_max_ms
        
    def evaluate(self, simulation_time_s: float, source_time_s: float, packet_received: bool) -> tuple[float, float]:
        """
        Evaluate availability rules.
        
        Args:
            simulation_time_s: Current simulation clock in seconds.
            source_time_s: Timestamp from the sensor in seconds.
            packet_received: True if the packet successfully arrived.
            
        Returns:
            Tuple of (data_age_ms, S_a)
            S_a is the normalized anomaly score in [0, 1].
        """
        # A3 DoS target
        if not packet_received:
            return 0.0, 1.0
            
        # A2 Replay target
        data_age_ms = (simulation_time_s - source_time_s) * 1000.0
        
        if data_age_ms > self.tau_a:
            # Linear ramp from 0.0 at tau_a to 1.0 at tau_a_max (continuous)
            s_a = min((data_age_ms - self.tau_a) / (self.tau_a_max - self.tau_a), 1.0)
            return data_age_ms, s_a
            
        return data_age_ms, 0.0
