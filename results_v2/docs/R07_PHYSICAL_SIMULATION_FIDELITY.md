# R07: Physical Simulation Fidelity & Dynamic Equivalence

## 1. Physical Process Equations & Governing Dynamics

The simulated physical plant modeled throughout the repository is an industrial single-tank water buffering system governed by mass conservation:

$$\frac{dh}{dt} = \frac{Q_{\text{in}}(t) - Q_{\text{out}}(t)}{A}$$

Where:
- $h(t)$: Instantaneous water level in the tank ($\text{m}$).
- $A$: Tank cross-sectional area ($A = 1.0\text{ m}^2$).
- $Q_{\text{in}}(t)$: Volumetric inflow delivered by the inlet pump ($\text{m}^3/\text{s}$).
- $Q_{\text{out}}(t)$: Volumetric outflow drained through the throttling control valve ($\text{m}^3/\text{s}$).

### A. Inflow Modeling (Pump Dynamics)
When the pump is commanded ON (`pump_command == 1`), flow rate ramps smoothly to maximum capacity $Q_{\text{max}} = 0.005\text{ m}^3/\text{s}$ ($5.0\text{ L/s}$). Mechanical delay is simulated via a discrete response buffer ($t_{\text{delay}} = 1\text{ s}$).

### B. Outflow Modeling (Torricelli Gravity Drain)
Outflow depends on both control valve opening percentage ($V \in [0, 100\%]$) and hydrostatic pressure head according to Torricelli's Law:

$$Q_{\text{out}}(t) = C_v \cdot \left(\frac{V(t)}{100}\right) \cdot \sqrt{2 \cdot g \cdot \max(0, h(t))}$$

Where $C_v = 0.001\text{ m}^2$ (discharge coefficient) and $g = 9.81\text{ m/s}^2$ (gravitational acceleration). At nominal $h = 1.0\text{ m}$ and $V = 50\%$, nominal outflow is:
$$Q_{\text{out}} = 0.001 \cdot 0.50 \cdot \sqrt{19.62} \approx 0.00221\text{ m}^3/\text{s}$$

---

## 2. Sensor Noise & Discrete Integration

- **Integration Algorithm**: Forward Euler discrete-time stepping with fixed timestep $\Delta t = 1.0\text{ s}$:
  $$h(t + \Delta t) = h(t) + \frac{Q_{\text{in}}(t) - Q_{\text{out}}(t)}{A} \cdot \Delta t$$
- **Sensor Noise**: Zero-mean Gaussian noise added to raw water level:
  $$h_{\text{obs}}(t) = h(t) + \mathcal{N}(0, \sigma^2), \quad \sigma = 0.005\text{ m} \ (0.5\text{ cm})$$
- **Noise Bounds**: The $3\sigma$ noise boundary is $1.5\text{ cm}$. Any constant physical sensor bias below $1.5\text{ cm}$ remains mathematically within natural Gaussian noise fluctuations.
- **Physical Clamping**: The water level is physically bounded by $h \in [0.0\text{ m}, 2.5\text{ m}]$. If $h \le 0.05\text{ m}$, `dry_run` is flagged; if $h \ge 2.5\text{ m}$, `overflow` is flagged.

---

## 3. Plant Equivalence: Batch Simulator vs Streaming LivePlant

A foundational architectural requirement is that the offline dataset generator ([`simulation/process_simulator.py`](file:///c:/projects/p1/New%20folder/simulation/process_simulator.py)) and the real-time streaming simulation engine ([`scada_live/plant_sim/plant.py`](file:///c:/projects/p1/New%20folder/scada_live/plant_sim/plant.py)) must be **bit-for-bit mathematically equivalent**.

### Verification Evidence ([`test_phase2_equivalence.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase2_equivalence.py))
During execution of the live test suite, `test_phase2_equivalence.py` evaluated equivalence across 600 consecutive ticks across 5 scenarios:
1. `N_001` (Normal Closed-Loop): Maximum level difference $\Delta h = 0.000000\text{ m}$.
2. `A1_001` (FDI Attack): Maximum level difference $\Delta h = 0.000000\text{ m}$.
3. `A2_001` (Replay Attack): Maximum level difference $\Delta h = 0.000000\text{ m}$.
4. `A3_001` (DoS Outage): Maximum level difference $\Delta h = 0.000000\text{ m}$.
5. `A4_001` (Auth Misuse): Maximum level difference $\Delta h = 0.000000\text{ m}$.

All 8 tests in `test_phase2_equivalence.py` passed with zero float discrepancy, verifying that models trained on batch data transition to live streaming execution without domain shift.
