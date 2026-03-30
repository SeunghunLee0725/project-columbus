# 기존 의학 온톨로지 및 데이터 표준 서베이

## 1. 재사용 대상 온톨로지

### 질병/표현형
| 온톨로지 | IRI | 용도 | 핵심 매핑 포인트 |
|---------|-----|------|---------------|
| Disease Ontology (DO) | `obo:doid.owl` | 면역 질환 분류 | DOID:2914 (면역계 질환), ICD-10 교차참조 |
| Human Phenotype Ontology (HPO) | `obo:hp.owl` | 환자 표현형 | HP:0002715 (면역계 이상) |
| SNOMED CT | `snomed.info/sct` | 임상 용어 | 한국은 SNOMED International 회원국 |

### 분자/경로
| 온톨로지 | IRI | 용도 | 핵심 매핑 포인트 |
|---------|-----|------|---------------|
| Gene Ontology (GO) | `obo:go.owl` | 면역 경로/유전자 | GO:0006955 (면역반응), GO:0000302 (ROS 반응) |
| ChEBI | `obo:chebi.owl` | RONS 화학종 | CHEBI:26523 (ROS), CHEBI:62764 (RNS) |
| Reactome | reactome.org | 신호전달 경로 | R-HSA-9607240 (NF-κB), R-HSA-1280215 (사이토카인) |
| KEGG | genome.jp/kegg | 경로 지도 | hsa04064 (NF-κB), hsa04658 (Th1/Th2) |

### 환경/노출
| 온톨로지 | IRI | 용도 | 핵심 매핑 포인트 |
|---------|-----|------|---------------|
| Environment Ontology (ENVO) | `obo:envo.owl` | 환경 요인 | 대기 오염물질, 환경 물질 |
| Exposure Ontology (ExO) | `obo:exo.owl` | 노출 모델링 | 노출 사건-경로-기간-결과 |
| Experimental Factor Ontology (EFO) | `ebi.ac.uk/efo` | 실험 변수 | DO, HPO, ChEBI 교차 통합 |

### 조사/측정
| 온톨로지 | IRI | 용도 |
|---------|-----|------|
| OBI | `obo:obi.owl` | 분석법, 측정 프로토콜 |
| Relation Ontology (RO) | `obo:ro.owl` | 표준 관계 (has_phenotype 등) |

## 2. 데이터 표준

| 표준 | 용도 | 면역케어 온톨로지 연결 |
|------|------|-----------------|
| HL7 FHIR R4/R5 | 임상 데이터 교환 | Observation, Condition, RiskAssessment 리소스 |
| OMOP CDM | 관찰 연구 데이터 | 한국 NHIS → OMOP 매핑 완료 (아주대 FEEDER-NET) |
| Open mHealth | 웨어러블 데이터 | heart-rate, sleep-duration, physical-activity |
| IEEE 11073 | 건강기기 통신 | 심혈관, 활동 모니터 데이터 포맷 |
| LOINC | 검사 코딩 | 바이오마커 표준 코드 |

## 3. 환경-면역 연계 데이터베이스

| 데이터베이스 | 국가 | 규모 | 면역케어 관련성 |
|-----------|------|------|-------------|
| Korean NHIS | 한국 | ~5,200만 (전 국민) | ICD-10 면역질환 + AirKorea 연계 가능 |
| KoGES | 한국 | ~20만 | 유전체 + 환경 + 건강 코호트 |
| UK Biobank | 영국 | ~50만 | PM2.5/NO2 + 유전체 + 종단 추적 |
| NHANES | 미국 | ~5,000/년 | 환경화학물질 + 면역 바이오마커 |
| CTD | 국제 | 문헌 큐레이션 | 화학물질-유전자-질병 상호작용 |
| Exposome-Explorer | 국제 | 노출 바이오마커 | 환경 위험요인 바이오마커 DB |

## 4. 플라즈마 의학 지식 기반 현황

**기존 CAP 치료 온톨로지: 없음** — 본 과제가 세계 최초

관련 자원:
- NCI Thesaurus: 플라즈마(물리) 용어 있으나 CAP 치료 미포함
- MeSH: "Cold Atmospheric Plasma" 전용 헤딩 미등재
- ChEBI: RONS 화학종 완비 (H2O2, NO, O3, •OH, ONOO⁻ 등)
- Reactome/KEGG: NF-κB, Nrf2/Keap1, MAPK 경로 상세 수록

## 5. 상위 온톨로지 및 설계 원칙

- **BFO 2.0**: ISO/IEC 21838-2:2021 — OBO Foundry 필수 상위 온톨로지
- **OBO Foundry 원칙**: 오픈 라이선스(CC-BY), OWL 포맷, PURL 네임스페이스, 텍스트 정의 필수
- **MIREOT**: 외부 온톨로지 용어 최소 정보 참조 패턴
- **ROBOT**: CLI 기반 온톨로지 빌드/병합/추론 도구
