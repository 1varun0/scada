# Progress Tracker: SCADA Hybrid IDS Documentation Audit (docs_v2)

## Current Status
- Phase: Phase 1 - Source File Analysis & Verification
- Active Task: matlab/scada_params.m next
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

## Next Tasks
- [ ] Phase 1: Review and document tests/ (root tests/ and scada_live/tests/).
- [ ] Phase 1: Review experiments/ (scripts, results, and findings).
- [ ] Phase 1: Read existing docs vs code, produce `docs_v2/DOC_VS_CODE_DISCREPANCIES.md`.
- [ ] Phase 1: Address all "Leads to VERIFY" items.
- [ ] Stop point 1: STOP and wait for user after Phase 1 completion.
- [ ] Phase 1: Read existing docs vs code, produce `docs_v2/DOC_VS_CODE_DISCREPANCIES.md`.
- [ ] Phase 1: Address all "Leads to VERIFY" items.
- [ ] Stop point 1: STOP and wait for user after Phase 1 completion.

## Blockers
- None.
