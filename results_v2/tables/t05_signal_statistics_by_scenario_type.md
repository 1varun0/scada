# Table T05: Physical Signal Statistics Across Scenario Groups

> Source: `scada_telemetry` table in `data/scada_ids.db`.

| Scenario Group | Records | Level Min (m) | Level Mean (m) | Level Max (m) | Mean Qin (m³/s) | Mean Qout (m³/s) | Pump Duty Cycle | Attack Tick Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Auth Misuse (A4, N=15)` | 15,000 | 0.3891 | 1.0385 | 2.1043 | 0.001985 | 0.002016 | 39.21% | 10.10% |
| `DoS (A3, N=15)` | 15,000 | 0.7890 | 0.9609 | 1.2131 | 0.001646 | 0.001819 | 32.43% | 6.90% |
| `FDI (A1, N=45)` | 45,000 | 0.7833 | 0.9873 | 1.4113 | 0.002001 | 0.001964 | 39.54% | 18.32% |
| `Normal (N=60)` | 60,000 | 0.4897 | 1.0541 | 1.7125 | 0.002703 | 0.002040 | 53.69% | 0.00% |
| `Replay (A2, N=15)` | 15,000 | 0.7893 | 0.9600 | 1.2099 | 0.002023 | 0.001964 | 39.99% | 6.60% |
