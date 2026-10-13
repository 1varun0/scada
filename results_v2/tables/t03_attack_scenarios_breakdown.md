# Table T03: Attack Scenarios Profile & Threat Distribution

> Source: `attack_scenarios` table from `data/scada_ids.db`. Total: 90 attack scenarios.

## Threat Class Breakdown

| Attack Type | Operating Condition | Scenario Count | Start Range (s) | End Range (s) | Avg Duration (s) | Initial Tank Level Range (m) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `Auth_Misuse` | `Misuse_Condition` | 15 | [200, 200] | [300, 300] | 100.0s | [0.40, 2.10] |
| `DoS` | `Steady_State` | 15 | [350, 350] | [370, 470] | 68.0s | [1.00, 1.00] |
| `FDI` | `Steady_State` | 45 | [300, 300] | [500, 500] | 200.0s | [1.00, 1.00] |
| `Replay` | `Steady_State` | 15 | [400, 400] | [430, 500] | 65.0s | [1.00, 1.00] |
| **Total** | - | **90** | - | - | - | - |

## Telemetry Aggregate Ingress Facts

- **Total Ingress Records**: 150,000
- **Total Scenarios**: 150 (60 Normal + 90 Attack)
- **Ticks per Scenario**: Exactly 1,000 ticks (Sequence ID range: 0 to 999)
- **Simulation Time Span**: 0.0s to 999.0s (1.0s tick duration)
- **Normal Ticks (ground_truth = 0)**: 138,215 (92.14%)
- **Attack Ticks (ground_truth = 1)**: 11,785 (7.86%)
- **Dropped Packets (packet_received = 0)**: 1,035 (100% strictly aligned with DoS A3 attack periods)
- **Telemetry Age (data_age_ms)**: Min: 0 ms, Mean: 482.17 ms, Max: 200,000 ms (200.0s buffer stale ceiling during DoS)
