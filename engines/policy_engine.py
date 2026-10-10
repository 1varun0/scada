from config.parameters import PARAMS

class PolicyEngine:
    """
    Engine 3: Command/Policy Safety (Target: A4 Auth Misuse)
    Evaluates commands against the current physical state using deterministic safety rules.
    
    Rules target authenticated misuse scenarios where valid operators issue
    commands that violate process safety constraints.
    """
    def __init__(self, epsilon_m: float = 0.05):
        self.h_crit_low = PARAMS.tank.critical_low_m
        self.h_crit_high = PARAMS.tank.critical_high_m
        self.h_max = PARAMS.tank.max_height_m
        self.epsilon = epsilon_m
        self.default_valve_pct = PARAMS.controller.default_valve_pct

    def evaluate(self, h_observed: float, pump_command: int, valve_command: float) -> float:
        """
        Evaluate safety rules. Returns 1.0 if a violation occurs, else 0.0.
        
        Rules:
        1. Pump ON when H > H_crit_high (near overflow) => 1.0
        2. Valve opened ABOVE the controller default when H < H_crit_low => 1.0
        """
        # Rule 1: Tank nearly overflowing, but pump is commanded ON
        if h_observed > (self.h_max - self.epsilon) and pump_command == 1:
            return 1.0
            
        # Rule 2: Tank critically low and valve opened beyond normal operating point
        # This correctly targets misuse (e.g., VALVE_SET_80 when H is dangerously low)
        # without flagging the controller's normal default valve position
        if h_observed < self.h_crit_low and valve_command > self.default_valve_pct:
            return 1.0
            
        return 0.0

    def evaluate_v2(self, h_observed: float, pump_command: int, valve_command: float) -> float:
        """
        Evaluate stricter safety rules based on Controller hysteresis band and valve logic.
        
        Rules:
        1. Pump ON when H > H_off (1.2m) + epsilon => 1.0
        2. Pump OFF when H < H_on (0.8m) - epsilon => 1.0
        3. Valve is not a legitimate value (default or safe_position) => 1.0
        """
        h_off = PARAMS.controller.pump_off_threshold_m
        h_on = PARAMS.controller.pump_on_threshold_m
        safe_valve_pct = getattr(PARAMS.valve, "safe_position_pct", 0.0)
        
        # The controller only enters fail-safe (valve=0.0) when dos is active, and forces pump=0.
        # Allow safe_position only if the pump is also OFF.
        if valve_command != self.default_valve_pct:
            if valve_command != safe_valve_pct or pump_command != 0:
                return 1.0
            
        # Fall back to v1 rules for critical bounds
        return self.evaluate(h_observed, pump_command, valve_command)

