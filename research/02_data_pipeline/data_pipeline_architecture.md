# 면역 케어 데이터 파이프라인 아키텍처
# Immune Care Data Pipeline Architecture

**문서 버전**: 1.0
**작성일**: 2026-03-30
**단계**: 1단계 (시드연구) 설계 문서
**상태**: Draft — Phase 1 architecture design

---

## 목차

1. [전체 아키텍처 개요](#1-전체-아키텍처-개요)
2. [데이터 소스 및 수집 계층](#2-데이터-소스-및-수집-계층)
3. [데이터 처리 파이프라인](#3-데이터-처리-파이프라인)
4. [온톨로지 인스턴스 생성](#4-온톨로지-인스턴스-생성)
5. [AI/ML 통합](#5-aiml-통합)
6. [기술 스택 권고사항](#6-기술-스택-권고사항)
7. [데이터 흐름 다이어그램](#7-데이터-흐름-다이어그램)
8. [단계별 구현 로드맵](#8-단계별-구현-로드맵)

---

## 1. 전체 아키텍처 개요

본 파이프라인은 4계층(환경-라이프로그-바이오마커-플라즈마) 데이터를 통합하여
면역 궤적을 예측하는 엔드-투-엔드 시스템이다. 핵심 설계 원칙은 다음과 같다.

**설계 원칙:**

| 원칙 | 설명 |
|------|------|
| Lambda Architecture | 실시간 스트리밍(hot path)과 배치 처리(cold path) 이중 경로 |
| Schema-on-Read | 이종 센서 데이터를 원본 보존 후 변환 시점에서 스키마 적용 |
| Ontology-First | 모든 통합 데이터는 최종적으로 OWL 온톨로지 인스턴스로 변환 |
| Time-Aligned | 서로 다른 샘플링 주기의 데이터를 통일된 시간축으로 정렬 |
| Privacy-by-Design | 환자 식별자 가명화, 데이터 접근 감사 로그 |

**핵심 성능 목표 (Phase 1):**
- 스트리밍 레이턴시: < 100ms (센서 수집 ~ 복합지표 갱신)
- 배치 처리 윈도우: 일 1회 (새벽 02:00 KST)
- 온톨로지 인스턴스 생성: 시간당 10,000+ 트리플
- SPARQL 쿼리 응답: < 2초 (단일 환자 궤적)

---

## 2. 데이터 소스 및 수집 계층

### 2.1 Layer 1: 환경 IoT 센서

| 센서 | 측정항목 | 프로토콜 | 샘플링 주기 | 데이터 포맷 | 일일 데이터량 (추정) |
|------|---------|---------|-----------|-----------|-------------------|
| SPS30 | PM2.5, PM10 | I2C/UART | 1초 | float32 x2 | ~690 KB |
| SGP41 | VOC Index, NOx | I2C | 1초 | uint16 x2 | ~345 KB |
| SCD41 | CO2, 온도, 습도 | I2C | 5초 | float32 x3 | ~207 KB |
| BME680 | 온도, 습도, 기압, Gas | I2C | 3초 | float32 x4 | ~460 KB |
| GC-PID | BTEX, PFAS | RS-485/Modbus | 30초 | float32 x6 | ~69 KB |

**수집 전략:**
- **에지 게이트웨이**: Raspberry Pi 4B + Sensirion SEK-SEN5x 보드
- **로컬 버퍼링**: SQLite WAL 모드로 네트워크 단절 시 최대 72시간 로컬 저장
- **전송**: MQTT v5 (QoS 1) → 클라우드 MQTT 브로커
- **토픽 구조**: `ico/{patient_id}/env/{sensor_type}/{measurement}`
- **메시지 포맷**: Protocol Buffers (Protobuf) — JSON 대비 60-80% 크기 절감

```
# MQTT 토픽 예시
ico/P001/env/sps30/pm25          # PM2.5 실시간
ico/P001/env/sgp41/voc_index     # VOC Index
ico/P001/env/scd41/co2           # CO2 농도
ico/P001/env/gc_pid/btex         # BTEX 농도
```

**에지 전처리 (게이트웨이 수준):**
- 칼만 필터: SPS30 노이즈 제거 (PM2.5 센서 특성상 습도 보정 필수)
- 이상값 플래깅: 물리적 범위 초과 값 마킹 (PM2.5 > 500 μg/m³ 등)
- 다운샘플링: 1초 원시 → 10초 집계(mean, max) 전송 (대역폭 절감)

### 2.2 Layer 2: 웨어러블 디바이스

| 데이터 | 소스 | 샘플링 주기 | API/프로토콜 |
|--------|------|-----------|------------|
| HRV (RMSSD, SDNN) | 스마트워치 | 5분 요약 | Samsung Health SDK / Apple HealthKit |
| SpO2 | 스마트워치 | 10분 | Samsung Health SDK |
| 수면 단계 | 스마트워치 | 세션별 | Samsung Health SDK |
| 활동량 (걸음, METs) | 스마트워치 | 1분 | Samsung Health SDK |
| 피부온도 | 스마트워치/링 | 1분 | BLE GATT |

**수집 전략:**
- **1차 경로**: 스마트폰 → 제조사 클라우드 API → 당일 배치 풀링 (REST)
- **2차 경로 (연구용)**: BLE GATT 직접 수신 → 에지 게이트웨이 (저지연)
- **데이터 포맷**: Open mHealth JSON 스키마 준수
- **동기화**: 기기 내부 클럭 NTP 동기화, 서버 수신 시 UTC 타임스탬프 부여

```json
{
  "header": {
    "schema_id": {"namespace": "omh", "name": "heart-rate-variability", "version": "1.0"},
    "acquisition_provenance": {"source_name": "Galaxy Watch 7", "modality": "sensed"}
  },
  "body": {
    "effective_time_frame": {"date_time": "2026-05-15T14:30:00+09:00"},
    "rmssd": {"value": 42.3, "unit": "ms"},
    "sdnn": {"value": 55.1, "unit": "ms"}
  }
}
```

### 2.3 Layer 3: 바이오마커 분석

| 분석법 | 마커 | 빈도 | 데이터 특성 |
|--------|------|------|-----------|
| Raman SERS (PoC) | CRP, IL-6 | 주 1-2회 | 정량값 + 스펙트럼 원시 데이터 (1024 pts) |
| ELISA (실험실) | IL-6, TNF-α, IL-4, IL-10, IL-13, IgE, IL-5, IL-17 | 월 1회 | 정량값 (pg/mL) |
| 산화 마커 | 8-OHdG, MDA | 월 1회 | 정량값 |

**수집 전략:**
- **SERS**: 휴대용 라만 분광기 → Bluetooth → 스마트폰 앱 → REST API 업로드
- **ELISA**: LIMS (Laboratory Information Management System) → HL7 FHIR Observation 리소스 → API 수집
- **스펙트럼 데이터**: HDF5 포맷으로 원시 보관, 피크 추출값만 파이프라인 투입
- **LOINC 코딩**: 모든 바이오마커에 LOINC 코드 부여 (예: CRP → LOINC 1988-5)

### 2.4 Layer 4: 플라즈마 치료 디바이스

| 파라미터 | 범위 | 샘플링 |
|---------|------|--------|
| 인가전압 | 0-20 kV | 100 Hz |
| 펄스주파수 | 1-100 kHz | 이벤트 |
| 가스유량 | 0-5 SLM | 1 Hz |
| 처리시간 | 0-300초 | 세션 |
| RONS 농도 (UV-Vis) | 종별 μM | 0.1초 |
| RONS 종별 (EPR) | 종별 스핀 | 세션 |

**수집 전략:**
- **디바이스 컨트롤러**: 임베디드 MCU → USB/UART → 제어 PC
- **세션 기반**: 치료 시작/종료 이벤트로 세션 경계 설정
- **UV-Vis 스펙트럼**: 원시 스펙트럼 HDF5 보관 + 종별 농도 추출값 투입
- **EPR 데이터**: 세션 요약 (g-factor, 스핀 농도) → JSON → API

### 2.5 외부 데이터 소스

| 소스 | 데이터 | API | 갱신 주기 |
|------|--------|-----|---------|
| 건강보험공단 (NHIS) | ICD-10 진료 이력, 처방 | 공공데이터포털 API | 연 1회 (코호트) |
| AirKorea | 대기질 (PM, O3, NO2, SO2) | 에어코리아 API | 1시간 |
| 기상청 (KMA) | 기온, 습도, 기압, 자외선 | 기상자료개방포털 | 1시간 |
| HIRA | 의약품 처방 패턴 | DUR API | 코호트 |

**수집 전략:**
- AirKorea/KMA: 1시간 주기 스케줄링 (Apache Airflow DAG)
- NHIS/HIRA: 연구 승인 후 코호트 데이터 일괄 수집, IRB 관리
- 환자 거주지 기반 가장 가까운 측정소 매핑 (역거리 가중 보간)

---

## 3. 데이터 처리 파이프라인

### 3.1 실시간 스트리밍 경로 (Hot Path)

**대상 데이터**: 환경 센서 (10초 집계), 웨어러블 (분 단위), AirKorea/KMA (시간)

```
[MQTT 브로커] → [Kafka Connect MQTT Source] → [Apache Kafka] → [Apache Flink] → [결과]
```

**Kafka 토픽 설계:**

| 토픽 | 파티션 키 | 보존기간 |
|------|---------|---------|
| `raw.env.sensors` | patient_id | 7일 |
| `raw.wearable.biosignal` | patient_id | 7일 |
| `raw.external.airkorea` | station_id | 3일 |
| `raw.external.kma` | station_id | 3일 |
| `processed.composite_index` | patient_id | 30일 |
| `processed.alerts` | patient_id | 90일 |

**Flink 스트리밍 작업:**

1. **시간 정렬 (Time Alignment)**
   - 이벤트 타임 워터마크: 최대 30초 지연 허용
   - 환경 센서(10초) + 웨어러블(1분) → 1분 텀블링 윈도우로 통합
   - Late event 처리: 사이드 아웃풋으로 분리 후 배치에서 보정

2. **복합지표 실시간 계산**

   **산화스트레스 부하 (Oxidative Stress Load, OSL):**
   ```
   OSL(t) = w1 * norm(PM2.5(t)) + w2 * norm(VOC_index(t)) + w3 * norm(O3_ext(t))

   여기서:
   - norm(): min-max 정규화 (0-1), 기준값은 WHO 가이드라인
   - w1=0.45, w2=0.35, w3=0.20 (문헌 기반 초기 가중치, 학습으로 조정)
   - PM2.5: 실내 SPS30 + 외부 AirKorea 가중 합산
   - O3_ext: AirKorea 측정값 (실내 센서 미설치 시)
   ```

   **알레르겐 노출점수 (Allergen Exposure Score, AES):**
   ```
   AES(t) = w4 * humidity_risk(RH(t)) + w5 * mold_risk(T(t), RH(t))

   여기서:
   - humidity_risk(): RH > 65% 구간에서 비선형 증가
   - mold_risk(): 온도-습도 교차 함수 (ASHRAE 곰팡이 성장 모델)
   - w4=0.6, w5=0.4
   ```

   **환기지수 (Ventilation Index, VI):**
   ```
   VI(t) = CO2_decay_rate(t) / reference_decay_rate

   여기서:
   - CO2_decay_rate: 환기 이벤트 후 CO2 감소 기울기 (ppm/min)
   - reference_decay_rate: 기준 환기율(0.5 ACH) 시 예상 감쇠율
   ```

3. **알림 생성**
   - OSL > 0.7 지속 2시간 → "높은 산화스트레스 노출" 알림
   - HRV (RMSSD) < 20ms 지속 30분 → "자율신경 저하" 알림
   - 복합 조건: OSL > 0.5 AND HRV < 30ms → "면역 스트레스 경고"

### 3.2 배치 처리 경로 (Cold Path)

**대상 데이터**: 바이오마커, 플라즈마 세션, NHIS, 일일 요약, 모델 재학습

**오케스트레이션**: Apache Airflow

**주요 DAG:**

| DAG | 스케줄 | 설명 |
|-----|--------|------|
| `daily_aggregation` | 매일 02:00 KST | 센서/웨어러블 일일 요약 통계 생성 |
| `biomarker_ingestion` | 이벤트 트리거 | SERS/ELISA 결과 수신 시 파이프라인 가동 |
| `plasma_session_etl` | 이벤트 트리거 | 플라즈마 치료 세션 완료 시 ETL |
| `external_data_sync` | 매시간 | AirKorea, KMA 데이터 동기화 |
| `ontology_generation` | 매일 03:00 KST | 일일 데이터 → OWL 인스턴스 변환 |
| `model_retrain` | 주 1회 (일요일) | 궤적 예측 모델 재학습 |
| `data_quality_audit` | 매일 04:00 KST | 결측, 이상값, 센서 드리프트 보고서 |

### 3.3 시간축 정렬 전략 (Cross-Layer Time Alignment)

4계층의 샘플링 주기가 극단적으로 다르므로 (1초 ~ 월 1회), 다음 3단계 전략을 적용한다.

**Tier 1: Micro-alignment (초~분)**
- 환경 센서 + 웨어러블 → 1분 텀블링 윈도우
- Flink 이벤트 타임 기반 워터마크 (30초 허용)

**Tier 2: Meso-alignment (시간~일)**
- 1분 데이터 → 시간별/일별 요약 집계
- 요약 통계: mean, median, p95, max, min, std, trend_slope
- AirKorea/KMA 시간 데이터와 시간 단위 조인

**Tier 3: Macro-alignment (주~월)**
- 바이오마커(주/월) 시점 기준으로 환경/라이프로그 윈도우 역추적
- 예: IL-6 측정일 기준 [-7d, 0d] 환경 노출 통계를 피처로 생성
- 지연 효과(lag) 반영: PM2.5→IL-6는 6-24h lag, VOC→IgE는 수 주 lag
- 가변 윈도우: 각 인과 경로의 알려진 lag에 맞춘 역추적 윈도우

```
시간 해상도 정렬 다이어그램:

  환경센서     1s → [에지] → 10s → [Flink] → 1min → 1hr → 1day
  웨어러블     1min ──────────────→ [Flink] → 1min → 1hr → 1day
  AirKorea     1hr ────────────────────────────────→ 1hr → 1day
  바이오마커   주/월 ─────────────────────────→ [역추적 윈도우 조인]
  플라즈마     세션 ──────────────────────────→ [세션 요약] → 1day
                                                      ↓
                                              [Macro-aligned Feature Matrix]
```

### 3.4 데이터 품질 및 결측값 처리

**품질 관리 계층:**

| 계층 | 검사 항목 | 조치 |
|------|---------|------|
| L0: 원시 | 물리적 범위 (PM2.5: 0-500), 타입 검증 | 범위 초과 → flag + clamp |
| L1: 에지 | 센서 상태, 연속성 (gap > 5분) | 상태 코드 부착, gap 보고 |
| L2: 인제스트 | 중복 제거 (idempotent key), 순서 보장 | Kafka exactly-once |
| L3: 처리 | 통계적 이상값 (IQR 3.0배) | 플래깅, 윈도우 통계에서 제외 |
| L4: 통합 | 교차 센서 일관성 (BME680 vs SCD41 온도) | 불일치 > 2도 → 센서 점검 알림 |

**결측값 처리 전략:**

| 결측 유형 | 조건 | 보간 방법 |
|----------|------|---------|
| 순간 결측 (< 5분) | 단일 센서 일시 누락 | 선형 보간 |
| 단기 결측 (5분~1시간) | 네트워크 단절 등 | 에지 로컬 캐시에서 복구, 없으면 스플라인 보간 |
| 장기 결측 (> 1시간) | 센서 고장 | AirKorea 외부 데이터로 대체 (실내/실외 비율 모델 적용) |
| 웨어러블 미착용 | 활동량 0 + HRV 없음 | 결측 마킹 (NaN), 일일 요약에서 착용률 메타데이터 기록 |
| 바이오마커 미측정 | 스케줄 누락 | 보간하지 않음, 모델에서 마스킹 처리 |

---

## 4. 온톨로지 인스턴스 생성

### 4.1 변환 파이프라인: 센서 데이터 → OWL 인스턴스

원시 센서 데이터가 OWL 온톨로지 인스턴스(ABox)로 변환되는 과정은 4단계이다.

```
[집계 데이터] → [Semantic Mapper] → [RDF 트리플] → [Triple Store] → [SPARQL 엔드포인트]
```

**Stage 1: 측정 이벤트 인스턴스화**

일별 집계 데이터 1행이 다음과 같은 OWL 인스턴스 그래프로 변환된다.

```turtle
# 환경 측정 인스턴스
ico:env_obs_P001_20260515 a ico:envimmune/EnvironmentalExposureEvent ;
    obi:has_specified_input ico:sensor_sps30_P001 ;
    ico:envimmune/has_pm25_value "23.5"^^xsd:float ;
    ico:envimmune/has_voc_index "142"^^xsd:integer ;
    ico:envimmune/has_co2_ppm "680"^^xsd:float ;
    obi:has_measurement_unit_label "μg/m³" ;
    ro:occurs_in ico:location_P001_home ;
    bfo:has_temporal_region ico:time_20260515 .

# 복합지표 인스턴스
ico:osl_P001_20260515 a ico:envimmune/OxidativeStressLoad ;
    ico:envimmune/has_osl_value "0.62"^^xsd:float ;
    ro:derives_from ico:env_obs_P001_20260515 ;
    bfo:has_temporal_region ico:time_20260515 .

# 바이오마커 인스턴스
ico:biomarker_P001_20260515 a obi:Assay ;
    obi:has_specified_output ico:il6_result_P001_20260515 ;
    ico:lifelog/has_crp_value "2.8"^^xsd:float ;
    ico:lifelog/has_il6_value "4.2"^^xsd:float ;
    loinc:code "1988-5" ;
    bfo:has_temporal_region ico:time_20260515 .
```

**Stage 2: 인과 관계 트리플 생성**

도메인 분석에서 확립된 인과 경로를 관계 트리플로 인코딩한다.

```turtle
# PM2.5 → ROS → NF-κB → IL-6 인과 체인
ico:causal_pm25_il6 a ico:trajectory/CausalPathway ;
    ico:trajectory/has_upstream_factor ico:env_obs_P001_20260515 ;
    ico:trajectory/has_downstream_effect ico:il6_result_P001_20260515 ;
    ico:trajectory/has_correlation_coefficient "0.52"^^xsd:float ;
    ico:trajectory/has_temporal_lag "PT12H"^^xsd:duration ;
    ico:trajectory/has_mechanism "PM2.5→ROS→NF-κB→IL-6" ;
    ico:trajectory/has_evidence_level "literature" .
```

**Stage 3: 질병 궤적 인스턴스화**

```turtle
# 환자 P001의 알레르기 마치 궤적
ico:trajectory_P001 a ico:trajectory/DiseaseTrajectory ;
    ico:trajectory/has_subject ico:patient_P001 ;
    ico:trajectory/has_stage ico:stage_P001_AD ;
    ico:trajectory/has_stage ico:stage_P001_asthma ;
    ico:trajectory/follows ico:trajectory/AllergicMarchProgression .

ico:stage_P001_AD a ico:trajectory/TrajectoryStage ;
    ico:trajectory/has_disease doid:atopic_dermatitis ;
    icd10:code "L20" ;
    ico:trajectory/onset_date "2024-03-01"^^xsd:date ;
    ico:trajectory/has_risk_score "0.72"^^xsd:float .
```

### 4.2 Semantic Mapper 구현 전략

**매핑 규칙 엔진:**
- YARRRML (YAML-based RML) 템플릿으로 선언적 매핑 규칙 정의
- RMLMapper 또는 Morph-KGC로 규칙 실행
- 매핑 규칙은 `ontology_mappings/` 디렉토리에서 버전 관리

```yaml
# YARRRML 매핑 예시 (환경 센서 → OWL)
prefixes:
  ico: http://purl.org/ico/
  obi: http://purl.obolibrary.org/obo/OBI_
  xsd: http://www.w3.org/2001/XMLSchema#

mappings:
  environmental_observation:
    sources:
      - [daily_env_summary.csv~csv]
    subject: ico:env_obs_$(patient_id)_$(date)
    predicateobjects:
      - [a, ico:envimmune/EnvironmentalExposureEvent]
      - [ico:envimmune/has_pm25_value, $(pm25_mean), xsd:float]
      - [ico:envimmune/has_voc_index, $(voc_mean), xsd:integer]
      - [bfo:has_temporal_region, ico:time_$(date)]
```

### 4.3 Triple Store 및 SPARQL 엔드포인트

**저장소 선택: Ontotext GraphDB (Free/Enterprise)**

선택 근거:
- OWL 2 RL 추론 내장 (HermiT/ELK 대비 대용량 ABox에 효율적)
- SPARQL 1.1 Full 지원, GeoSPARQL 확장
- SHACL 제약 조건 검증 지원
- 한국어 텍스트 인덱싱 (Lucene 기반)

**SPARQL 쿼리 템플릿 예시:**

```sparql
# Q1: 특정 환자의 환경 노출과 바이오마커 상관 분석
PREFIX ico: <http://purl.org/ico/>
PREFIX ro: <http://purl.obolibrary.org/obo/RO_>

SELECT ?date ?osl_value ?il6_value ?hrv_rmssd
WHERE {
  ?env a ico:envimmune/OxidativeStressLoad ;
       ico:envimmune/has_osl_value ?osl_value ;
       bfo:has_temporal_region ?time .
  ?bio obi:has_specified_output ?il6_result ;
       ico:lifelog/has_il6_value ?il6_value ;
       bfo:has_temporal_region ?time .
  ?hrv a ico:lifelog/HRVMeasurement ;
       ico:lifelog/has_rmssd ?hrv_rmssd ;
       bfo:has_temporal_region ?time .
  ?time ico:has_date ?date .
  FILTER(?date >= "2026-05-01"^^xsd:date && ?date <= "2026-05-31"^^xsd:date)
}
ORDER BY ?date

# Q2: 인과 경로 추론 — PM2.5 노출이 높은 날의 후속 IL-6 변화
PREFIX ico: <http://purl.org/ico/>

SELECT ?patient ?exposure_date ?pm25 ?il6_date ?il6_value
WHERE {
  ?env a ico:envimmune/EnvironmentalExposureEvent ;
       ico:envimmune/has_pm25_value ?pm25 ;
       bfo:has_temporal_region ?t1 .
  ?bio obi:has_specified_output ?result ;
       ico:lifelog/has_il6_value ?il6_value ;
       bfo:has_temporal_region ?t2 .
  ?t1 ico:has_date ?exposure_date .
  ?t2 ico:has_date ?il6_date .
  FILTER(?pm25 > 35.0)
  FILTER(?il6_date > ?exposure_date && ?il6_date <= ?exposure_date + "P2D"^^xsd:duration)
}

# Q3: 알레르기 마치 진행 패턴 탐색
PREFIX ico: <http://purl.org/ico/>

SELECT ?patient ?disease1 ?onset1 ?disease2 ?onset2
WHERE {
  ?traj a ico:trajectory/DiseaseTrajectory ;
        ico:trajectory/has_subject ?patient ;
        ico:trajectory/has_stage ?s1 ;
        ico:trajectory/has_stage ?s2 .
  ?s1 ico:trajectory/has_disease ?disease1 ;
      ico:trajectory/onset_date ?onset1 .
  ?s2 ico:trajectory/has_disease ?disease2 ;
      ico:trajectory/onset_date ?onset2 .
  FILTER(?onset2 > ?onset1)
}
ORDER BY ?patient ?onset1
```

---

## 5. AI/ML 통합

### 5.1 피처 엔지니어링

4계층 데이터에서 추출되는 피처 매트릭스는 다음과 같이 구성된다.

**피처 카테고리:**

| 카테고리 | 피처 예시 | 차원 | 시간 해상도 |
|---------|---------|------|-----------|
| 환경 통계 | pm25_{mean,p95,max}_7d, voc_{mean,trend}_7d | ~30 | 일별 |
| 복합지표 | osl_{mean,max,auc}_7d, aes_mean_7d, vi_mean_7d | ~15 | 일별 |
| 라이프로그 | hrv_rmssd_mean_7d, sleep_deep_ratio, steps_mean | ~20 | 일별 |
| 바이오마커 | il6_latest, crp_latest, ige_latest, il6_trend | ~15 | 측정 시점 |
| 외부환경 | airkorea_pm25_mean_7d, kma_temp_mean, uv_index | ~10 | 일별 |
| 인구통계 | age, sex, bmi, smoking, allergy_family_hx | ~8 | 정적 |
| 플라즈마 (해당 시) | last_treatment_days_ago, cumulative_rons_dose | ~6 | 세션별 |
| 교차 피처 | osl_x_hrv_ratio, pm25_lag12h_x_il6 | ~10 | 일별 |
| **합계** | | **~114** | |

**피처 생성 파이프라인:**

```
[Time-Aligned Store] → [Feature Store (Feast)] → [Training / Inference]
```

- **Feast (Feature Store)**: 오프라인(학습)과 온라인(추론) 피처를 일관되게 제공
- **시간 윈도우 피처**: 7일, 14일, 30일 롤링 통계 (mean, std, trend, AUC)
- **Lag 피처**: 인과 경로별 알려진 시간 지연 반영 (예: pm25_lag_24h)
- **교차 피처**: 계층 간 상호작용 (예: 높은 OSL + 낮은 HRV = 면역 취약 상태)

### 5.2 질병 궤적 예측 모델 아키텍처

**모델 구조: Multi-task Temporal Fusion Transformer (TFT) + Knowledge-Informed Embedding**

선택 근거:
- TFT는 다변량 시계열에서 variable-wise attention을 통해 각 피처의 기여도를 자체 해석 가능
- 바이오마커처럼 불규칙 간격 데이터 처리에 강점
- 멀티태스크 헤드로 여러 질환 궤적을 동시에 예측

```
[Feature Matrix (114D)]
        |
[Static Covariate Encoder] ← (age, sex, bmi, genetics)
        |
[Variable Selection Network] ← attention으로 피처 중요도 학습
        |
[LSTM Encoder] ← 과거 시계열 (lookback: 90일)
        |
[Interpretable Multi-Head Attention]
        |
  ┌─────┼─────┐
  |     |     |
[Head1] [Head2] [Head3]
 AD     Asthma  Rhinitis   ← 질환별 위험도 (0-1)
 risk   risk    risk
```

**모델 구성 요소:**

1. **입력 처리**
   - Static Covariates: Entity Embedding으로 범주형 변수 인코딩
   - Time-Varying Known: 요일, 계절, AirKorea 예보
   - Time-Varying Unknown: 센서 데이터, 바이오마커 (실시간 관측)

2. **Knowledge-Informed Embedding**
   - 온톨로지의 인과 경로를 soft constraint로 주입
   - 예: PM2.5→IL-6 경로가 존재하면, 해당 피처 쌍의 attention에 prior 부여
   - 구현: Regularization term으로 추가 (attention weight와 온톨로지 관계 일치도)

3. **출력 헤드**
   - 각 면역 질환별 30일/90일/180일 발생 확률
   - 전반적 면역 위험 점수 (Immune Risk Score, 0-100)

**보조 모델:**

| 모델 | 용도 | 아키텍처 |
|------|------|---------|
| Anomaly Detector | 센서 이상값/고장 탐지 | Isolation Forest + LSTM-AE |
| Imputation Model | 결측값 고급 보간 | SAITS (Self-Attention Imputation for Time Series) |
| Causal Discovery | 인과 구조 탐색 | PCMCI+ (Tigramite) |

### 5.3 XAI (설명 가능한 AI) 통합

**SHAP 분석 파이프라인:**

```
[Trained TFT Model]
        |
[SHAP DeepExplainer / KernelExplainer]
        |
  ┌─────┼─────┐
  |     |     |
[Global SHAP]  [Local SHAP]  [Temporal SHAP]
 피처 중요도    개별 예측 설명   시점별 기여도 변화
```

**통합 전략:**

1. **Global Explanation**
   - 전체 코호트에서 피처 중요도 순위 → 온톨로지 인과 경로 검증
   - SHAP 중요도 상위 피처 ↔ 온톨로지 CausalPathway 매칭

2. **Local Explanation (개인별)**
   - 환자 P001의 "천식 위험도 0.72" 예측에 대해:
     - "지난 7일 OSL 평균 0.68 (기여도 +0.15)"
     - "HRV RMSSD 평균 28ms (기여도 +0.11)"
     - "최근 IL-6: 5.2 pg/mL (기여도 +0.09)"
   - SHAP 값 → 온톨로지 CausalPathway 매핑 → 자연어 설명 생성

3. **SHAP-Ontology Bridge**
   - SHAP 상위 피처를 SPARQL로 온톨로지 인과 경로 조회
   - 통계적 설명(SHAP) + 의학적 설명(온톨로지) 결합
   - 예: "PM2.5 노출이 높아 IL-6 상승이 예상됩니다 (PM2.5→ROS→NF-κB→IL-6 경로, r=0.52)"

### 5.4 GNN 기반 온톨로지 자동 생성

**목적**: 데이터에서 새로운 인과 관계를 발견하여 온톨로지에 제안

**아키텍처: Relational GNN (R-GCN)**

```
[기존 온톨로지 그래프] → [R-GCN Encoder] → [Link Prediction Decoder]
                                                    |
                                              [신규 관계 후보]
                                                    |
                                              [전문가 검증]
                                                    |
                                              [온톨로지 업데이트]
```

**프로세스:**

1. 온톨로지 TBox + ABox를 DGL (Deep Graph Library) 이종 그래프로 변환
2. R-GCN으로 노드 임베딩 학습 (엔티티: 환경요인, 바이오마커, 질환 등)
3. Link Prediction: 존재하지 않는 엣지 중 확률 높은 것을 신규 관계 후보로 추출
4. 전문가 검증 후 온톨로지에 반영 (Human-in-the-loop)

**예상 발견 유형:**
- "피부온도 일주기 진폭 감소 → 건선 악화" (기존 문헌에 없는 관계)
- "수면 깊은 수면 비율 → IL-10 수준" (간접 경로 발견)

---

## 6. 기술 스택 권고사항

### 6.1 전체 기술 스택 매트릭스

| 계층 | 컴포넌트 | 추천 기술 | 대안 | 선택 근거 |
|------|---------|---------|------|---------|
| **에지** | 게이트웨이 | Raspberry Pi 4B + Python | ESP32 (저전력) | I2C 센서 5종 동시 구동, 로컬 SQLite 버퍼 |
| **에지** | 메시지 직렬화 | Protocol Buffers | MessagePack | 스키마 정의로 버전 관리 용이 |
| **에지** | 전송 | MQTT v5 (Mosquitto) | AMQP | IoT 표준, QoS 1, 저대역폭 |
| **수집** | 메시지 브로커 | Apache Kafka 3.x | Redpanda | 검증된 확장성, Kafka Connect 생태계 |
| **수집** | 커넥터 | Kafka Connect (MQTT Source) | 커스텀 | 코드 없이 구성 가능 |
| **스트리밍** | 처리 엔진 | Apache Flink 1.18+ | Kafka Streams | 이벤트 타임 처리, 복잡 윈도우, 상태 관리 |
| **배치** | 오케스트레이션 | Apache Airflow 2.x | Prefect | 커뮤니티 규모, DAG 시각화, 한국 사용 사례 다수 |
| **배치** | 처리 엔진 | Apache Spark 3.x (PySpark) | Dask | 대규모 코호트 데이터 처리 |
| **저장** | 시계열 DB | TimescaleDB (PostgreSQL) | InfluxDB | SQL 호환, 하이퍼테이블 파티셔닝, JOIN 지원 |
| **저장** | 원시 데이터 | MinIO (S3 호환) | Local FS | HDF5/Parquet 원시 파일 객체 저장 |
| **저장** | 피처 스토어 | Feast | Tecton | 오픈소스, 오프라인/온라인 일관성 |
| **지식그래프** | Triple Store | Ontotext GraphDB | Apache Jena Fuseki | OWL 추론, SPARQL, SHACL 검증 |
| **지식그래프** | 온톨로지 편집 | Protege 5.6 + ROBOT CLI | TopBraid | OBO Foundry 표준, CI/CD 빌드 |
| **지식그래프** | RDF 매핑 | Morph-KGC + YARRRML | RMLMapper | Python 네이티브, 성능 우수 |
| **지식그래프** | Python OWL | Owlready2 | RDFLib + OWL-RL | OWL 클래스 직접 조작, 추론기 연동 |
| **ML** | 프레임워크 | PyTorch 2.x + PyTorch Lightning | TensorFlow | 연구 유연성, TFT 구현체 존재 |
| **ML** | 시계열 | PyTorch Forecasting (TFT) | GluonTS | TFT 기본 제공, 해석 가능성 도구 내장 |
| **ML** | GNN | DGL (Deep Graph Library) | PyG | 이종 그래프 지원, R-GCN 내장 |
| **ML** | XAI | SHAP + Captum | LIME | DeepSHAP PyTorch 지원, 시계열 특화 |
| **ML** | 인과 추론 | Tigramite (PCMCI+) | DoWhy | 시계열 인과 발견 특화 |
| **ML** | 실험 추적 | MLflow | Weights & Biases | 온프레미스 가능, 모델 레지스트리 |
| **인프라** | 컨테이너 | Docker + Docker Compose | K8s (3단계) | 1단계 소규모 적합, 3단계에서 K8s 전환 |
| **인프라** | 모니터링 | Prometheus + Grafana | Datadog | 오픈소스, 센서 대시보드 |
| **인프라** | 로그 | Loki + Grafana | ELK | 경량, Grafana 통합 |
| **보안** | 인증 | Keycloak | Auth0 | 온프레미스, OIDC/SAML |
| **보안** | 가명화 | ARX (k-anonymity) | 자체 구현 | 의료 데이터 가명화 전용 도구 |

### 6.2 핵심 성능 요구사항 대응

| 요구사항 | 목표 | 대응 기술 |
|---------|------|---------|
| 스트리밍 레이턴시 < 100ms | 센서→복합지표 | Kafka(p99 < 10ms) + Flink(처리 < 50ms) + 네트워크(< 40ms) |
| SPARQL 응답 < 2초 | 단일 환자 조회 | GraphDB 인메모리 인덱스 + 환자별 Named Graph 파티셔닝 |
| 일일 온톨로지 생성 | 10K+ 트리플/시간 | Morph-KGC 배치 모드 + GraphDB Bulk Load API |
| 모델 추론 | < 500ms | TorchServe + GPU (RTX 3060 이상) |

---

## 7. 데이터 흐름 다이어그램

### 7.1 전체 아키텍처 다이어그램

```
+=====================================================================+
|                        DATA SOURCES (Layer 1~4)                      |
+=====================================================================+
|                                                                      |
|  [SPS30]  [SGP41]  [SCD41]  [BME680]  [GC-PID]    <-- IoT Sensors  |
|     |        |        |        |         |                           |
|     +--------+--------+--------+---------+                           |
|                    |                                                 |
|            [Edge Gateway]  ← Kalman filter, downsampling             |
|              (RPi 4B)      ← SQLite local buffer (72h)               |
|                    |                                                 |
|               MQTT v5 (Protobuf)                                     |
|                    |                                                 |
|  [Smartwatch] ──BLE/API──→ [Phone App]                               |
|                                 |                                    |
|  [SERS Device] ──BT──→ [Phone App]                                   |
|                                 |                                    |
|  [ELISA/Lab] ──FHIR──→ [LIMS]  |                                    |
|                            |    |                                    |
|  [Plasma Device] ──UART──→ [Control PC]                              |
|                                 |                                    |
|  [AirKorea] ──REST──→ |        |                                    |
|  [KMA]      ──REST──→ |        |                                    |
|  [NHIS]     ──Batch─→ |        |                                    |
|                        |        |                                    |
+========================|========|====================================+
                         |        |
                         v        v
+=====================================================================+
|                     INGESTION LAYER                                  |
+=====================================================================+
|                                                                      |
|  [Mosquitto MQTT Broker]                                             |
|         |                                                            |
|  [Kafka Connect]          [REST API Gateway]                         |
|    MQTT Source              (FastAPI)                                 |
|         |                      |                                     |
|         v                      v                                     |
|  +-------------------------------------------+                       |
|  |          Apache Kafka Cluster             |                       |
|  |  Topics:                                  |                       |
|  |   raw.env.sensors                         |                       |
|  |   raw.wearable.biosignal                  |                       |
|  |   raw.biomarker.assay                     |                       |
|  |   raw.plasma.session                      |                       |
|  |   raw.external.airkorea                   |                       |
|  |   raw.external.kma                        |                       |
|  +-------------------------------------------+                       |
|                         |                                            |
+=========================|============================================+
            +-------------+-------------+
            |                           |
            v                           v
+========================+  +============================+
|   HOT PATH (Stream)   |  |   COLD PATH (Batch)        |
+========================+  +============================+
|                        |  |                            |
| [Apache Flink Cluster] |  | [Apache Airflow]           |
|                        |  |   |                        |
| Jobs:                  |  |   +-- daily_aggregation    |
| - Time alignment       |  |   +-- biomarker_ingestion  |
|   (1-min tumbling)     |  |   +-- plasma_session_etl   |
| - OSL calculation      |  |   +-- external_data_sync   |
| - AES calculation      |  |   +-- ontology_generation  |
| - VI calculation       |  |   +-- model_retrain        |
| - Alert generation     |  |   +-- data_quality_audit   |
|                        |  |                            |
| Output:                |  | [Apache Spark]             |
| - Kafka: processed.*   |  |   - Cohort analytics       |
| - TimescaleDB: realtime|  |   - NHIS data processing   |
|                        |  |                            |
+========================+  +============================+
            |                           |
            v                           v
+=====================================================================+
|                      STORAGE LAYER                                   |
+=====================================================================+
|                                                                      |
|  [TimescaleDB]         [MinIO]           [Feast]                     |
|   Time-series data      Raw files         Feature Store              |
|   (hypertables)         (HDF5, Parquet)   (Online + Offline)         |
|   - 1min aggregates     - Raman spectra                              |
|   - hourly summaries    - UV-Vis spectra                             |
|   - daily features      - EPR data                                   |
|                                                                      |
+=====================================================================+
            |                           |
            v                           v
+============================+  +==============================+
|   KNOWLEDGE GRAPH LAYER   |  |      AI/ML LAYER             |
+============================+  +==============================+
|                            |  |                              |
| [Morph-KGC]               |  | [Feature Engineering]        |
|   YARRRML mappings         |  |   Feast → Feature Matrix     |
|   CSV/JSON → RDF triples   |  |   (114 dimensions)           |
|         |                  |  |         |                    |
|         v                  |  |         v                    |
| [Ontotext GraphDB]        |  | [PyTorch TFT Model]          |
|   OWL 2 RL Reasoning      |  |   Multi-task heads:          |
|   SPARQL 1.1 Endpoint     |  |   - AD risk (30/90/180d)     |
|   SHACL Validation        |  |   - Asthma risk              |
|   Named Graphs per patient|  |   - Rhinitis risk            |
|         |                  |  |   - Immune Risk Score        |
|         v                  |  |         |                    |
| [SPARQL Queries]           |  | [SHAP Explainer]             |
|   Causal pathway lookup    |  |   Global + Local + Temporal  |
|   Trajectory patterns      |  |         |                    |
|   Cross-layer correlation  |  |         v                    |
|                            |  | [R-GCN (DGL)]                |
|         +<-----------------+--+   Link prediction            |
|         |  SHAP-Ontology   |  |   → New relation candidates  |
|         |  Bridge          |  |                              |
|         v                  |  | [Tigramite PCMCI+]           |
| [Ontology Update]          |  |   Causal structure discovery  |
|   Expert validation        |  |                              |
|   ROBOT merge              |  | [MLflow]                     |
|                            |  |   Experiment tracking        |
+============================+  |   Model registry             |
                                +==============================+
                                            |
                                            v
                                +========================+
                                |   APPLICATION LAYER    |
                                +========================+
                                |                        |
                                | [Grafana Dashboards]   |
                                |   - Real-time sensors  |
                                |   - Patient dashboard  |
                                |   - Alert management   |
                                |                        |
                                | [Clinical API]         |
                                |   - Risk scores        |
                                |   - Explanations       |
                                |   - Treatment recs     |
                                |                        |
                                | [Research Portal]      |
                                |   - SPARQL explorer    |
                                |   - Cohort analysis    |
                                |   - Model performance  |
                                +========================+
```

### 7.2 단일 환자 데이터 흐름 시퀀스

```
시간 ──────────────────────────────────────────────────────────→

환경센서    ■■■■■■■■■■■■■■■■■■■■■■■■■■■■  (연속 1초 간격)
            │ 10초 집계
            ▼
MQTT/Kafka  ●──●──●──●──●──●──●──●──●──●  (10초 메시지)
            │
Flink       ├─── 1분 윈도우 ───┤
            │   PM2.5=23.5     │
            │   VOC=142        │
            │   CO2=680        │
            │   OSL=0.62       │
            ▼
TimescaleDB [1min row: env_metrics + composite_indices]

웨어러블    ○─────○─────○─────○─────○─── (5분 HRV)
            │
Flink       ├─── 1분 리샘플 ──┤
            ▼
TimescaleDB [1min row: hrv, spo2, activity, skin_temp]

AirKorea    ◆───────────────────────────◆  (1시간)
            │
Airflow     ├── 시간 조인 ──→ TimescaleDB [hourly_external]
            ▼

=== 매일 02:00 배치 ===

Airflow     daily_aggregation:
            TimescaleDB 1min rows → daily_summary (mean, p95, trend...)
            + AirKorea/KMA daily stats
            + Feature engineering (lag features, cross features)
            → Feast Feature Store [114-dim feature vector]

=== 바이오마커 측정 시 (주 1회) ===

SERS/ELISA  ★ IL-6=4.2, CRP=2.8
            │
Airflow     biomarker_ingestion:
            + 역추적 윈도우: [-7d, 0d] 환경/라이프로그 통계 결합
            → Feast 업데이트
            → TimescaleDB [biomarker_observation]

=== 매일 03:00 온톨로지 생성 ===

Airflow     ontology_generation:
            daily_summary + biomarker → YARRRML → Morph-KGC
            → RDF Triples → GraphDB Bulk Load
            → SHACL Validation

=== 주 1회 모델 재학습 ===

Airflow     model_retrain:
            Feast offline → PyTorch TFT training
            → SHAP analysis → MLflow logging
            → R-GCN link prediction → expert review queue
```

---

## 8. 단계별 구현 로드맵

### Phase 1 (2026-04 ~ 2027-12): 기반 구축

| 분기 | 목표 | 상세 |
|------|------|------|
| Q2 2026 | 에지 프로토타입 | RPi + SPS30/SGP41/SCD41 연동, MQTT 전송, SQLite 버퍼 |
| Q3 2026 | 스트리밍 코어 | Kafka + Flink 설치, 1분 윈도우 정렬, OSL 실시간 계산 |
| Q3 2026 | 배치 코어 | Airflow DAG 3종 (daily_agg, external_sync, data_quality) |
| Q4 2026 | 저장 계층 | TimescaleDB 스키마 설계, MinIO 구축, Feast 피처 정의 |
| Q1 2027 | 온톨로지 파이프라인 | YARRRML 매핑, Morph-KGC, GraphDB 설치, SPARQL 쿼리 5종 |
| Q2 2027 | ML 베이스라인 | TFT 모델 v1 (동물실험 데이터), SHAP 통합, MLflow |
| Q3 2027 | 통합 테스트 | End-to-end 10명 시뮬레이션, 레이턴시 검증 (< 100ms) |
| Q4 2027 | GNN 프로토타입 | R-GCN link prediction v1, 전문가 검증 워크플로우 |

### Phase 2 (2028-01 ~ 2029-12): 고도화

- 웨어러블 + SERS 실시간 경로 추가
- 플라즈마 세션 ETL 완성
- TFT 모델 v2 (오가노이드 + 동물 + 인체 데이터)
- AUC >= 0.70 달성
- NHIS 코호트 데이터 통합
- GraphDB Enterprise 전환 (HA 클러스터)

### Phase 3 (2030-01 ~ 2033-12): 상용화

- Kubernetes 전환 (수백 명 동시 모니터링)
- 실시간 추론 서빙 (TorchServe + GPU 클러스터)
- AUC >= 0.85 달성
- HL7 FHIR 인터페이스로 병원 EMR 연동
- 국가 단위 플랫폼 확장

---

## 부록 A: 데이터 보안 및 개인정보보호

| 항목 | 전략 |
|------|------|
| 환자 식별자 | SHA-256 해시 기반 가명 ID (patient_id는 매핑 테이블로만 복원) |
| 전송 암호화 | MQTT TLS 1.3, HTTPS, Kafka SSL |
| 저장 암호화 | PostgreSQL TDE, MinIO SSE-S3 |
| 접근 제어 | Keycloak RBAC, 역할별 데이터 범위 제한 |
| 감사 로그 | 모든 데이터 접근 기록, 90일 보관 |
| IRB | NHIS/임상 데이터 연구윤리위원회 승인 필수 |
| 가명화 도구 | ARX (k-anonymity k>=5, l-diversity l>=3) |

## 부록 B: 모니터링 및 관측성

| 대상 | 메트릭 | 알림 임계값 |
|------|--------|-----------|
| 센서 게이트웨이 | heartbeat 간격, 메시지율 | heartbeat > 5분 |
| Kafka | consumer lag, 파티션 수 | lag > 1000 메시지 |
| Flink | checkpoint 지연, backpressure | backpressure > 50% |
| TimescaleDB | 쿼리 지연, 디스크 사용량 | 디스크 > 80% |
| GraphDB | SPARQL 응답 시간, 트리플 수 | 응답 > 5초 |
| ML 모델 | 추론 지연, 예측 분포 드리프트 | PSI > 0.2 |
| 에지 센서 | 교차 센서 일관성, 물리적 범위 | BME680 vs SCD41 온도 차 > 2도 |

---

*본 문서는 Project Columbus 1단계 데이터 파이프라인 설계 기초문서이며,
구현 진행에 따라 지속적으로 업데이트된다.*
