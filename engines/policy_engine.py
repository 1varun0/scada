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
        Evaluate safety rules based on Controller valve logic and critical boundaries.
        
        Note on Hysteresis Rules:
        h_off (1.2m) and h_on (0.8m) are defined for reference, but static pump-vs-level
        hysteresis rules are omitted here because PolicyEngine is not setpoint-aware
        and hardcoding [0.8, 1.2m] causes false alarms during dynamic setpoint transitions
        (e.g., setpoint profile steps). Setpoint-aware pump filtering is handled by the
        gateway command filter with live controller state.
        
        Active Rules in v2:
        1. Valve must be default (50%) or legitimate fail-safe (0% with pump OFF) => 1.0 if violated
        2. Fall back to v1 critical boundary checks (overflow near h_max, drain near h_crit_low)
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

