# Ontology and Knowledge Graph Advancement Plan

작성일: 2026-06-28

## 목적

다음 개발 단계는 현재 core ontology 수준에 머물러 있는 integrated KG를 실제 NHIS 건강정보,
환경 노출, 면역질환 관계 데이터로 확장하는 것이다. 특히 환경 유해물질과 면역질환의 관계를
더 구체화하고, 공공 NHIS 건강검진/진료/환경성질환 데이터를 KG 인스턴스로 연결해야 한다.

## 현재 수준 평가

### Core Ontology

파일:

- `research/01_ontology/immune_care_ontology.owl`

현재 검증된 baseline:

- triples: 821
- OWL classes: 109
- object properties: 14
- datatype properties: 10
- named individuals: 25
- `ico:CausalPathway`: 19
- `owl:versionInfo`: `0.2.0`

직접 subclass 기준 주요 구성:

- `EnvironmentalFactor`: 6개
  - `AirPollutant`
  - `BiologicalAllergen`
  - `CO2Level`
  - `ClimateFactor`
  - `PFAS`
  - `Radon`
- `ImmuneDisease`: 7개
  - `Asthma`
  - `AllergicRhinitis`
  - `AtopicDermatitis`
  - `Psoriasis`
  - `RheumatoidArthritis`
  - `DryEyeDisease`
  - `Alopecia`
- `Biomarker`: 4개
  - `Cytokine`
  - `IgE`
  - `OxidativeDamageMarker`
  - `SystemicInflammationMarker`

현재 강점:

- 환경, 라이프로그, 바이오마커, 플라즈마 치료 layer 구분이 있다.
- PM2.5, VOCs, 상대습도, HRV, sleep, cytokine, IgE, CRP, TNF-alpha, IL-17 등 핵심 경로가
  causal pathway individual로 표현되어 있다.
- 각 causal pathway에 source layer, target layer, evidence strength, lag time, correlation
  coefficient 일부가 들어 있다.
- read-only API, validator, KG exporter, calibration, NHIS RDF generator가 production package로
  들어와 있다.

현재 한계:

- integrated KG는 아직 core OWL과 동일한 821 triples이다.
- NHIS RDF, PMO, bridge source가 committed KG에 결합되어 있지 않다.
- `EnvironmentalFactor`, `ImmuneDisease`, `ImmunePathway`의 실제 instance 수는 매우 적거나 없다.
  현재 핵심 관계는 대부분 `CausalPathway` individual에 집중되어 있다.
- 환경 유해물질 taxonomy가 아직 넓지 않다. PFAS/Radon은 상위 class로 있지만 실제 세부 물질,
  측정 단위, 노출 경로, 질환 연결 경로가 부족하다.
- NHIS 건강검진/진료 데이터가 아직 KG 인스턴스로 안정적으로 변환되지 않았다.

### Integrated KG

파일:

- `research/01_ontology/integrated_knowledge_graph.ttl`
- `research/01_ontology/integrated_knowledge_graph.report.json`

현재 상태:

- Turtle parse OK
- triples: 821
- core OWL snapshot과 동일
- report상 loaded source는 `immune_care_ontology.owl`뿐이다.

결론:

- 현재 KG는 “통합 지식그래프”라기보다 “검증 가능한 core ontology snapshot”에 가깝다.
- 다음 단계의 핵심은 NHIS/환경/바이오마커 데이터를 인스턴스로 생성하고, causal pathway와 연결하는
  것이다.

## 현재 Causal Pathway 수준

현재 19개 causal pathway가 있다.

환경 노출 중심:

- `PM2_5_to_IL6_Path`: PM2.5 -> NF-kB -> IL-6
- `PM2_5_to_TNFa_Path`: PM2.5 -> M1 macrophage -> TNF-alpha
- `PM2_5_to_8OHdG_Path`: PM2.5 -> mitochondrial ROS -> 8-OHdG
- `PM2_5_to_CRP_Path`: PM2.5 -> systemic inflammation -> CRP
- `PM2_5_to_HRV_Path`: PM2.5 -> autonomic imbalance -> HRV decrease
- `PM2_5_to_SpO2_Path`: PM2.5 -> airway inflammation -> SpO2 decrease
- `VOCs_to_IgE_Path`: VOCs -> epithelial barrier -> Th2 -> IgE
- `VOCs_to_Sleep_Path`: VOCs -> airway irritation -> sleep disruption
- `RH_to_IL13_Path`: high relative humidity -> dust mite -> Der p1 -> IL-13

바이오마커/질환 중심:

- `IgE_IL5_to_Asthma_Path`: IgE + IL-5 -> asthma
- `IL4_IL13_to_AtopicDerm_Path`: IL-4/IL-13 -> atopic dermatitis
- `TNFa_IL17_to_Psoriasis_Path`: TNF-alpha + IL-17 -> psoriasis
- `SleepDeprivation_to_CRP_Path`
- `HRV_to_IL6_Path`
- `LowActivity_to_TNFa_Path`
- `CompositeScore_to_AllergicMarch_Path`

플라즈마 치료 중심:

- `CAP_NFkB_Inhibition_Path`
- `CAP_Nrf2_Activation_Path`
- `CAP_Psoriasis_Treatment_Path`

고도화 필요:

- PM2.5 중심 편중을 줄이고, PM10, NO2, SO2, O3, CO, VOC 세부종, formaldehyde, BTEX, PFAS,
  radon, mold/dust mite/allergen, temperature variability 등으로 확장해야 한다.
- 면역질환도 asthma/rhinitis/atopy/psoriasis 중심에서 RA, dry eye, alopecia, rare immune
  disease, drug-prescription-linked disease phenotypes로 확장해야 한다.
- 각 pathway에 evidence source, data source, population/region/time granularity, confidence
  calculation method를 추가해야 한다.

## NHIS 데이터 현재 상태

로컬에 확인된 원자료:

- `data/국민건강보험공단_건강검진정보_20241231.zip`
- `data/국민건강보험공단_진료내역정보_2023.zip`
- `data/국민건강보험공단_환경성질환(천식) 의료이용정보_20241231.xlsx`
- `data/국민건강보험공단_환경성질환(비염) 의료이용정보_20241231.xlsx`
- `data/국민건강보험공단_환경성질환(아토피) 의료이용정보_20241231.xlsx`
- 특정 의약품 처방 CSV
- 희귀질환 건강보험 진료 통계 CSV

현재 processed 상태:

- `data/processed/env_disease_joined.parquet`
  - 읽기 가능
  - 11,628 rows
  - columns: `sido_code`, `year`, `month`, `disease`, `episode_count`, `sido_name`,
    `avg_temp`, `diurnal_range`, `avg_rh`, `avg_pm25`, `avg_pm10`, `avg_o3`, `osl`, `aes`
- 다음 파일은 존재하지만 parquet로 읽히지 않았다.
  - `data/processed/health_checkup_2024.parquet`
  - `data/processed/medical_records_immune_2023.parquet`
  - `data/processed/environmental_disease_combined.parquet`
- 다음 파일은 0바이트였다.
  - `research/02_data_pipeline/correlation_reports/correlation_summary.csv`
  - `research/02_data_pipeline/correlation_reports/biomarker_env_correlations.csv`
  - `research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl`

판단:

- 사용자의 기억처럼 “NHIS에서 건강정보 데이터를 가져오는 순서”가 다음 단계로 맞다.
- 다만 현재는 원자료를 다시 읽어 processed parquet와 correlation CSV를 재생성하는 단계부터 해야 한다.
- 이미 `columbus generate-nhis-rdf`는 준비되어 있으나, 입력 CSV가 0바이트라 바로 KG 확장은 불가능하다.

## 다음 개발 계획

### Phase 1: NHIS 데이터 재생성 및 품질 게이트

목표:

- 원자료 ZIP/XLSX/CSV에서 정상 parquet와 correlation CSV를 재생성한다.

작업:

1. `nhis_data_preprocessor.py`를 production-safe runner로 정리한다.
   - import-time directory creation 제거
   - hard-coded path를 CLI argument로 전환
   - raw input 존재/encoding/sheet 검증 추가
2. 건강검진정보 ZIP을 읽어 `health_checkup_2024.parquet`를 재생성한다.
3. 진료내역정보 ZIP에서 면역질환 ICD-10 subset을 추출해 `medical_records_immune_2023.parquet`를 재생성한다.
4. 환경성질환 XLSX 3종에서 `environmental_disease_combined.parquet`를 재생성한다.
5. parquet smoke validation 추가:
   - row count > 0
   - 필수 컬럼 존재
   - disease code/domain value 검증
   - 날짜/year/month 범위 검증

완료 기준:

```bash
python -m pytest -q tests/pipeline
```

그리고 주요 parquet가 `pd.read_parquet`로 정상 로드되어야 한다.

### Phase 2: 환경-질환/바이오마커 상관 요약 재생성

목표:

- KG 입력으로 쓸 수 있는 correlation summary를 생성한다.

작업:

1. `env_disease_correlator.py`의 pure logic을 `src/project_columbus/pipeline/`로 승격한다.
2. `env_disease_joined.parquet`에서 환경변수-질환 상관을 계산한다.
3. `biomarker_env_analyzer.py` 또는 `biomarker_risk_predictor.py` 흐름에서 건강검진 biomarker와
   환경/질환 proxy를 연결한다.
4. `correlation_summary.csv`, `biomarker_env_correlations.csv`를 재생성한다.
5. CSV schema test 추가:
   - `disease`
   - `env_var`
   - `lag_months`
   - `mean_pearson_r`
   - `mean_spearman_r`
   - `pct_significant`

완료 기준:

- correlation CSV가 0바이트가 아니고, `columbus generate-nhis-rdf` 입력으로 사용 가능해야 한다.

### Phase 3: NHIS RDF 생성 및 integrated KG 결합

목표:

- NHIS 상관요약을 RDF로 만들고 integrated KG에 결합한다.

작업:

1. `columbus generate-nhis-rdf`로 `nhis_disease_instances.ttl` 생성
2. `columbus export-integrated-kg` 실행
3. report에 loaded source로 NHIS RDF가 포함되는지 확인
4. integrated KG triple 수가 821보다 증가하는지 확인
5. SPARQL 테스트 추가:
   - 특정 질환에 연결된 환경요인 조회
   - evidence/correlation coefficient 기준 필터
   - 질환별 top environmental factor 조회

완료 기준:

```bash
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
python -m pytest -q tests/ontology tests/pipeline
```

### Phase 4: 환경 유해물질 taxonomy 확장

목표:

- 환경 유해물질을 실질적으로 구체화한다.

우선 확장 후보:

- particulate matter: PM2.5, PM10, ultrafine particles
- gases: NO2, SO2, O3, CO, CO2
- VOCs: benzene, toluene, ethylbenzene, xylene, formaldehyde
- persistent chemicals: PFAS, PFOA, PFOS
- indoor hazards: mold, dust mite allergen, radon
- climate stressors: temperature, relative humidity, diurnal temperature range, heat wave, cold wave
- composite exposure indices: OSL, AES, ventilation index

각 물질/요인마다 추가할 속성:

- measurement unit
- exposure route
- indoor/outdoor source
- target immune pathway
- known biomarker response
- linked disease phenotype
- evidence grade
- data source

### Phase 5: 면역질환 phenotype 확장

목표:

- NHIS ICD-10 기반 면역질환 phenotype을 ontology와 KG에 연결한다.

우선 대상:

- asthma: J45/J46
- allergic rhinitis: J30/J31
- atopic dermatitis: L20
- contact dermatitis/urticaria: L23/L50
- rheumatoid arthritis: M05/M06
- systemic autoimmune/connective tissue disorders: M32/M35
- inflammatory bowel disease: K50/K51
- immune deficiency: D80-D84/D89
- psoriasis: L40
- dry eye: H04.1
- alopecia: L63/L65 후보 검토

작업:

- ICD-10 mapping table을 ontology annotation 또는 KG mapping instance로 추가
- NHIS disease episode observation과 ontology disease class 연결
- prescription/drug proxy와 disease severity proxy 검토

### Phase 6: Evidence 모델 정교화

목표:

- 단순 correlation coefficient를 넘어 evidence strength를 계산 가능하게 만든다.

추가할 요소:

- sample size
- region count
- time lag
- p-value/significance percent
- consistency across regions
- directionality
- literature-backed prior
- NHIS-backed evidence

출력:

- `EvidenceBasedCorrelation`
- `EnvironmentalCorrelation`
- `CausalPathway` 간 관계 정리
- API/CLI에서 evidence 기준 필터 가능하게 확장

## 권장 다음 작업 지시문

다음 작업을 시작할 때는 아래처럼 지시하면 된다.

```text
NHIS 건강검진정보/진료내역/환경성질환 원자료를 다시 읽어 processed parquet를 정상 재생성하고,
correlation_summary.csv까지 만든 뒤, columbus generate-nhis-rdf와 export-integrated-kg로
NHIS RDF를 integrated KG에 결합해줘. 기존 사용자 파일은 삭제하지 말고, TDD로 pipeline
validation 테스트부터 추가해.
```

## 시작 전 확인 명령

```bash
git status --short --branch
python -m pytest -q
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
ls -lh data/processed research/02_data_pipeline/correlation_reports research/02_data_pipeline/rdf_output
```
