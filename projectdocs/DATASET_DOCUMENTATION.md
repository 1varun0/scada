# SCADA IDS: Comprehensive Dataset Documentation

## 1. Dataset Overview & Executive Summary

This dataset represents a high-fidelity, cyber-physical SCADA telemetry benchmark specifically engineered for evaluating multi-evidence anomaly detection algorithms, Digital Twins, and intrusion detection systems (IDS) in critical industrial infrastructure.

* **Total Scenarios:** 150 independent scenarios
* **Total Telemetry Records:** 150,000 samples (1,000 seconds per scenario at 1 Hz resolution)
* **Storage Formats:**
  * Raw Individual CSVs: `matlab/data/N_001.csv` through `N_060.csv`, `A1_001.csv` through `A4_015.csv`
  * Relational SQL Storage: `data/scada_ids.db` (SQLite in WAL mode)
  * Ground-Truth Metadata: `matlab/data/attack_scenarios.csv`
* **Process Topology:** Single-tank water storage and distribution system featuring an ON/OFF feed pump with mechanical delay, a continuously variable gravity-driven discharge valve with actuator slew dynamics, a closed-loop hysteresis controller, and a deterministic fail-safe mechanism.

---

## 2. Dataset Generation Methodology

The dataset was generated using a physics-first simulation architecture validated across both **Python 3.10+** reference models and **MATLAB / Simulink** numerical scripts.

### 2.1 Simulation Execution Pipeline

Each simulation scenario is executed over $T = 1000\text{ s}$ with a discrete timestep $\Delta t = 1.0\text{ s}$ following this sequence at every step $k$:

1. **Setpoint Scheduling:** The current level setpoint $H_{sp}(t)$ is computed from the assigned profile (Constant, Step, or Ramp).
2. **Sensor Measurement & Noise Injection:** True water level $H_{true}(t)$ and flow rates are calculated and perturbed with zero-mean Gaussian noise:
   $$H_{observed}(t) = H_{true}(t) + \mathcal{N}(0, \sigma_H^2), \quad \sigma_H = 0.005\text{ m}$$
   $$Q_{in,obs}(t) = \max\left(0, Q_{in,true}(t) + \mathcal{N}(0, \sigma_Q^2)\right), \quad \sigma_Q = 0.0001\text{ m}^3/\text{s}$$
   $$Q_{out,obs}(t) = \max\left(0, Q_{out,true}(t) + \mathcal{N}(0, \sigma_Q^2)\right)$$
3. **Closed-Loop Controller Decision:**
   * If $H_{observed} < H_{sp} - d \implies \text{pump\_command} = 1$ (PUMP_ON)
   * If $H_{observed} > H_{sp} + d \implies \text{pump\_command} = 0$ (PUMP_OFF)
   * If within deadband $[H_{sp} - d, H_{sp} + d] \implies$ Hold previous command
4. **Actuator Dynamic Propagation:**
   * **Pump:** Commanded state translates to physical execution after inertia delay $\tau_{pump} = 2.0\text{ s}$ (2 steps).
   * **Valve:** Position changes at maximum slew rate $R_{max} = \frac{100\%}{\tau_{valve}} = \frac{100}{1.5} = 66.67\%/\text{s}$.
5. **Physical Flow Computation:**
   * $Q_{in}(t) = Q_{max} \cdot \text{pump\_state}(t)$ where $Q_{max} = 0.005\text{ m}^3/\text{s}$ ($5\text{ L/s}$).
   * $Q_{out}(t) = C_v \cdot \left(\frac{V_{actual}(t)}{100}\right) \cdot \sqrt{H_{true}(t)}$ where $C_v = 0.004\text{ m}^3/\text{s}$.
6. **Hydrodynamic State Integration (Mass Balance):**
   $$H_{true}(t + \Delta t) = \text{clamp}\left(H_{true}(t) + \frac{Q_{in}(t) - Q_{out}(t)}{A} \cdot \Delta t, \; 0, \; H_{max}\right)$$
   where $A = 2.0\text{ m}^2$ and $H_{max} = 2.5\text{ m}$.
7. **Attack Post-Processing:** For attack scenarios, the attack generation engine injects cyber-physical anomalies into the telemetry stream during the prescribed attack window.

### 2.2 Seed Strategy & Reproducibility

To prevent data leakage while guaranteeing 100% deterministic reproducibility:
* **Normal Scenarios (`N_001` – `N_060`):** $\text{Seed} = 42000 + \text{scenario\_index}$ ($\text{Seed } 42001 \to 42060$).
* **Attack Scenarios (`A1_001` – `A4_015`):** $\text{Seed} = 42000 + 100 + \text{scenario\_index}$ ($\text{Seed } 42101 \to 42210$).

---

## 3. Schema & Telemetry Field Definitions

Every scenario produces a CSV table with 25 standardized columns matching the `scada_telemetry` table in SQLite (`scada_ids.db`).

| Field Name | Data Type | Physical Unit / Format | Example Value | Description & Purpose |
|---|---|---|---|---|
| `scenario_id` | TEXT | Identifier | `"N_001"`, `"A1_005"` | Unique scenario trajectory name. |
| `sequence_id` | INTEGER | Counter (0-indexed) | `0, 1, 2, ... 999` | Monotonically increasing timestep counter. |
| `simulation_time_s` | REAL | Seconds ($\text{s}$) | `120.0` | Global simulation epoch clock. |
| `source_time_s` | REAL | Seconds ($\text{s}$) | `120.0` | Virtual sensor generation timestamp. Stale in Replay attacks. |
| `data_age_ms` | INTEGER | Milliseconds ($\text{ms}$) | `0`, `45000` | Derived latency: $(t_{sim} - t_{source}) \times 1000$. Critical for Replay detection. |
| `packet_received` | INTEGER | Boolean (`0` or `1`) | `1` (Normal), `0` (DoS) | Network communication packet delivery flag. |
| `communication_status` | TEXT | Enum string | `"NORMAL"`, `"BLOCKED"` | SCADA network link status indicator. |
| `operating_condition` | TEXT | Enum string | `"Steady_State"`, `"Setpoint_Change"`, `"Variable_Load"`, `"Recovery"` | High-level physical process operational phase. |
| `tank_level_setpoint` | REAL | Meters ($\text{m}$) | `1.0`, `1.5` | Target water level commanded to controller. |
| `tank_level_observed` | REAL | Meters ($\text{m}$) | `1.0042` | Sensor reading received by controller/SCADA (includes noise/attacks). |
| `q_in` | REAL | $\text{m}^3/\text{s}$ | `0.00501` | Reported volumetric inflow from feed pump. |
| `q_out` | REAL | $\text{m}^3/\text{s}$ | `0.00203` | Reported volumetric outflow through control valve. |
| `pump_command` | INTEGER | Binary (`0` or `1`) | `1` (ON), `0` (OFF) | Digital control output issued by controller. |
| `pump_state` | INTEGER | Binary (`0` or `1`) | `1` (ON), `0` (OFF) | Actual mechanical operating state of the pump. |
| `valve_command` | REAL | Percentage ($0.0 - 100.0\%$) | `50.0` | Target valve position requested by controller. |
| `valve_state` | REAL | Percentage ($0.0 - 100.0\%$) | `50.0` | Actual mechanical stem position of the valve. |
| `control_command` | TEXT | Command descriptor | `"HOLD"`, `"PUMP_ON"`, `"PUMP_OFF"`, `"FAILSAFE"` | Structured payload string logged by control unit. |
| `user_id` | TEXT | Username | `"operator_01"`, `"attacker_01"` | SCADA operator session identity. |
| `user_role` | TEXT | RBAC Role | `"operator"`, `"admin"` | Authorization role of current session. |
| `is_authenticated` | INTEGER | Boolean (`0` or `1`) | `1` | Authentication validity flag. |
| `is_authorized` | INTEGER | Boolean (`0` or `1`) | `1` | Command permission authorization flag. |
| `attack_type` | TEXT | Attack category | `"None"`, `"FDI"`, `"Replay"`, `"DoS"`, `"Auth_Misuse"` | Ground-truth attack taxonomy label. |
| `attack_parameter` | REAL | Floating point / NaN | `0.05`, `1.10`, `45.0` | Numerical magnitude of injected attack. |
| `ground_truth` | INTEGER | Binary (`0` or `1`) | `0` (Normal), `1` (Attack) | Per-timestep binary anomaly label for scoring. |
| `replay_source_sequence_id` | REAL / INT | Counter / NaN | `125`, `NaN` | Original `sequence_id` replayed during A2 attack. |

---

## 4. Scenario Breakdown & Taxonomy

The 150 scenarios are organized into 5 primary groups designed to balance normal operational variability against distinct threat vectors.

```
Total: 150 Scenarios (150,000 timesteps)
├── Normal Scenarios (60 Scenarios, 60,000 timesteps)
│   ├── Steady State (N_001 – N_020)
│   ├── Setpoint Step Change (N_021 – N_035)
│   ├── Variable Load Ramp (N_036 – N_050)
│   └── Low Level Recovery (N_051 – N_060)
└── Attack Scenarios (90 Scenarios, 90,000 timesteps)
    ├── A1: False Data Injection (A1_001 – A1_045) [45 Scenarios]
    ├── A2: Replay Attacks (A2_001 – A2_015) [15 Scenarios]
    ├── A3: Denial of Service (A3_001 – A3_015) [15 Scenarios]
    └── A4: Authenticated Misuse (A4_001 – A4_015) [15 Scenarios]
```

### 4.1 Normal Scenarios (60 Scenarios: `N_001` – `N_060`)

These scenarios establish baseline physics and train the LSTM-Autoencoder under legitimate operational dynamics.

| Scenario ID Range | Count | Operating Condition | Initial Level ($H_0$) | Setpoint Profile Behavior | Description & Dynamics |
|---|---|---|---|---|---|
| `N_001` – `N_020` | 20 | `Steady_State` | $1.0\text{ m}$ | Constant at $1.0\text{ m}$ | Steady-state cycling around nominal $1.0\text{ m}$ level within $[0.8, 1.2]\text{ m}$ deadband. |
| `N_021` – `N_035` | 15 | `Setpoint_Change` | $1.0\text{ m}$ | Step: $1.0\text{ m} \to 1.5\text{ m}$ at $t=400\text{ s}$ | Tests transient response to abrupt setpoint adjustment. |
| `N_036` – `N_050` | 15 | `Variable_Load` | $0.8\text{ m}$ | Ramp: $0.8\text{ m} \to 1.4\text{ m}$ ($t=200\text{--}1000\text{ s}$) | Continuous linear setpoint tracking over 800 seconds. |
| `N_051` – `N_060` | 10 | `Recovery` | $0.5\text{ m}$ | Constant at $1.0\text{ m}$ | Recovery from low initial storage ($H_0=0.5\text{ m}$) back to nominal setpoint. |

---

### 4.2 Attack Scenarios (110 Scenarios: `A1_001` – `A4_015`)

Attacks are injected deterministically over specified time windows while physical interactions continue.

#### A1: False Data Injection (FDI) — 45 Scenarios (`A1_001` – `A1_045`)
Sensor readings for tank level are falsified between $t = 300\text{ s}$ and $t = 500\text{ s}$ ($200\text{ s}$ attack window). Flow meters and actuator feedback remain uncompromised.

* **Small Additive Bias ($b = +0.05\text{ m}$, 10 Scenarios: `A1_001` – `A1_010`):**
  $$H_{fake}(t) = H_{actual}(t) + 0.05\text{ m}$$
  *Subtle attack: close to 3-sigma noise band; tests high-sensitivity physics residuals.*
* **Medium Additive Bias ($b = +0.10\text{ m}$, 10 Scenarios: `A1_011` – `A1_020`):**
  $$H_{fake}(t) = H_{actual}(t) + 0.10\text{ m}$$
* **Large Additive Bias ($b = +0.20\text{ m}$, 10 Scenarios: `A1_021` – `A1_030`):**
  $$H_{fake}(t) = H_{actual}(t) + 0.20\text{ m}$$
  *Forces controller to prematurely cut pump, inducing progressive tank drainage.*
* **Multiplicative Scaling ($\alpha = 1.10$, 10 Scenarios: `A1_031` – `A1_040`):**
  $$H_{fake}(t) = 1.10 \times H_{actual}(t)$$
  *State-dependent scaling error.*
* **Intermittent Pulsing Bias ($b = +0.15\text{ m}$, 5 Scenarios: `A1_041` – `A1_045`):**
  $$H_{fake}(t) = \begin{cases} H_{actual}(t) + 0.15\text{ m} & \text{if } (k - k_{start}) \bmod 5 = 0 \\ H_{actual}(t) & \text{otherwise} \end{cases}$$
  *Evasive periodic attack designed to bypass simple EWMA / window smoothing.*

---

#### A2: Replay Attacks — 15 Scenarios (`A2_001` – `A2_015`)
The adversary captures legitimate steady-state level telemetry during a buffer window preceding $t=400\text{ s}$, then replays that buffer continuously from $t=400\text{ s}$ onward.

* **Buffer Durations Tested:** $30\text{ s}, 40\text{ s}, 50\text{ s}, 60\text{ s}, 70\text{ s}, 80\text{ s}, 90\text{ s}, 100\text{ s}, 35\text{ s}, 45\text{ s}, 55\text{ s}, 65\text{ s}, 75\text{ s}, 85\text{ s}, 95\text{ s}$.
* **Mathematical Signature:**
  $$H_{observed}(t) = H_{buffer}(t_{replay}), \qquad t_{source}(t) = t_{source}(t_{replay})$$
  $$\text{DataAge}_{ms}(t) = (t_{sim} - t_{source}(t)) \times 1000 \gg 0$$
* **Ground Truth Tracking:** The field `replay_source_sequence_id` stores the exact historical sequence index being transmitted.

---

#### A3: Denial of Service (DoS) — 15 Scenarios (`A3_001` – `A3_015`)
Network communication is severed starting at $t=350\text{ s}$ for durations ranging from $20\text{ s}$ to $120\text{ s}$.

* **Durations Tested:** $20\text{ s}, 30\text{ s}, 40\text{ s}, 50\text{ s}, 60\text{ s}, 70\text{ s}, 80\text{ s}, 90\text{ s}, 100\text{ s}, 110\text{ s}, 120\text{ s}, 25\text{ s}, 45\text{ s}, 75\text{ s}, 105\text{ s}$.
* **Protocol & Physical Impact:**
  * $\text{packet\_received} = 0$, $\text{communication\_status} = \text{"BLOCKED"}$.
  * Controller activates deterministic fail-safe: $\text{Pump} = 0$ (OFF), $\text{Valve} = 0\%$ (Closed).
  * Outflow drops to 0, locking the remaining water volume in the tank.

---

#### A4: Authenticated Misuse — 15 Scenarios (`A4_001` – `A4_015`)
An adversary operating with valid credentials (`is_authenticated=1`, `is_authorized=1`, `user_id="attacker_01"`) injects hazardous commands between $t=200\text{ s}$ and $t=300\text{ s}$.

| Scenario ID | Injected Command | Physical Condition at Attack Start | Unsafe Actuator Action | Hazardous Failure Mode |
|---|---|---|---|---|
| `A4_001` – `A4_003` | `VALVE_SET_80`, `90`, `100` | Critically Low Level ($H_0 = 0.4\text{ m}$) | Valve opened to $80\text{--}100\%$, Pump forced OFF | Rapid complete drainage / dry run cavitation risk. |
| `A4_004` | `PUMP_ON_AT_HIGH` | Critically High Level ($H_0 = 2.1\text{ m}$) | Pump forced ON ($5\text{ L/s}$), Valve forced Closed ($0\%$) | Tank overflow hazard ($H > 2.5\text{ m}$). |
| `A4_005` – `A4_006` | `VALVE_SET_70`, `95` | Low Level ($H_0 = 0.4\text{ m}$) | Valve opened to $70\text{--}95\%$, Pump OFF | Severe inventory loss. |
| `A4_007` | `PUMP_ON_AT_OVERFLOW` | High Level ($H_0 = 2.1\text{ m}$) | Sustained Pump ON | Structural overflow. |
| `A4_008` – `A4_009` | `VALVE_SET_85`, `75` | Low Level ($H_0 = 0.4\text{ m}$) | Valve opened to $75\text{--}85\%$ | Critical low level. |
| `A4_010` | `PUMP_ON_AT_CRIT_HIGH` | High Level ($H_0 = 2.1\text{ m}$) | Pump forced ON | Overflow limit violation. |
| `A4_011` – `A4_012` | `VALVE_SET_60`, `100_SUSTAINED`| Low Level ($H_0 = 0.4\text{ m}$) | Valve opened to $60\text{--}100\%$ | Unchecked discharge. |
| `A4_013` | `PUMP_FORCE_ON` | High Level ($H_0 = 2.1\text{ m}$) | Pump forced ON | Physical ceiling breach. |
| `A4_014` – `A4_015` | `VALVE_SET_80_LONG`, `90_LONG` | Low Level ($H_0 = 0.4\text{ m}$) | Sustained Valve opening | Critical process exhaustion. |

---

## 5. Storage Architecture & Database Schema

The primary production dataset is stored in SQLite (`data/scada_ids.db`) using **Write-Ahead Logging (WAL)** mode for high-throughput streaming and concurrent read access.

```sql
PRAGMA journal_mode = WAL;

CREATE TABLE scada_telemetry (
    scenario_id TEXT NOT NULL,
    sequence_id INTEGER NOT NULL,
    simulation_time_s REAL NOT NULL,
    source_time_s REAL NOT NULL,
    data_age_ms INTEGER NOT NULL,
    packet_received INTEGER NOT NULL,
    communication_status TEXT NOT NULL,
    operating_condition TEXT NOT NULL,
    tank_level_setpoint REAL NOT NULL,
    tank_level_observed REAL NOT NULL,
    q_in REAL NOT NULL,
    q_out REAL NOT NULL,
    pump_command INTEGER NOT NULL,
    pump_state INTEGER NOT NULL,
    valve_command REAL NOT NULL,
    valve_state REAL NOT NULL,
    control_command TEXT,
    user_id TEXT,
    user_role TEXT,
    is_authenticated INTEGER,
    is_authorized INTEGER,
    attack_type TEXT NOT NULL DEFAULT 'None',
    attack_parameter REAL,
    ground_truth INTEGER NOT NULL DEFAULT 0,
    replay_source_sequence_id INTEGER,
    PRIMARY KEY (scenario_id, sequence_id)
);

CREATE INDEX idx_telemetry_scenario ON scada_telemetry(scenario_id);
CREATE INDEX idx_telemetry_attack ON scada_telemetry(attack_type);
```

---

## 6. How to Load and Inspect the Dataset

### Loading via Python (SQLite)
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("data/scada_ids.db")

# Load a specific scenario
df_n001 = pd.read_sql_query(
    "SELECT * FROM scada_telemetry WHERE scenario_id = 'N_001' ORDER BY sequence_id",
    conn
)

# Check total samples and ground truth distribution
summary = pd.read_sql_query(
    "SELECT attack_type, COUNT(*) as samples, SUM(ground_truth) as anomalies FROM scada_telemetry GROUP BY attack_type",
    conn
)
print(summary)
conn.close()
```

### Loading via Python (Raw CSVs)
```python
import pandas as pd

# Load individual scenario CSV generated by MATLAB or Python
df = pd.read_csv("matlab/data/A1_001.csv")
print(f"Loaded scenario {df['scenario_id'].iloc[0]} with {len(df)} records.")
```
