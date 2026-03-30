# 면역 궤적 예측 AI 모델 아키텍처
# Immune Trajectory Prediction AI Model Architecture

**문서 버전**: 1.0
**작성일**: 2026-03-30
**단계**: 1단계 (시드연구) 설계 문서
**상태**: Draft — Phase 1 architecture design

---

## 목차

1. [질병 궤적 예측 모델 (Disease Trajectory Prediction Model)](#1-질병-궤적-예측-모델)
2. [인과 추론 엔진 (Causal Inference Engine)](#2-인과-추론-엔진)
3. [GNN 기반 온톨로지 자동 생성 (Ontology Auto-generation via GNN)](#3-gnn-기반-온톨로지-자동-생성)
4. [성능 목표 및 평가 (Performance Targets & Evaluation)](#4-성능-목표-및-평가)

---

## 1. 질병 궤적 예측 모델

### 1.1 모델 개요

본 과제의 핵심 AI 모델은 **Multi-task Temporal Fusion Transformer (TFT)**로,
4계층(환경-라이프로그-바이오마커-치료) 시계열 데이터를 통합하여 7개 면역 질환의
발생 위험도를 다중 시간 수평선(1일, 1주, 1개월, 3개월)에서 동시 예측한다.

**모델 선택 근거:**
- TFT는 다변량 시계열에서 variable-wise attention으로 피처 기여도를 자체 해석 가능
- 불규칙 간격 데이터(바이오마커: 주/월 1회) 처리에 강점
- Multi-task 헤드로 알레르기 마치(Allergic March) 순차 진행을 동시 학습
- 온톨로지 인과 경로를 attention prior로 주입 가능한 구조

### 1.2 전체 아키텍처

```
                         ┌─────────────────────────┐
                         │   Static Covariates      │
                         │ (age, sex, BMI, genetics)│
                         └───────────┬─────────────┘
                                     │
                                     v
┌──────────────────────────────────────────────────────────────────┐
│                    INPUT PROCESSING (114D)                        │
│                                                                  │
│  Layer 1: Environment (30D)  ──→ [VSN_env]  ──→ selected_env    │
│  Layer 2: Lifelog     (20D)  ──→ [VSN_life] ──→ selected_life   │
│  Layer 3: Biomarker   (15D)  ──→ [VSN_bio]  ──→ selected_bio   │
│  Layer 4: Treatment   (6D)   ──→ [VSN_tx]   ──→ selected_tx    │
│  Cross-features       (10D)  ──→ [VSN_cross]──→ selected_cross  │
│  External env         (10D)  ──→ [VSN_ext]  ──→ selected_ext   │
│  Composite indices    (15D)  ──→ [VSN_comp] ──→ selected_comp  │
│  Demographics         (8D)   ──→ [Static Covariate Encoder]     │
│                                                                  │
│  Total: 114 time-varying + 8 static = 122 input dimensions      │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────────────┐
│                    TEMPORAL ENCODER                               │
│                                                                  │
│  [Concatenated selected features]                                │
│           │                                                      │
│           v                                                      │
│  [Bidirectional LSTM Encoder]  ← lookback window: 90 days       │
│           │                                                      │
│           v                                                      │
│  [Gated Residual Network (GRN)]                                  │
│           │                                                      │
│           v                                                      │
│  [Layer Normalization]                                           │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────────────┐
│              INTERPRETABLE MULTI-HEAD ATTENTION                  │
│                                                                  │
│  Ontology-Informed Attention Prior:                              │
│    - CausalPathway instances → attention bias matrix             │
│    - PM2.5→IL-6 (r=0.52, lag=12h) → bias on (pm25, il6) pair   │
│    - VOCs→IgE (r=0.35, lag=weeks) → bias on (voc, ige) pair    │
│    - HRV↔IL-6 (r=-0.42) → bias on (hrv, il6) pair             │
│                                                                  │
│  Multi-head attention (h=4 heads)                                │
│    - Head 1: Environment → Biomarker pathways                   │
│    - Head 2: Lifelog → Biomarker pathways                       │
│    - Head 3: Treatment → Biomarker pathways                     │
│    - Head 4: Free attention (data-driven)                       │
│                                                                  │
│  Attention output + GRN + Skip connection                       │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────────────┐
│              MULTI-HORIZON DECODER                               │
│                                                                  │
│  [Temporal Attention Decoder]                                    │
│           │                                                      │
│    ┌──────┼──────┬──────┐                                       │
│    v      v      v      v                                       │
│  [1day] [1wk] [1mo]  [3mo]   ← prediction horizons             │
│                                                                  │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        v
┌──────────────────────────────────────────────────────────────────┐
│              MULTI-TASK DISEASE HEADS                             │
│                                                                  │
│  For each horizon, 7 disease risk scores (sigmoid output):      │
│                                                                  │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐                  │
│  │  AD    │ │ Asthma │ │ Rhinitis │ │Psoriasis│                 │
│  │ (L20)  │ │ (J45)  │ │  (J30)   │ │ (L40)  │                 │
│  └────────┘ └────────┘ └──────────┘ └────────┘                  │
│  ┌────────┐ ┌────────┐ ┌──────────┐                              │
│  │Dry Eye │ │  RA    │ │ Alopecia │                              │
│  │(H04.1) │ │        │ │          │                              │
│  └────────┘ └────────┘ └──────────┘                              │
│                                                                  │
│  Output shape: [batch, 4 horizons, 7 diseases]                  │
│  + Immune Risk Score (0-100, regression head)                   │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 입력 피처 사양 (114 Dimensions)

#### Layer 1: 환경 모니터링 (30D)

| # | 피처명 | 설명 | 시간 해상도 | 단위 |
|---|--------|------|-----------|------|
| 1 | `pm25_mean_7d` | PM2.5 7일 평균 | 일별 | ug/m3 |
| 2 | `pm25_p95_7d` | PM2.5 7일 95 백분위 | 일별 | ug/m3 |
| 3 | `pm25_max_7d` | PM2.5 7일 최대 | 일별 | ug/m3 |
| 4 | `pm25_trend_7d` | PM2.5 7일 추세 기울기 | 일별 | ug/m3/day |
| 5 | `pm10_mean_7d` | PM10 7일 평균 | 일별 | ug/m3 |
| 6 | `pm10_max_7d` | PM10 7일 최대 | 일별 | ug/m3 |
| 7 | `voc_index_mean_7d` | VOC Index 7일 평균 | 일별 | index |
| 8 | `voc_index_max_7d` | VOC Index 7일 최대 | 일별 | index |
| 9 | `voc_trend_7d` | VOC 7일 추세 기울기 | 일별 | index/day |
| 10 | `co2_mean_7d` | CO2 7일 평균 | 일별 | ppm |
| 11 | `co2_max_7d` | CO2 7일 최대 | 일별 | ppm |
| 12 | `temp_indoor_mean_7d` | 실내 온도 7일 평균 | 일별 | C |
| 13 | `temp_indoor_std_7d` | 실내 온도 7일 표준편차 | 일별 | C |
| 14 | `humidity_indoor_mean_7d` | 실내 습도 7일 평균 | 일별 | %RH |
| 15 | `humidity_indoor_max_7d` | 실내 습도 7일 최대 | 일별 | %RH |
| 16 | `pressure_mean_7d` | 기압 7일 평균 | 일별 | hPa |
| 17 | `btex_mean_7d` | BTEX 농도 7일 평균 | 일별 | ug/m3 |
| 18 | `btex_max_7d` | BTEX 농도 7일 최대 | 일별 | ug/m3 |
| 19 | `pfas_mean_7d` | PFAS 농도 7일 평균 | 일별 | ng/m3 |
| 20 | `hcho_mean_7d` | HCHO 농도 7일 평균 | 일별 | ug/m3 |
| 21 | `pm25_lag_24h` | PM2.5 24시간 지연 값 | 일별 | ug/m3 |
| 22 | `voc_lag_48h` | VOC 48시간 지연 값 | 일별 | index |
| 23 | `pm25_auc_7d` | PM2.5 7일 곡선하면적 | 일별 | ug*h/m3 |
| 24 | `humidity_above65_hours_7d` | 습도 65% 초과 누적시간 | 일별 | hours |
| 25 | `co2_above1000_hours_7d` | CO2 1000ppm 초과 누적시간 | 일별 | hours |
| 26-30 | `env_reserved_1~5` | 추후 확장 (라돈, O3 실내 등) | 일별 | - |

#### Layer 2: 복합지표 (15D)

| # | 피처명 | 설명 | 시간 해상도 |
|---|--------|------|-----------|
| 31 | `osl_mean_7d` | 산화스트레스 부하 7일 평균 | 일별 |
| 32 | `osl_max_7d` | 산화스트레스 부하 7일 최대 | 일별 |
| 33 | `osl_auc_7d` | OSL 7일 곡선하면적 | 일별 |
| 34 | `osl_trend_7d` | OSL 7일 추세 | 일별 |
| 35 | `osl_above07_hours_7d` | OSL > 0.7 누적시간 | 일별 |
| 36 | `aes_mean_7d` | 알레르겐 노출점수 7일 평균 | 일별 |
| 37 | `aes_max_7d` | 알레르겐 노출점수 7일 최대 | 일별 |
| 38 | `aes_trend_7d` | AES 7일 추세 | 일별 |
| 39 | `vi_mean_7d` | 환기지수 7일 평균 | 일별 |
| 40 | `vi_min_7d` | 환기지수 7일 최소 | 일별 |
| 41-45 | `composite_reserved_1~5` | 추후 확장 | 일별 |

#### Layer 3: 라이프로그 / 생체신호 (20D)

| # | 피처명 | 설명 | 시간 해상도 |
|---|--------|------|-----------|
| 46 | `hrv_rmssd_mean_7d` | HRV RMSSD 7일 평균 | 일별 |
| 47 | `hrv_rmssd_min_7d` | HRV RMSSD 7일 최소 | 일별 |
| 48 | `hrv_rmssd_trend_7d` | HRV RMSSD 7일 추세 | 일별 |
| 49 | `hrv_sdnn_mean_7d` | HRV SDNN 7일 평균 | 일별 |
| 50 | `spo2_mean_7d` | SpO2 7일 평균 | 일별 |
| 51 | `spo2_min_7d` | SpO2 7일 최소 | 일별 |
| 52 | `sleep_deep_ratio_7d` | 깊은 수면 비율 7일 평균 | 일별 |
| 53 | `sleep_rem_ratio_7d` | REM 수면 비율 7일 평균 | 일별 |
| 54 | `sleep_duration_mean_7d` | 수면 시간 7일 평균 | 일별 |
| 55 | `sleep_quality_score_7d` | 수면 품질 점수 7일 평균 | 일별 |
| 56 | `steps_mean_7d` | 일일 걸음수 7일 평균 | 일별 |
| 57 | `steps_trend_7d` | 걸음수 7일 추세 | 일별 |
| 58 | `mets_mean_7d` | METs 7일 평균 | 일별 |
| 59 | `skin_temp_mean_7d` | 피부온도 7일 평균 | 일별 |
| 60 | `skin_temp_circadian_amp` | 피부온도 일주기 진폭 | 일별 |
| 61 | `wearable_adherence_7d` | 웨어러블 착용률 7일 | 일별 |
| 62-65 | `lifelog_reserved_1~4` | 추후 확장 (SERS 연속 모니터링) | 일별 |

#### Layer 4: 바이오마커 (15D)

| # | 피처명 | 설명 | 시간 해상도 |
|---|--------|------|-----------|
| 66 | `il6_latest` | IL-6 최근 측정값 | 측정 시점 |
| 67 | `il6_trend` | IL-6 추세 (최근 3회) | 측정 시점 |
| 68 | `tnf_alpha_latest` | TNF-alpha 최근 측정값 | 측정 시점 |
| 69 | `il4_latest` | IL-4 최근 측정값 | 측정 시점 |
| 70 | `il10_latest` | IL-10 최근 측정값 | 측정 시점 |
| 71 | `il13_latest` | IL-13 최근 측정값 | 측정 시점 |
| 72 | `ige_latest` | IgE 최근 측정값 | 측정 시점 |
| 73 | `ige_trend` | IgE 추세 (최근 3회) | 측정 시점 |
| 74 | `crp_latest` | CRP 최근 측정값 | 측정 시점 |
| 75 | `crp_trend` | CRP 추세 (최근 3회) | 측정 시점 |
| 76 | `il5_latest` | IL-5 최근 측정값 | 측정 시점 |
| 77 | `il17_latest` | IL-17 최근 측정값 | 측정 시점 |
| 78 | `ohdg_latest` | 8-OHdG 최근 측정값 | 측정 시점 |
| 79 | `mda_latest` | MDA 최근 측정값 | 측정 시점 |
| 80 | `th1_th2_ratio` | Th1/Th2 균형 비율 | 측정 시점 |

#### Layer 5: 플라즈마 치료 (6D)

| # | 피처명 | 설명 | 시간 해상도 |
|---|--------|------|-----------|
| 81 | `last_treatment_days_ago` | 마지막 치료 경과일 | 세션별 |
| 82 | `cumulative_rons_dose` | 누적 RONS 투여량 | 세션별 |
| 83 | `treatment_frequency_30d` | 30일 내 치료 횟수 | 세션별 |
| 84 | `avg_rons_selectivity` | 평균 RONS 선택성 프로파일 | 세션별 |
| 85 | `treatment_duration_avg` | 평균 치료 시간 | 세션별 |
| 86 | `plasma_voltage_avg` | 평균 인가 전압 | 세션별 |

#### Layer 6: 외부 환경 (10D)

| # | 피처명 | 설명 | 시간 해상도 |
|---|--------|------|-----------|
| 87 | `airkorea_pm25_mean_7d` | 외부 PM2.5 7일 평균 | 시간 |
| 88 | `airkorea_o3_mean_7d` | 외부 오존 7일 평균 | 시간 |
| 89 | `airkorea_no2_mean_7d` | 외부 NO2 7일 평균 | 시간 |
| 90 | `kma_temp_mean_7d` | 외부 기온 7일 평균 | 시간 |
| 91 | `kma_humidity_mean_7d` | 외부 습도 7일 평균 | 시간 |
| 92 | `kma_pressure_mean_7d` | 외부 기압 7일 평균 | 시간 |
| 93 | `kma_uv_index_max_7d` | 자외선지수 7일 최대 | 시간 |
| 94 | `season_encoding_sin` | 계절 사인 인코딩 | 일별 |
| 95 | `season_encoding_cos` | 계절 코사인 인코딩 | 일별 |
| 96 | `day_of_week_encoding` | 요일 인코딩 | 일별 |

#### Layer 7: 인구통계 및 정적 변수 (8D, Static)

| # | 피처명 | 설명 | 유형 |
|---|--------|------|------|
| 97 | `age` | 연령 | continuous |
| 98 | `sex` | 성별 | categorical |
| 99 | `bmi` | 체질량지수 | continuous |
| 100 | `smoking_status` | 흡연 상태 | categorical |
| 101 | `allergy_family_hx` | 알레르기 가족력 | binary |
| 102 | `atopy_score` | 아토피 점수 | continuous |
| 103 | `genetic_risk_score` | 유전자 위험 점수 (2단계~) | continuous |
| 104 | `comorbidity_count` | 동반질환 수 | integer |

#### Layer 8: 교차 피처 (10D)

| # | 피처명 | 설명 |
|---|--------|------|
| 105 | `osl_x_hrv_ratio` | OSL * (1/HRV) 면역 취약 지수 |
| 106 | `pm25_lag12h_x_il6` | PM2.5(12h lag) * IL-6 상호작용 |
| 107 | `sleep_x_tnf_alpha` | 수면품질 * TNF-alpha 상호작용 |
| 108 | `aes_x_ige` | 알레르겐노출 * IgE 상호작용 |
| 109 | `osl_x_crp` | 산화스트레스 * CRP 상호작용 |
| 110 | `vi_x_il6` | 환기지수 * IL-6 상호작용 |
| 111 | `steps_x_tnf_alpha` | 활동량 * TNF-alpha 상호작용 |
| 112 | `skin_temp_amp_x_il17` | 피부온도진폭 * IL-17 상호작용 |
| 113 | `treatment_x_il10` | 치료 * IL-10 상호작용 |
| 114 | `humidity_x_ige` | 습도 * IgE 상호작용 |

### 1.4 모델 구성 요소 상세

#### A. Variable Selection Network (VSN)

각 데이터 계층별로 독립적인 VSN을 배치하여 피처 중요도를 학습한다.

```
Input (layer_dim) → Linear(layer_dim, layer_dim) → ELU
                  → Linear(layer_dim, layer_dim) → Softmax  → attention weights
                  → element-wise multiply with input         → selected features
```

**핵심 설계:**
- 각 계층의 VSN은 독립적으로 피처 중요도를 학습
- Static covariates는 context vector로 모든 VSN에 주입 (환자 특성에 따라 피처 중요도 달라짐)
- Softmax 출력은 해석 가능: "환자 P001에게 PM2.5가 가장 중요한 환경 요인"
- GRN(Gated Residual Network) 내부에 ELU + Dropout으로 비선형성 + 과적합 방지

#### B. Temporal Encoder (LSTM + GRN)

```
selected_features (T=90, D_selected)
        │
        v
[Bidirectional LSTM]  ← hidden_size=128, num_layers=2, dropout=0.1
        │
        v
[GRN (Gated Residual Network)]
        │
        v
[LayerNorm]
        │
        v
encoded_sequence (T=90, D_hidden=256)
```

**Lookback window**: 90일 (3개월)
- 환경 노출의 장기 누적 효과와 단기 급성 효과를 모두 포착
- 바이오마커(월 1회)가 최소 3회 포함되도록 보장
- 결측 시점은 마스킹 처리 (LSTM은 가변 길이 처리 가능)

#### C. Ontology-Informed Attention Prior

온톨로지 CausalPathway 인스턴스를 attention bias matrix로 변환하여
모델이 의학적으로 알려진 인과 관계에 집중하도록 유도한다.

**SPARQL 쿼리로 인과 경로 추출:**

```sparql
PREFIX ico: <http://purl.org/ico/>
SELECT ?upstream ?downstream ?correlation ?lag
WHERE {
  ?pathway a ico:trajectory/CausalPathway ;
           ico:trajectory/has_upstream_factor ?upstream ;
           ico:trajectory/has_downstream_effect ?downstream ;
           ico:trajectory/has_correlation_coefficient ?correlation ;
           ico:trajectory/has_temporal_lag ?lag .
}
```

**Attention bias 생성:**

```
1. CausalPathway 인스턴스에서 (upstream_feature, downstream_feature, correlation) 추출
2. 114x114 attention bias matrix B 초기화 (zeros)
3. 각 경로에 대해: B[upstream_idx, downstream_idx] = correlation * scale_factor
4. Attention 계산: Attention(Q,K,V) = softmax(QK^T / sqrt(d) + B) * V
```

**Prior의 역할:**
- 학습 초기에 온톨로지 지식이 attention을 유도 (cold-start 완화)
- 학습이 진행됨에 따라 데이터 기반 attention이 점차 지배
- Prior 강도는 temperature parameter tau로 조절: `B * (1/tau)`
  - tau가 클수록 prior 영향 감소 (데이터 의존)
  - 1단계 (데이터 적음): tau=1.0 (strong prior)
  - 3단계 (대규모 데이터): tau=5.0 (weak prior)

#### D. Multi-horizon Decoder

```
encoded_sequence
        │
        v
[Temporal Attention Decoder]
        │
        ├──→ horizon_1d:  Dense → risk_1day  (7 diseases)
        ├──→ horizon_1w:  Dense → risk_1week (7 diseases)
        ├──→ horizon_1m:  Dense → risk_1month(7 diseases)
        └──→ horizon_3m:  Dense → risk_3month(7 diseases)
```

각 horizon은 독립적인 dense head를 가지며 sigmoid 활성화로 0-1 위험 확률 출력.

#### E. Multi-task Disease Heads

7개 질환 동시 예측 (multi-label classification):

| 질환 | ICD-10 | 주요 관련 경로 | 핵심 피처 |
|------|--------|-------------|---------|
| 아토피 피부염 | L20 | Th2 사이토카인 | IL-4, IL-13, IgE, 습도, 알레르겐 |
| 천식 | J45 | 기도 염증 | IL-5, IgE, SpO2, PM2.5, OSL |
| 알레르기 비염 | J30 | 비강 과민 | IgE, IL-4, 알레르겐 노출, 계절 |
| 건선 | L40 | Th17/TNF-alpha | IL-17, TNF-alpha, 피부온도, 스트레스 |
| 안구건조증 | H04.1 | 안구 표면 염증 | IL-6, TNF-alpha, 습도, 환기 |
| 류마티스 관절염 | - | 전신 자가면역 | CRP, IL-6, TNF-alpha, 8-OHdG |
| 탈모 | - | 면역 매개 탈모 | IL-17, TNF-alpha, 스트레스, 수면 |

**Task 간 관계 학습:**
- Hard parameter sharing: Encoder/Attention은 공유
- Soft parameter sharing: Disease head 간 attention 정보 교환
- 알레르기 마치 순서 제약: AD→Asthma→Rhinitis 진행 패턴 정규화

### 1.5 손실 함수

```
L_total = L_disease + lambda_1 * L_trajectory + lambda_2 * L_ontology

여기서:
  L_disease     = sum_d sum_h [ w_d * BCE(y_d_h, yhat_d_h) ]
                  weighted binary cross-entropy, 질환별 유병률로 가중치 조정

  L_trajectory  = sum_t [ max(0, risk_downstream(t) - risk_upstream(t-lag)) ]
                  알레르기 마치 순서 일관성 정규화
                  (하류 질환 위험도가 상류 질환보다 먼저 높아지면 벌칙)

  L_ontology    = KL( attention_weights || ontology_prior )
                  attention 분포가 온톨로지 인과 경로와 일치하도록 유도

  lambda_1 = 0.1 (trajectory consistency weight)
  lambda_2 = 0.05 (ontology alignment weight, tau에 따라 조정)
```

**질환별 가중치 (w_d, 유병률 역수 기반):**
- 아토피 피부염: 1.0 (가장 빈번)
- 천식: 1.2
- 알레르기 비염: 1.1
- 건선: 2.0
- 안구건조증: 1.5
- 류마티스 관절염: 3.0 (가장 희귀)
- 탈모: 2.5

### 1.6 모델 사양

| 항목 | 값 |
|------|------|
| 파라미터 수 (추정) | ~2.5M |
| 입력 차원 | 114 time-varying + 8 static |
| Lookback window | 90 days |
| Prediction horizons | 4 (1d, 1w, 1m, 3m) |
| LSTM hidden size | 128 |
| LSTM layers | 2 (bidirectional) |
| Attention heads | 4 |
| Attention d_model | 256 |
| GRN hidden size | 128 |
| Dropout | 0.1 (encoder), 0.3 (heads) |
| Batch size | 64 |
| Learning rate | 1e-3 (AdamW, cosine annealing) |
| Weight decay | 1e-4 |
| 학습 에폭 | 100 (early stopping patience=10) |

**학습 데이터 요구량 (추정):**

| 단계 | 데이터 규모 | 출처 |
|------|-----------|------|
| 1단계 | 합성 데이터 1,000명 + 동물 실험 50개체 | 시뮬레이션 + 소규모 동물 |
| 2단계 | 3D 오가노이드 200 + 동물 200개체 + 예비 인간 100명 | PoC 데이터 |
| 3단계 | 임상 코호트 1,000명 이상 (2년 종단 데이터) | NHIS + 전향적 코호트 |

---

## 2. 인과 추론 엔진

### 2.1 PCMCI+ (Tigramite) 기반 시계열 인과 발견

**목적**: 4계층 다변량 시계열에서 통계적 인과 관계를 자동으로 발견하고,
온톨로지 CausalPathway 인스턴스를 데이터 기반으로 갱신한다.

**PCMCI+ 알고리즘 개요:**

```
[다변량 시계열 (114D x T)] → [PCMCI+] → [조건부 독립성 기반 인과 그래프]

1단계: PC-stable 알고리즘으로 후보 인과 관계 탐색 (skeleton discovery)
2단계: MCI (Momentary Conditional Independence) 테스트로 가짜 상관 제거
3단계: 시간 지연(lag) 반영한 인과 방향 결정
```

**구현 계획:**

```python
import tigramite
from tigramite.pcmci import PCMCI
from tigramite.independence_tests.parcorr import ParCorr

# 시계열 데이터 구성 (환자별)
dataframe = tigramite.data_processing.DataFrame(
    data=patient_multivariate_timeseries,  # (T, 114) numpy array
    var_names=feature_names
)

# PCMCI+ 실행
pcmci = PCMCI(dataframe=dataframe, cond_ind_test=ParCorr())
results = pcmci.run_pcmciplus(
    tau_min=0,           # 최소 시간 지연
    tau_max=30,          # 최대 30일 지연
    pc_alpha=0.05        # 유의수준
)

# 결과: 인과 그래프 (adjacency matrix + p-values + lag information)
```

**SPARQL 기반 인과 추론과의 연결:**

PCMCI+가 발견한 인과 관계를 온톨로지 CausalPathway와 대조한다.

```
                 ┌─────────────────┐
                 │  PCMCI+ 결과    │
                 │  (통계적 인과)  │
                 └────────┬────────┘
                          │
                          v
              ┌───────────────────────┐
              │   대조 (Reconcile)     │
              │                       │
              │  PCMCI+ 발견 ∩ 온톨로지 존재  → 강화 (confidence 업데이트)
              │  PCMCI+ 발견 ∩ 온톨로지 없음  → 신규 후보 (전문가 검증 대기)
              │  PCMCI+ 미발견 ∩ 온톨로지 존재 → 약화 (evidence_level 하향)
              └───────────────────────┘
                          │
                          v
              ┌───────────────────────┐
              │  SPARQL Update        │
              │  온톨로지 CausalPathway│
              │  인스턴스 갱신         │
              └───────────────────────┘
```

**SPARQL Update 예시:**

```sparql
# 신규 인과 관계 발견 시 CausalPathway 인스턴스 추가
PREFIX ico: <http://purl.org/ico/>
INSERT DATA {
  ico:causal_skin_temp_psoriasis a ico:trajectory/CausalPathway ;
    ico:trajectory/has_upstream_factor ico:feature/skin_temp_circadian_amp ;
    ico:trajectory/has_downstream_effect ico:disease/psoriasis ;
    ico:trajectory/has_correlation_coefficient "0.38"^^xsd:float ;
    ico:trajectory/has_temporal_lag "P7D"^^xsd:duration ;
    ico:trajectory/has_evidence_level "data_driven" ;
    ico:trajectory/has_pcmci_pvalue "0.003"^^xsd:float ;
    ico:trajectory/discovered_by "PCMCI+" ;
    ico:trajectory/discovery_date "2027-06-15"^^xsd:date .
}
```

### 2.2 SHAP 통합

SHAP (SHapley Additive exPlanations)을 3개 수준에서 적용한다.

#### A. Global SHAP: 코호트 수준 피처 중요도

```
[Trained TFT Model] + [전체 검증 데이터셋]
        │
        v
[SHAP DeepExplainer]  (PyTorch 모델 → DeepSHAP)
        │
        v
[mean(|SHAP values|) per feature]  → 피처 중요도 순위
        │
        v
[온톨로지 검증]
  - SHAP 상위 10 피처와 CausalPathway 매칭
  - 매칭률이 50% 미만이면 온톨로지 검토 필요 경고
```

**산출물:**
- 질환별 Global Feature Importance 차트
- 온톨로지 CausalPathway와의 일치도 보고서
- 신규 인과 관계 후보 목록

#### B. Local SHAP: 개인별 예측 설명

```
[환자 P001의 예측]  risk_asthma_1month = 0.72
        │
        v
[SHAP values per feature]
  osl_mean_7d:      +0.15  (산화스트레스 높음)
  hrv_rmssd_mean_7d: +0.11  (자율신경 저하)
  il6_latest:        +0.09  (IL-6 상승)
  pm25_mean_7d:      +0.07  (PM2.5 노출)
  sleep_deep_ratio:  +0.05  (깊은 수면 부족)
  ...
        │
        v
[SHAP-to-Ontology Bridge]
  각 SHAP 기여 피처 → SPARQL로 CausalPathway 조회
        │
        v
[자연어 설명 생성]
  "지난 7일간 산화스트레스 부하가 높았으며(OSL 0.68),
   이는 PM2.5→ROS→NF-kB→IL-6 경로를 통해 기도 염증을
   유발할 수 있습니다 (r=0.52). HRV 저하(RMSSD 28ms)도
   미주신경 항염증 반사 약화를 시사합니다."
```

#### C. Temporal SHAP: 시점별 기여도 변화

```
[90일 lookback window 내 각 시점의 SHAP values]
        │
        v
[시점별 피처 기여도 히트맵]
  - X축: 시간 (Day -90 ~ Day 0)
  - Y축: 피처 (114개)
  - 색상: SHAP 값 (양: 위험 증가, 음: 위험 감소)
        │
        v
[시간 패턴 분석]
  - "Day -14 ~ Day -7: PM2.5 급상승 기간, SHAP 기여도 급증"
  - "Day -3: IL-6 측정값 이상치, 위험도 급상승 트리거"
```

**구현 기술:**

| 컴포넌트 | 기술 | 비고 |
|---------|------|------|
| Global/Local SHAP | `shap.DeepExplainer` | PyTorch 모델 직접 지원 |
| Temporal SHAP | `captum.attr.IntegratedGradients` | 시계열 특화, 시점별 기여도 |
| SHAP 시각화 | `shap.summary_plot`, `shap.waterfall_plot` | 내장 시각화 |
| SHAP→Ontology | Custom SPARQL bridge | SHAP 상위 피처 → CausalPathway 매핑 |

### 2.3 SHAP-to-Ontology Bridge

SHAP 어트리뷰션을 온톨로지 CausalPathway 인스턴스와 연결하는 핵심 모듈이다.

**매핑 프로세스:**

```
1. SHAP 상위 K개 피처 추출 (예: K=10)
2. 각 피처에 대해 SPARQL 쿼리 실행:
   SELECT ?pathway ?mechanism ?correlation
   WHERE {
     ?pathway a ico:trajectory/CausalPathway ;
              ico:trajectory/has_upstream_factor ?factor .
     ?factor ico:feature_name "{feature_name}" .
     ?pathway ico:trajectory/has_mechanism ?mechanism ;
              ico:trajectory/has_correlation_coefficient ?correlation .
   }
3. SHAP 기여도 + 온톨로지 메커니즘 → 통합 설명 생성

결과 예시:
{
  "feature": "pm25_mean_7d",
  "shap_value": +0.07,
  "shap_rank": 4,
  "ontology_pathways": [
    {
      "pathway_uri": "ico:causal_pm25_il6",
      "mechanism": "PM2.5 → ROS → NF-kB → IL-6",
      "correlation": 0.52,
      "temporal_lag": "PT12H",
      "evidence_level": "literature"
    }
  ],
  "explanation": "PM2.5 노출이 ROS 생성을 통해 NF-kB 신호전달을 활성화하고,
                  이는 6-24시간 후 IL-6 상승으로 이어질 수 있습니다."
}
```

---

## 3. GNN 기반 온톨로지 자동 생성

### 3.1 R-GCN (Relational Graph Convolutional Network)

**목적**: 기존 온톨로지 지식 그래프에서 누락된 관계(링크)를 예측하고,
새로운 인과 경로를 자동으로 제안한다.

**아키텍처:**

```
┌──────────────────────────────────────────────────────┐
│                 R-GCN Architecture                    │
│                                                      │
│  [Knowledge Graph]                                   │
│    Nodes: 환경요인, 바이오마커, 질환, RONS, 경로, ...  │
│    Edges: causes, correlates_with, treats, ...       │
│    Relations: ~15 relation types                     │
│                                                      │
│         ↓                                            │
│  [R-GCN Encoder]                                     │
│    Layer 1: R-GCN(in=feat_dim, out=256, num_rels=15)│
│    Layer 2: R-GCN(in=256, out=128, num_rels=15)     │
│    Basis decomposition (B=5) for parameter sharing   │
│         ↓                                            │
│  [Node Embeddings] (N x 128)                         │
│         ↓                                            │
│  ┌──────────┬──────────────────┐                     │
│  │          │                  │                     │
│  v          v                  v                     │
│ [Link      [Node             [Triple                │
│  Predict]   Classify]         Score]                 │
│                                                      │
│  DistMult   Softmax           TransE                 │
│  Decoder    Classifier        Scoring                │
└──────────────────────────────────────────────────────┘
```

### 3.2 Link Prediction: 신규 인과 경로 발견

**목적**: 온톨로지에 존재하지 않는 잠재적 인과 관계를 발견한다.

**방법:**
1. 기존 온톨로지 트리플을 학습 데이터로 사용
2. R-GCN으로 노드 임베딩 학습
3. DistMult 디코더로 모든 가능한 (head, relation, tail) 조합 점수 계산
4. 존재하지 않는 트리플 중 높은 점수를 신규 후보로 추출

**DistMult 점수 함수:**

```
score(h, r, t) = h^T * diag(R_r) * t

여기서:
  h: head entity embedding (128D)
  R_r: relation-specific diagonal matrix (128D)
  t: tail entity embedding (128D)
```

**예상 발견 유형:**

| 발견 유형 | 예시 | 기대 효과 |
|----------|------|---------|
| 새로운 RONS-경로 연관 | "N2O3 → Th17 활성화" | 플라즈마 치료 프로토콜 최적화 |
| 환경-질환 신규 경로 | "실내 PFAS → 면역 억제 → 감염 감수성" | 환경 관리 가이드라인 확장 |
| 바이오마커 간 숨은 상관 | "8-OHdG ↔ 피부온도 일주기" | 비침습 바이오마커 프록시 |
| 치료 효과 경로 | "RONS 선택성 → 특정 사이토카인 억제" | 맞춤형 치료 파라미터 |

### 3.3 Node Classification: 새로운 엔티티 분류

새로 발견된 바이오마커나 환경 요인을 기존 온톨로지 분류체계에 자동 배치한다.

```
[새로운 엔티티 (예: 신규 사이토카인)]
        │
        v
[R-GCN 임베딩 계산]  ← 이웃 노드 정보 집계
        │
        v
[Softmax 분류기]
        │
  ┌─────┼──────┬──────────┐
  v     v      v          v
 ROS   RNS   Cytokine   Allergen  ← 온톨로지 클래스
(prob) (prob) (prob)     (prob)
```

### 3.4 Human-in-the-Loop 검증 워크플로우

자동 발견된 관계는 반드시 전문가 검증을 거쳐 온톨로지에 반영된다.

```
┌─────────────────────────────────────────────────────────────┐
│                 Human-in-the-Loop Workflow                    │
│                                                             │
│  Step 1: 자동 발견                                          │
│    R-GCN Link Prediction + PCMCI+ Causal Discovery          │
│    → 신규 관계 후보 목록 생성 (score > threshold)            │
│                                                             │
│  Step 2: 자동 사전 검증                                      │
│    - 문헌 검색 (PubMed API): 유사 관계 선행 연구 존재 여부   │
│    - 통계적 유의성: PCMCI+ p-value < 0.01                   │
│    - 예측 점수: R-GCN score > 0.7                           │
│    - 기존 온톨로지와의 논리적 일관성 (OWL 추론기 검증)      │
│                                                             │
│  Step 3: 전문가 검증 대시보드                                │
│    - 후보 관계 목록 + 근거 자료 표시                         │
│    - 전문가 판정: Accept / Reject / Modify / Defer           │
│    - 판정 이력 기록 (감사 추적)                              │
│                                                             │
│  Step 4: 온톨로지 업데이트                                   │
│    - Accept → ROBOT CLI로 OWL 파일에 추가                   │
│    - HermiT 추론기로 일관성 검증                             │
│    - Git commit + 버전 태깅                                  │
│                                                             │
│  Step 5: 모델 재학습 트리거                                   │
│    - 온톨로지 업데이트 → Attention prior matrix 갱신         │
│    - 다음 model_retrain DAG에서 반영                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 학습 데이터

| 데이터 소스 | 트리플 수 (추정) | 유형 |
|-----------|---------------|------|
| ICO 온톨로지 TBox | ~500 | 클래스/관계 정의 |
| ICO 온톨로지 ABox (Phase 1) | ~10,000 | 측정 인스턴스 |
| Disease Ontology (DO) | ~12,000 | 질환 분류 |
| Gene Ontology (GO, 면역 서브셋) | ~5,000 | 면역 경로 |
| ChEBI (RONS 서브셋) | ~1,000 | 화학종 |
| 문헌 마이닝 (PubMed) | ~20,000 (2단계~) | 추출 관계 |
| PCMCI+ 발견 관계 | ~100-500 (점진적) | 데이터 기반 |

**문헌 마이닝 파이프라인 (2단계 이후):**

```
[PubMed 논문] → [BioBERT NER] → (entity1, relation, entity2) 추출
             → [관계 정규화] → 온톨로지 용어 매핑
             → [R-GCN 학습 데이터에 추가]
```

---

## 4. 성능 목표 및 평가

### 4.1 단계별 성능 목표

| 지표 | 1단계 (2026-2027) | 2단계 (2028-2029) | 3단계 (2030-2033) |
|------|------------------|------------------|------------------|
| **질병 예측 AUC-ROC** | >= 0.75 (baseline) | >= 0.70 | >= 0.85 |
| **데이터 출처** | 합성 + 소규모 동물 | 센서 + 3D 오가노이드 + 동물 | 임상 코호트 (1000명+) |
| **모델 상태** | 아키텍처 검증 | 실데이터 학습 | 임상 검증 완료 |

**1단계 AUC 0.75가 2단계 AUC 0.70보다 높은 이유:**
- 1단계는 합성/시뮬레이션 데이터로 인한 과적합 가능성 (낙관적 추정)
- 2단계는 실제 센서 데이터의 노이즈와 결측이 반영된 현실적 성능
- 2단계 AUC 0.70은 실데이터 기반 검증된(validated) 성능

### 4.2 평가 메트릭

#### A. 질병 예측 성능

| 메트릭 | 설명 | 1단계 목표 | 3단계 목표 |
|--------|------|----------|----------|
| AUC-ROC | 분류 판별력 (class-imbalanced에 강건) | >= 0.75 | >= 0.85 |
| AUC-PR | 양성 예측 정밀도-재현율 (희귀 질환에 적합) | >= 0.40 | >= 0.65 |
| Brier Score | 확률 교정도 (낮을수록 좋음) | <= 0.25 | <= 0.15 |
| Sensitivity | 민감도 (질환 감지 능력) | >= 0.70 | >= 0.85 |
| Specificity | 특이도 (오경보 최소화) | >= 0.65 | >= 0.80 |
| F1 (macro) | 질환별 균형 성능 | >= 0.50 | >= 0.70 |

#### B. 사이토카인 프로파일 유사도

플라즈마 치료 후 사이토카인 변화 패턴 예측의 정확도를 측정한다.

| 메트릭 | 설명 | 1단계 | 2단계 | 3단계 |
|--------|------|-------|-------|-------|
| R-squared (R2) | 사이토카인 프로파일 예측 결정계수 | >= 0.70 | >= 0.88 | >= 0.90 |
| RMSE | 개별 사이토카인 예측 오차 | 보고 | 보고 | 보고 |
| Profile Cosine Similarity | 다차원 사이토카인 프로파일 유사도 | >= 0.80 | >= 0.92 | >= 0.95 |

**사이토카인 프로파일 정의:**
```
Profile = [IL-6, TNF-alpha, IL-4, IL-10, IL-13, IgE, CRP, IL-5, IL-17, 8-OHdG, MDA]
        = 11차원 벡터

R2 = 1 - sum((y_actual - y_predicted)^2) / sum((y_actual - y_mean)^2)
```

#### C. 공정성 메트릭

| 메트릭 | 설명 | 기준 |
|--------|------|------|
| Demographic Parity | 성별/연령 그룹 간 예측 양성률 차이 | < 0.1 |
| Equalized Odds | 그룹 간 TPR/FPR 차이 | < 0.1 |
| Calibration by Group | 그룹별 예측 확률 교정도 차이 | Brier 차이 < 0.05 |

#### D. 인과 추론 평가

| 메트릭 | 설명 | 목표 |
|--------|------|------|
| Causal Precision | PCMCI+ 발견 중 전문가 검증 통과 비율 | >= 0.60 |
| Causal Recall | 알려진 인과 관계 중 PCMCI+가 탐지한 비율 | >= 0.50 |
| Ontology Alignment | SHAP 상위 피처와 CausalPathway 일치율 | >= 0.50 |
| Link Prediction MRR | R-GCN 링크 예측 Mean Reciprocal Rank | >= 0.30 |
| Link Prediction Hits@10 | 상위 10개 예측 내 정답 포함률 | >= 0.40 |

### 4.3 평가 프로토콜

**교차 검증 전략:**
- 1단계: 5-fold cross-validation (데이터 소규모)
- 2단계: 시간 기반 분할 (temporal train/val/test split)
  - Train: 첫 60% 기간
  - Validation: 다음 20% 기간
  - Test: 마지막 20% 기간
- 3단계: 외부 검증 코호트 (다기관 데이터)

**모델 선택 기준:**
- Primary: AUC-ROC (7개 질환 macro-average)
- Secondary: Brier Score (확률 교정)
- Constraint: Fairness 메트릭 위반 시 모델 기각

### 4.4 MLflow 실험 추적

```
[학습 실행] → [MLflow Tracking]
                │
                ├── Parameters: lr, batch_size, hidden_size, tau, lambda_1, lambda_2
                ├── Metrics: AUC-ROC, AUC-PR, Brier, R2, fairness
                ├── Artifacts: model checkpoint, SHAP plots, confusion matrix
                └── Model Registry: staging → production 승격 워크플로
```

**모델 배포 기준:**
- AUC-ROC >= 단계별 목표
- Brier Score <= 단계별 목표
- Fairness 메트릭 모두 기준 충족
- Ontology Alignment >= 0.50
- 전문가 리뷰 승인
