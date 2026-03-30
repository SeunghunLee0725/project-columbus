# 면역 케어 온톨로지 아키텍처 설계

## 1. 상위 온톨로지 (Upper Ontology)

**BFO 2.0 (Basic Formal Ontology)** 채택
- ISO/IEC 21838-2:2021 국제 표준
- OBO Foundry의 모든 생의학 온톨로지와 호환 보장
- DO, GO, HPO, ENVO, ChEBI, OBI, ExO 모두 BFO 기반

### BFO 핵심 구분
- **Continuant** (지속체): 시간을 통해 존재하는 개체
  - Independent Continuant: 환자, 면역세포, 플라즈마 기기
  - Quality: 바이오마커 수치, 온도
  - Disposition: 질병 감수성
- **Occurrent** (발생체): 시간 속에서 전개되는 개체
  - Process: 면역 반응, 플라즈마 치료, 환경 노출
  - Temporal Region: 치료 기간, 관찰 기간

## 2. 재사용 온톨로지 (Imported Ontologies)

| 온톨로지 | IRI | 용도 | 매핑 영역 |
|---------|-----|------|---------|
| Disease Ontology (DO) | `obo:doid.owl` | 면역 질환 분류 | DOID:2914 (면역계 질환) 하위 트리 |
| Gene Ontology (GO) | `obo:go.owl` | 면역 경로, 유전자 기능 | GO:0006955 (면역반응), GO:0000302 (ROS 반응) |
| Human Phenotype Ontology (HPO) | `obo:hp.owl` | 환자 표현형 | HP:0002715 (면역계 이상) |
| ChEBI | `obo:chebi.owl` | RONS 화학종 | CHEBI:26523 (ROS), CHEBI:62764 (RNS) |
| Environment Ontology (ENVO) | `obo:envo.owl` | 환경 요인 | 대기 오염물질, 환경 물질 |
| Exposure Ontology (ExO) | `obo:exo.owl` | 노출 모델링 | 노출 사건, 경로, 기간 |
| OBI | `obo:obi.owl` | 측정 방법 | 분석법, 측정 프로토콜 |
| Relation Ontology (RO) | `obo:ro.owl` | 표준 관계 | has_phenotype, correlated_with 등 |

## 3. 신규 모듈 (Novel Modules) — 본 과제의 기여

### Module 1: 환경-면역 연계 모듈 (EnvImmune)
```
Namespace: ico:envimmune/
핵심 클래스:
  - EnvironmentalExposureEvent
  - OxidativeStressLoad (복합지표)
  - AllergenExposureScore (복합지표)
  - VentilationIndex (복합지표)
  - ExposureImmunePath (노출-면역 경로)
```

### Module 2: 라이프로그 모듈 (Lifelog)
```
Namespace: ico:lifelog/
핵심 클래스:
  - LifelogObservation
  - HRVMeasurement
  - SleepQualityAssessment
  - ActivityLevel
  - WearableDevice
  - BiosignalTimeSeries
```

### Module 3: 면역 궤적 모듈 (ImmuneTrajectory)
```
Namespace: ico:trajectory/
핵심 클래스:
  - DiseaseTrajectory
  - TrajectoryStage
  - AllergicMarchProgression
  - ImmuneRiskScore
  - CausalPathway
  - TrajectoryPrediction
```

### Module 4: 플라즈마 의학 온톨로지 (PMO)
```
Namespace: ico:pmo/
핵심 클래스:
  - ColdAtmosphericPlasmaDevice
  - PlasmaOperatingParameters
  - RONSGeneration
  - RONSSelectivityProfile
  - PlasmaImmuneModulation
  - TreatmentProtocol
  - HormesisResponse
```

## 4. 데이터 표준 정렬

| 표준 | 용도 | 정렬 전략 |
|------|------|---------|
| HL7 FHIR R4 | 임상 데이터 교환 | Observation, Condition, RiskAssessment 리소스 매핑 |
| OMOP CDM | 관찰 연구 데이터 | CONDITION_OCCURRENCE, MEASUREMENT 테이블 정렬 |
| Open mHealth | 웨어러블 데이터 | heart-rate, sleep-duration, physical-activity 스키마 |
| LOINC | 검사 코딩 | 바이오마커/검사 코드 매핑 |
| ICD-10 | 질병 코딩 | DO 경유 면역 질환 코드 매핑 |

## 5. 온톨로지 설계 원칙

1. **Import, Don't Duplicate**: MIREOT/ROBOT으로 기존 온톨로지 용어 가져오기
2. **OBO Foundry 원칙 준수**: CC-BY 라이선스, OWL 포맷, 텍스트 정의 필수
3. **Relation Ontology 사용**: 표준 관계 사용 (has_phenotype, participates_in 등)
4. **모듈화**: 4개 독립 모듈로 유지보수성 확보
5. **GitHub 공개**: OWL 파일 + SPARQL 쿼리 템플릿 배포 (계획서 명시)

## 6. 도구 환경

| 도구 | 용도 |
|------|------|
| Protégé 5.6+ | 온톨로지 편집 |
| ROBOT | CLI 빌드/병합/추론/추출 |
| HermiT/ELK | OWL 추론기 |
| WebVOWL | 시각화 |
| OOPS! | 설계 오류 검사 |
| BioPortal | 기존 온톨로지 검색/매핑 |
