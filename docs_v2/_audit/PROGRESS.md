# Progress Tracker: SCADA Hybrid IDS Documentation Audit (docs_v2)

## Current Status
- Phase: Phase 3 - Self-Audit & Final Verification
- Active Task: Phase 3 Verification Scripts & Final Report
- Context usage: Normal

## Tasks Done
- [x] Absolute Rule 2: Recorded SHA-256 hashes of all 353 tracked files into `docs_v2/_audit/hashes_before.txt` (Python hashlib, UTF-8).
- [x] Phase 0: Saved `git rev-parse HEAD` (`b7a6c999dd0b333475349fb33c3272ea434b447c`) and `git log --oneline --stat` to `docs_v2/_audit/outputs/git_log.txt`.
- [x] Phase 0: Saved `git ls-files` grouped by folder with line counts to `docs_v2/_audit/outputs/file_inventory.txt`.
- [x] Phase 0: Created `docs_v2/_audit/existing_docs.md` with first heading and last commit for all 18 existing doc files.
- [x] Phase 0: Created `docs_v2/_audit/UNVERIFIED.md`.
- [x] Phase 1: Database read-only queries saved to `docs_v2/_audit/outputs/query_db.py` and `docs_v2/_audit/outputs/db_queries_output.txt`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__controller.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__noise.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__process_simulator.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__pump.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__scenario_runner.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__tank.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/simulator__valve.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/config__parameters.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/config__scenarios.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/digital_twin__physics_twin.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/engines__physics_engine.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/engines__temporal_engine.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/engines__policy_engine.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/engines__availability_engine.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/engines__fusion_engine.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/models__lstm_autoencoder.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/models__preprocessor.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/models__trainer.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/evaluation__ablation.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/evaluation__metrics.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/evaluation__reporter.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/storage__sqlite_client.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__import_matlab_csv.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__run_ablation.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__run_e0_validation.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__run_evaluation.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__train_lstm.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scripts__validate_matlab_vs_python.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__attacks__apply_fdi.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__attacks__apply_replay.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__attacks__apply_dos.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__attacks__apply_auth_misuse.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__run_single_scenario.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__run_all_scenarios.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__scada_params.m.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/matlab__scada_simulink_guide.m.md`.

- [x] Phase 1: File note `docs_v2/_audit/notes/scada_live__config.yaml.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/run_demo.py.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scada_live__common.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scada_live__plant_sim.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scada_live__attacker_wire.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/scada_live__scada_ids.md`.

- [x] Phase 1: File note `docs_v2/_audit/notes/tests__batch_suite.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/tests__live_suite.md`.
- [x] Phase 1: File note `docs_v2/_audit/notes/experiments__registry.md`.
- [x] Phase 1: Both test suites executed; outputs saved to `pytest_batch_output.txt` (66 passed in 1.86s) and `pytest_live_output.txt` (116 passed in 314.58s).

- [x] Phase 1: Compile `docs_v2/DOC_VS_CODE_DISCREPANCIES.md` auditing all 12 major contradictions between old docs and code.
- [x] Phase 1: Address and verify all 13 "Leads to VERIFY" items with empirical code/data evidence.
- [x] Stop point 1 reached: Phase 1 is 100% complete.

## Next Tasks (Phase 2 - Documentation Writing)
- [x] Phase 2: `00_README_INDEX.md` (Index, reading order, relationship to legacy docs, evidence tag guide)
- [x] Phase 2: `01_ARCHITECTURE_V2.md` (Dual architecture, per-tick sequence, state machines, stubs vs code)
- [x] Stop point 2 reached: 01_ARCHITECTURE_V2.md finished.
- [x] Phase 2: `02_DATASET_DOCUMENTATION_V2.md` (Schema from PRAGMA, scenario taxonomy, data splits, artifacts)
- [x] Stop point 3 reached: 02_DATASET_DOCUMENTATION_V2.md finished.
- [x] Phase 2: `03_FORMULAS_REFERENCE_V2.md` (Continuous and discrete ODEs, engine mathematics, bounds, metrics)
- [x] Phase 2: `04_CODEBASE_MAP.md` (Directory tree, component role, entry points, stubs vs active)
- [x] Phase 2: `05_API_AND_PACKET_REFERENCE.md` (All 21 Flask routes, packet schemas, SSE streams, truth channel)
- [x] Phase 2: `06_CONFIGURATION_REFERENCE.md` (Every key in config.yaml and parameters.py, units, cross-config gaps)
- [x] Phase 2: `07_DETECTION_ENGINES_REFERENCE.md` (Physics, Temporal, Policy, Availability, Fusion engines, mathematical equations, failure modes)
- [x] Phase 2: `08_PREVENTION_AND_CONTROL.md` (Control server, level-source switching, twin takeover, hand-back, DoS gap re-seed rule, command filtering)
- [x] Phase 2: `09_TESTING_GUIDE.md` (Test suites catalog, execution commands, slow tests, real summary metrics from batch & live suites)
- [x] Phase 2: `10_RESULTS_AND_METRICS.md` (Headline numbers, A/B Monitor vs Prevention tables, sweeps, soaks, mismatch study, population definitions)
- [x] Phase 2: `11_KNOWN_LIMITATIONS_AND_FINDINGS.md` (Honest catalog: post-hoc artifacts, noise clamp drift, start-up sensitivity, threshold margins, simulation vs reality)
- [x] Phase 2: `12_RUNBOOK_AND_DEMO_GUIDE.md` (Setup, CLI runners, run_demo.py flags: --soak, --auto, --speed, UI walkthrough, troubleshooting)
- [x] Phase 2: `13_THREAT_MODEL.md` (STRIDE/MITRE ATT&CK for ICS threat model, threat agents, attack taxonomy, detection assumptions, prevention boundaries)
- [x] Phase 2: `14_PROJECT_HISTORY_AND_DECISIONS.md` (Reconstructed project timeline, git log archaeology, architectural phases, design pivot rationales)
- [x] Phase 2: `15_REVIEW_QA_PREP.md` (25 hardest technical review / audit questions with empirical citations)
- [x] Phase 2: `16_GLOSSARY.md` (Standardized terminology, physical units, mathematical notation, abbreviations)
- [ ] Phase 3: Run `check_docs.py` (markdown links, file paths, route definitions, config keys, mermaid blocks)
- [ ] Phase 3: Run `spot_checks.py` auditing 30 numerical claims directly against source data/code
- [ ] Phase 3: Verify bit-for-bit SHA-256 equivalence between `hashes_before.txt` and `hashes_after.txt`
- [ ] Phase 3: Publish `docs_v2/_audit/FINAL_REPORT.md` and sign off

## Blockers
- None.
