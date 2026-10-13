# Progress Tracker: SCADA Hybrid IDS Documentation Audit (docs_v2)

## Current Status
- Phase: Transition from Phase 0 (Inventory) to Phase 1 (Source File Notes & DB Verification)
- Active Task: Source file inspection and note generation
- Context usage: Normal

## Tasks Done
- [x] Absolute Rule 2: Recorded SHA-256 hashes of all 353 tracked files into `docs_v2/_audit/hashes_before.txt` (Python hashlib, UTF-8).
- [x] Phase 0: Saved `git rev-parse HEAD` (`b7a6c999dd0b333475349fb33c3272ea434b447c`) and `git log --oneline --stat` to `docs_v2/_audit/outputs/git_log.txt`.
- [x] Phase 0: Saved `git ls-files` grouped by folder with line counts to `docs_v2/_audit/outputs/file_inventory.txt`.
- [x] Phase 0: Created `docs_v2/_audit/existing_docs.md` with first heading and last commit for all 18 existing doc files.
- [x] Phase 0: Created `docs_v2/_audit/UNVERIFIED.md`.

## Next Tasks
- [ ] Phase 1: Database read-only queries saved to `docs_v2/_audit/outputs/` (PRAGMA table_info, scenario counts, ticks, initial levels, operating conditions, attack windows).
- [ ] Phase 1: Read code thoroughly and write note for each source file in `docs_v2/_audit/notes/<path_with___>.md`.
  - simulator/ (controller.py, noise.py, process_simulator.py, pump.py, scenario_runner.py, tank.py, valve.py)
  - config/ (parameters.py, scenarios.py)
  - digital_twin/ (physics_twin.py)
  - engines/ (availability_engine.py, fusion_engine.py, physics_engine.py, policy_engine.py, temporal_engine.py)
  - models/ (lstm_autoencoder.py, preprocessor.py, trainer.py)
  - evaluation/ (ablation.py, metrics.py, reporter.py)
  - storage/ (sqlite_client.py)
  - scripts/ (import_matlab_csv.py, run_ablation.py, run_e0_validation.py, run_evaluation.py, train_lstm.py, validate_matlab_vs_python.py)
  - matlab/ (apply_auth_misuse.m, apply_dos.m, apply_fdi.m, apply_replay.m, run_all_scenarios.m, run_single_scenario.m, scada_params.m, scada_simulink_guide.m)
  - dashboard/ (app.py, static/app.js, static/style.css, templates/index.html)
  - scada_live/ (config.yaml, run_demo.py, common/*, plant_sim/*, attacker_wire/*, scada_ids/*)
  - experiments/ (all python scripts and committed results)
  - tests/ and scada_live/tests/ (all test files)
- [ ] Phase 1: Read existing docs vs code, produce `docs_v2/DOC_VS_CODE_DISCREPANCIES.md`.
- [ ] Phase 1: Address all "Leads to VERIFY" items.
- [ ] Phase 1 Verification and pause: STOP and wait for user.

## Blockers
- None.
