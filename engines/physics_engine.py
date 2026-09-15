from digital_twin.physics_twin import PhysicsTwin

class PhysicsEngine:
    """
    Engine 1: Physics Consistency (Target: A1 FDI)
    Wraps the independent Digital Twin to compute the residual and normalize it.
    """
    def __init__(self, tau_p: float):
        """
        Args:
            tau_p: Physics threshold (e.g., from E0 validation 99th percentile).
        """
        self.tau_p = tau_p
        self.twin = None
    
    def reset(self, initial_level_m: float, area_m2: float = None, max_height_m: float = None):
        """Reinitialize the twin for a new scenario."""
        if self.twin is None:
            self.twin = PhysicsTwin(initial_level_m, area_m2, max_height_m)
        else:
            self.twin.reset(initial_level_m)
            
    def step(self, q_in: float, q_out: float, h_observed: float, dt: float) -> tuple[float, float, float]:
        """
        Advance the twin, compute residual, and return normalized anomaly score.
        
        Args:
            q_in: Reported volumetric inflow.
            q_out: Reported volumetric outflow.
            h_observed: Reported tank level.
            dt: Time step.
            
        Returns:
            Tuple of (h_twin, physics_residual, S_p)
            S_p is the normalized anomaly score in [0, 1].
        """
        if self.twin is None:
            raise RuntimeError("PhysicsEngine must be reset() with initial level before stepping.")
            
        # 1. Twin advances state using ONLY flow measurements
        h_twin = self.twin.step(q_in, q_out, dt)
        
        # 2. Compute residual between observed and twin level
        residual = self.twin.compute_residual(h_observed)
        
        # 3. Normalize to [0, 1] using the threshold tau_p
        s_p = min(abs(residual) / self.tau_p, 1.0) if self.tau_p > 0 else 0.0
        
        return h_twin, residual, s_p
