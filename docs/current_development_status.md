# Project Columbus Current Development Status

작성일: 2026-06-28

## 현재 브랜치와 기준 커밋

- 현재 브랜치: `production-hardening`
- 현재 HEAD: `b686414 feat: add NHIS RDF and calibration CLI workflows`
- 원격 반영 상태: 로컬 브랜치 작업 완료, 원격 push/PR은 아직 하지 않음
- 보존 stash:
  - `stash@{0}`: `pre-local-merge-user-worktree-20260628`
  - 병합 전 untracked였던 `research/01_ontology/integrated_knowledge_graph.ttl` 이전 버전이 여기에 남아 있음

최근 주요 커밋:

```text
b686414 feat: add NHIS RDF and calibration CLI workflows
a8ce43b test: tolerate optional research artifacts
f7ec37c ci: add production readiness checks
b6acc19 feat: add read-only ontology API
f784ec7 chore: remove legacy import-time installs
3c8cfe1 feat: add safe evidence calibration
f7f1762 fix: regenerate integrated knowledge graph safely
72af426 chore: add production hardening foundation
```

## 완료된 Production Hardening 범위

현재 연구 프로토타입에서 다음 production baseline이 구축되어 있다.

- Python 패키지 구조 추가: `src/project_columbus/`
- 패키지/의존성/CLI 정의: `pyproject.toml`
- 온톨로지 로더/검증기 추가
- causal reasoning engine의 production API 추가
- 안전한 integrated KG exporter 추가
- evidence calibration production API 추가
- read-only FastAPI 앱 추가
- NHIS correlation summary CSV -> RDF Turtle 변환 모듈 추가
- CLI 추가:
  - `columbus validate-ontology`
  - `columbus export-integrated-kg`
  - `columbus generate-nhis-rdf`
  - `columbus calibrate-evidence`
- CI workflow 추가: `.github/workflows/ci.yml`
- 산출물 정책 문서 추가: `docs/artifact_policy.md`
- production readiness 문서 갱신: `docs/production_readiness.md`

## 주요 Production 모듈

```text
src/project_columbus/
  api/
    app.py                 Read-only FastAPI 앱
    schemas.py             API request schema
  calibration/
    evidence_calibrator.py Non-destructive evidence calibration
  ontology/
    loader.py              OWL/TTL graph loading and label resolution
    validator.py           Parse/structure validation
    integrated_export.py   Integrated KG generation
    models.py              Ontology dataclasses
    namespaces.py          RDF namespace constants
  pipeline/
    nhis_rdf.py            NHIS correlation CSV -> RDF Turtle
  reasoning/
    engine.py              Causal pathway query/reasoning API
  cli.py                   `columbus` CLI entry point
```

## 현재 검증 상태

마지막으로 확인한 전체 검증 결과:

```bash
ruff check .
python -m pytest -q
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
```

결과:

```text
All checks passed!
37 passed
OK triples=821 classes=109 causal_pathways=19 version=0.2.0
OK triples=821 classes=109 causal_pathways=19 version=0.2.0
```

참고:

- `pytest`는 `python -m pytest -q`로 실행하는 것이 안전하다.
- 현재 `ruff` 설정은 `research/`를 제외한다.
- local environment에는 `project-columbus`가 editable install 되어 있다.

## 온톨로지와 KG 상태

Canonical source:

- `research/01_ontology/immune_care_ontology.owl`
- RDF/XML parse OK
- 현재 baseline:
  - 821 triples
  - 109 OWL classes
  - 19 `ico:CausalPathway`
  - `owl:versionInfo`: `0.2.0`

Integrated KG snapshot:

- `research/01_ontology/integrated_knowledge_graph.ttl`
- Turtle parse OK
- 현재 committed snapshot은 core OWL 기반 821 triples
- `research/01_ontology/integrated_knowledge_graph.report.json`은 export provenance를 기록

Optional NHIS RDF input:

- 기본 위치: `research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl`
- 이 디렉터리는 generated artifact로 `.gitignore` 대상
- exporter는 missing optional source는 허용하고, empty/invalid optional RDF는 `optional_invalid`로 보고한다.
- NHIS RDF는 다음 명령으로 재생성한다.

```bash
columbus generate-nhis-rdf \
  --correlation-csv research/02_data_pipeline/correlation_reports/correlation_summary.csv \
  --output research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl \
  --report research/02_data_pipeline/rdf_output/nhis_disease_instances.report.json
```

그 뒤 integrated KG를 갱신하려면:

```bash
columbus export-integrated-kg
```

## Evidence Calibration 상태

Production API:

- `project_columbus.calibration.EvidenceCalibrator`
- source OWL을 기본적으로 직접 덮어쓰지 않음
- `output_owl == source_owl`일 때는 `in_place=True` 없으면 실패
- CSV 필수 컬럼:
  - `env_var`
  - `disease`
  - `lag_months`
  - `mean_pearson_r`
  - `mean_spearman_r`
  - `pct_significant`

CLI:

```bash
columbus calibrate-evidence \
  --source-owl research/01_ontology/immune_care_ontology.owl \
  --correlation-csv <correlation_summary.csv> \
  --output-owl <calibrated.owl> \
  --report <calibration.report.json> \
  --calibration-date 2026-06-28
```

## API 상태

Read-only API 생성 함수:

```python
from project_columbus.api.app import create_app

app = create_app(ontology_path="research/01_ontology/immune_care_ontology.owl")
```

현재 endpoints:

- `GET /health`
- `GET /ontology/stats`
- `POST /query/env-to-pathway`
- `POST /reason/causal-chain`

환경변수:

- `COLUMBUS_ONTOLOGY_PATH`: 기본 ontology path 설정

현재 non-goal:

- 환자 단위 진단/처방/치료 추천 아님
- mutable API endpoint 없음
- RDF store dependency 없음

## 테스트 구성

현재 테스트 수: 37개

주요 테스트 파일:

- `tests/test_package_import.py`
- `tests/test_cli.py`
- `tests/ontology/test_loader.py`
- `tests/ontology/test_validator.py`
- `tests/ontology/test_integrated_kg.py`
- `tests/reasoning/test_engine.py`
- `tests/calibration/test_evidence_calibrator.py`
- `tests/api/test_app.py`
- `tests/pipeline/test_nhis_rdf.py`
- `tests/legacy/test_legacy_entrypoints.py`

## 산출물/문서 관리 정책

정책 문서:

- `docs/artifact_policy.md`

현재 방침:

- git에 넣는 것:
  - `src/`
  - `tests/`
  - 작은 deterministic fixtures
  - canonical ontology source
  - 현재 테스트가 의존하는 reproducible KG snapshot
  - sanitized research scripts/docs
- git 밖에 두는 것:
  - raw NHIS/public data
  - processed parquet
  - EDA/correlation/model output
  - generated RDF output directory
  - IRB/NHIS controlled documents
  - 재생성 가능한 rendered diagrams

`.gitignore`에 추가된 주요 항목:

```gitignore
research/02_data_pipeline/correlation_reports/
research/02_data_pipeline/e2e_results/
research/02_data_pipeline/eda_reports/
research/02_data_pipeline/rdf_output/
research/03_ai_model/model_results/
research/project_architecture.png
docs/IRB_*.docx
docs/IRB_*.hwp
```

## 현재 작업트리의 미커밋 변경

다음 파일들은 현재 작업트리에 남아 있으나, 이번 production hardening 커밋에는 포함하지 않았다.

Modified:

- `CLAUDE.md`
- `work_log.md`
- `docs/*.pdf`
- `docs/*.hwp`

Untracked:

- `docs/generate_irb_draft.py`
- `research/01_ontology/ico_evidence_calibrator.py`
- `research/01_ontology/integrated_sparql_validator.py`
- `research/02_data_pipeline/biomarker_env_analyzer.py`
- `research/02_data_pipeline/env_disease_correlator.py`
- `research/02_data_pipeline/historical_env_collector.py`
- `research/02_data_pipeline/nhis_data_preprocessor.py`
- `research/02_data_pipeline/nhis_eda_report.py`
- `research/02_data_pipeline/nhis_rdf_generator.py`
- `research/02_data_pipeline/realtime_e2e_pipeline.py`
- `research/02_data_pipeline/sigungu_correlator.py`
- `research/02_data_pipeline/sigungu_station_mapper.py`
- `research/03_ai_model/biomarker_risk_predictor.py`
- `research/03_ai_model/env_disease_predictor.py`
- `research/irb_application_draft.md`
- `research/project_architecture.svg`

주의:

- 이 파일들은 사용자/연구 산출물일 수 있으므로 임의 삭제하거나 되돌리지 말 것.
- tracking 여부는 sanitization, artifact policy, 개인정보/IRB 문서 여부를 확인한 뒤 결정할 것.

## 다음 작업 후보

우선순위 1: 남은 연구 스크립트 정리

- `research/02_data_pipeline/*.py`, `research/03_ai_model/*.py`를 다음 세 그룹으로 분류:
  - production package로 승격할 pure logic
  - legacy runner/demo로 유지할 스크립트
  - generated report/model artifact로 git 밖에 둘 결과물
- import-time side effect 제거:
  - 디렉터리 생성
  - logging/matplotlib global 설정
  - `sys.path.insert`
  - hard-coded API key

우선순위 2: feature engineering production package화

- 후보:
  - `composite_index.py`의 pure index functions
  - `sensor_simulator.py`의 deterministic simulation
  - `env_disease_predictor.py`의 feature engineering
  - `biomarker_risk_predictor.py`의 biomarker labeling/features
- 권장 위치:
  - `src/project_columbus/pipeline/indices.py`
  - `src/project_columbus/pipeline/features.py`
  - 또는 `src/project_columbus/features/`

우선순위 3: NHIS RDF와 integrated KG end-to-end fixture 추가

- 작은 de-identified fixture CSV 추가
- `columbus generate-nhis-rdf` -> `columbus export-integrated-kg`까지 이어지는 테스트 추가
- 실제 `rdf_output/`은 계속 generated artifact로 유지

우선순위 4: API 운영 준비

- `COLUMBUS_ONTOLOGY_PATH` 설정 테스트 강화
- invalid ontology path startup behavior 테스트
- API 실행 문서 또는 Docker/dev server entrypoint 추가

우선순위 5: 원격 협업 절차

- `production-hardening`을 원격에 push
- PR 생성
- CI 확인
- 남은 user/research files tracking 정책 확정

## 다음 작업 시작 전 권장 확인 명령

```bash
git status --short --branch
git log --oneline --decorate -8
ruff check .
python -m pytest -q
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
```
