# Work Log - Project Columbus

## 2026-03-30

### 프로젝트 초기 세팅
- **작업**: 프로젝트 디렉토리 구조 생성 및 CLAUDE.md 작성
- **내용**:
  - Git 저장소 초기화
  - 디렉토리 구조 생성 (docs, research, references)
  - 과제 제안서를 docs/ 폴더로 이동
  - CLAUDE.md에 과제 개요, 단계별 목표, 에이전트 작업 지침 정리
- **결과**: 프로젝트 기본 구조 완성
- **다음 단계**: 1단계 1년차 연구 착수를 위한 세부 계획 수립 필요

### 면역 케어 온톨로지 초기 스키마 설계
- **작업**: 온톨로지 도메인 분석, 아키텍처 설계, OWL 스키마 초안 작성
- **내용**:
  1. **기존 온톨로지 서베이** — DO, GO, HPO, ChEBI, ENVO, ExO, OBI 등 9개 온톨로지 조사 및 매핑 전략 수립
  2. **4계층 도메인 분석** — 제안서에서 Layer 1~4의 모든 환경요인, 생체신호, 바이오마커, RONS, 질환 정보 추출
  3. **온톨로지 아키텍처 설계** — BFO 2.0 기반, 5개 모듈(환경-면역연계, 라이프로그, 면역궤적, PMO, 질환) 구조 설계
  4. **OWL 초기 스키마 작성** (immune_care_ontology.owl v0.1.0):
     - 11개 Object Properties, 6개 Data Properties
     - Layer 1: 15개 환경요인 클래스 + 3개 복합지표
     - Layer 2: 6개 라이프로그 클래스
     - Layer 3: 13개 바이오마커 + 6개 신호전달 경로 + 2개 분석법
     - Layer 4 (PMO): 12개 플라즈마 의학 클래스 (기기, RONS, 프로토콜)
     - 질병궤적: 7개 면역질환 + 알레르기 마치 + 인과경로
     - 3개 인스턴스 예시 (PM2.5→IL-6, PM2.5→HRV, 알레르기 마치)
  5. **SPARQL 쿼리 템플릿** — 인과추론 도구 Ver 1.0용 6개 쿼리 템플릿 작성
  6. **선행연구 서베이 문서** — 재사용 온톨로지, 데이터 표준, 환경-면역 DB 정리
- **산출물**:
  - `research/01_ontology/domain_analysis.md`
  - `research/01_ontology/ontology_architecture.md`
  - `research/01_ontology/immune_care_ontology.owl` (v0.1.0 → v0.2.0)
  - `research/01_ontology/sparql_templates.rq`
  - `references/ontology_survey.md`
- **결과**: 면역 케어 온톨로지 초기 스키마 완성 (Protégé 로딩 가능)
- **다음 단계**:
  - OWL 파일에 BFO 2.0 import 추가 및 기존 온톨로지 MIREOT 연결
  - ~~인과 경로 인스턴스 확장 (제안서의 모든 상관관계 데이터 반영)~~ ✅ 완료
  - Protégé에서 HermiT 추론기로 일관성 검증
  - ~~Layer 2 데이터 파이프라인 설계 착수~~ ✅ 완료

### OWL v0.2.0 업그레이드 + 데이터 파이프라인 설계
- **작업**: BFO 정렬, 외부 온톨로지 MIREOT 연결, 인과경로 인스턴스 확장, 데이터 파이프라인 아키텍처 설계
- **내용**:
  1. **BFO 2.0 정렬**: owl:imports 추가, 10개 핵심 클래스에 BFO 상위 클래스 매핑
     - Independent Continuant: Patient, EnvironmentalFactor, ReactiveSpecies, CAPDevice
     - Specifically Dependent Continuant: Biomarker
     - Process: LifelogObservation, SignalingPathway, PlasmaExposureEvent, DiseaseTrajectory
     - Disposition: ImmuneDisease
  2. **외부 온톨로지 MIREOT 스텁**: DO(DOID:2914), GO(GO:0006955, GO:0006954, GO:0000302), ChEBI(6종 RONS), Reactome(NF-κB, Cytokine signaling)
  3. **새 프로퍼티 추가**: hasSourceFactor, hasTargetFactor, involvesPathway, hasSourceLayer, hasTargetLayer, hasEvidenceStrength (6개)
  4. **인과경로 인스턴스 확장** (3개 → 25개):
     - L1→L3: 6개 (PM2.5→IL-6, PM2.5→TNF-α, PM2.5→8-OHdG, PM2.5→CRP, VOCs→IgE, RH→IL-13)
     - L1→L2: 3개 (PM2.5→HRV, PM2.5→SpO2, VOCs→수면)
     - L2→L3: 3개 (HRV→IL-6, 수면부족→CRP, 비활동→TNF-α)
     - L3→Disease: 4개 (IL-4/IL-13→아토피, IgE+IL-5→천식, TNF-α+IL-17→건선, 복합→알레르기마치)
     - L4→L3: 3개 (CAP NO→NF-κB 억제, CAP→Nrf2, CAP패치→건선 치료)
     - 알레르기 마치 궤적 5단계 인스턴스
  5. **데이터 파이프라인 아키텍처** (921줄):
     - Lambda Architecture: Kafka+Flink(hot) / Airflow+Spark(cold)
     - 5종 IoT 센서 수집 전략 (SPS30, SGP41, SCD41, BME680, GC-PID)
     - 3-tier 시간 정렬 (micro/meso/macro)
     - 온톨로지 인스턴스 생성 파이프라인 (YARRRML/Morph-KGC → GraphDB)
     - AI/ML: 114차원 특징 행렬, Multi-task TFT 모델, SHAP-온톨로지 브릿지
     - 30+ 컴포넌트 기술 스택 권고
- **산출물**:
  - `research/01_ontology/immune_care_ontology.owl` (v0.2.0 — 158개 OWL 요소)
  - `research/02_data_pipeline/data_pipeline_architecture.md` (921줄)
- **결과**: 온톨로지 v0.2.0 완성 (BFO 정렬 + 25개 인과경로), 데이터 파이프라인 설계 완료
- **다음 단계**:
  - Protégé에서 HermiT 추론기로 일관성 검증
  - 데이터 파이프라인 PoC 구현 (에지 게이트웨이 → Kafka → 복합지표 계산)
  - AI 모델 아키텍처 상세 설계 (TFT + GNN)

---
