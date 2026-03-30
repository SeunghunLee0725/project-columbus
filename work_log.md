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
  - `research/01_ontology/immune_care_ontology.owl` (v0.1.0)
  - `research/01_ontology/sparql_templates.rq`
  - `references/ontology_survey.md`
- **결과**: 면역 케어 온톨로지 초기 스키마 완성 (Protégé 로딩 가능)
- **다음 단계**:
  - OWL 파일에 BFO 2.0 import 추가 및 기존 온톨로지 MIREOT 연결
  - 인과 경로 인스턴스 확장 (제안서의 모든 상관관계 데이터 반영)
  - Protégé에서 HermiT 추론기로 일관성 검증
  - Layer 2 데이터 파이프라인 설계 착수

---
