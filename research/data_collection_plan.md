# 면역 케어 온톨로지 데이터 수집 전략
# Immune Care Ontology (ICO) Data Collection Strategy

**문서 버전**: 1.0
**작성일**: 2026-03-30
**단계**: 1단계 (시드연구) 계획 문서
**상태**: Draft

---

## 1. 데이터 수집 목적 및 전략 개요

### 1.1 데이터 수집 목적

본 데이터 수집 계획은 면역 케어 온톨로지(ICO)의 3가지 핵심 요구사항을 충족하기 위해 설계되었다.

**목적 1: 25개 인과 경로(Causal Pathway) 검증**
- 도메인 분석서에 정의된 환경-면역 인과 체인 (예: PM2.5→ROS→NF-κB→IL-6) 의 통계적 검증
- 각 경로의 상관계수(r), 시간 지연(lag), 효과 크기(effect size) 실측 확인
- 최소 경로당 200-500 관측치 필요 (통계적 검정력 0.80 기준)

**목적 2: Multi-task TFT 모델 학습**
- 114차원 시계열 입력 + 7개 질환 × 4개 시간 수평선 예측
- 최소 학습 데이터: 질환당 500명 이상 × 90일 시계열 (lookback window)
- 1단계 목표: 기준선 AUC 0.75 달성

**목적 3: 온톨로지 인스턴스(Instance) 채움**
- ICO의 4개 신규 모듈 (EnvImmune, Lifelog, ImmuneTrajectory, PMO)에 실측 인스턴스 투입
- SPARQL 쿼리 가능한 지식 그래프 구축
- 최소 클래스당 100개 이상 인스턴스 확보 목표

### 1.2 3-Tier 수집 전략

| Tier | 전략 | 기간 | 투입 비용 | 예상 데이터 규모 |
|------|------|------|---------|---------------|
| **Tier 1** | 공개 데이터셋 즉시 활용 | 0-3개월 | 낮음 (인건비만) | ~수백만 레코드 |
| **Tier 2** | 자체 센서/웨어러블 데이터 수집 | 3-9개월 | 중간 (장비 구매) | ~수십만 시계열 포인트 |
| **Tier 3** | 협력 기관 데이터 공유 | 9-24개월 | 높음 (공동연구) | ~수백만 레코드 |

### 1.3 단계별 최소 실행 가능 데이터셋 (Minimum Viable Dataset)

| 마일스톤 | 시점 | 내용 | 규모 |
|---------|------|------|------|
| **MVD-1** | 2026.07 (3개월) | Tier 1 공개 데이터 통합, 환경-질환 상관분석 가능 | NHIS 100만 + AirKorea 5년 |
| **MVD-2** | 2026.12 (9개월) | 자체 센서 파일럿 데이터 + 공개 데이터 병합, TFT 프로토타입 학습 가능 | 10명 × 90일 센서 데이터 |
| **MVD-3** | 2027.06 (15개월) | Tier 3 일부 + 확대 센서, TFT 본격 학습 가능 | 50명 × 180일 |
| **MVD-4** | 2027.12 (21개월) | 1단계 완료, 전체 파이프라인 검증 | 100명 × 365일 |

---

## 2. Tier 1: 공개 데이터셋 즉시 활용 (0-3개월)

### 2.A 환경 데이터

#### 2.A.1 AirKorea (에어코리아) — 실시간 대기질

| 항목 | 내용 |
|------|------|
| **데이터명** | 에어코리아 실시간/통계 대기오염 정보 |
| **제공 기관** | 한국환경공단 |
| **URL** | https://www.airkorea.or.kr |
| **API 포털** | https://data.go.kr — 한국환경공단_에어코리아_대기오염정보 |
| **데이터 항목** | PM2.5, PM10, O3, NO2, SO2, CO (6개 항목) |
| **시간 해상도** | 1시간 단위 |
| **공간 해상도** | 전국 ~640개 측정소 (도시대기, 도로변, 국가배경) |
| **라이선스** | 공공데이터 개방 (공공누리 1유형) |
| **데이터 규모** | 640소 × 6항목 × 24시간 × 365일 × 5년 ≈ ~1억 레코드 |
| **ICO 매핑** | `ico:envimmune/EnvironmentalExposureEvent` (PM2.5, O3 인스턴스), `ico:envimmune/OxidativeStressLoad` 산출 입력 |

**API 호출 예시:**

```python
import requests
import pandas as pd

# 에어코리아 실시간 측정정보 API
API_KEY = "YOUR_DATA_GO_KR_API_KEY"
BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

def fetch_airkorea_realtime(station_name: str = "창원"):
    """실시간 측정소별 대기질 데이터 조회"""
    url = f"{BASE_URL}/getMsrstnAcctoRltmMesureDnsty"
    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "numOfRows": 24,       # 최근 24시간
        "pageNo": 1,
        "stationName": station_name,
        "dataTerm": "DAILY",
        "ver": "1.0"
    }
    resp = requests.get(url, params=params)
    data = resp.json()["response"]["body"]["items"]
    df = pd.DataFrame(data)
    # 주요 컬럼: dataTime, pm25Value, pm10Value, o3Value, no2Value, so2Value, coValue
    return df

def fetch_airkorea_daily_avg(sido: str = "경남", search_date: str = "2026-04-01"):
    """시도별 일평균 대기질 조회"""
    url = f"{BASE_URL}/getCtprvnRltmMesureDnsty"
    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "numOfRows": 100,
        "pageNo": 1,
        "sidoName": sido,
        "ver": "1.0"
    }
    resp = requests.get(url, params=params)
    return resp.json()["response"]["body"]["items"]
```

**Cron 수집 스케줄:** 매 1시간 (정각 + 5분, API 갱신 딜레이 고려)

---

#### 2.A.2 KMA 기상청 — 기상 관측 데이터

| 항목 | 내용 |
|------|------|
| **데이터명** | 종관기상관측 (ASOS) / 방재기상관측 (AWS) |
| **제공 기관** | 기상청 |
| **URL** | https://data.kma.go.kr (기상자료개방포털) |
| **API 포털** | https://data.go.kr — 기상청_지상(종관, 방재)시간자료 |
| **데이터 항목** | 기온, 상대습도, 기압, 풍속, 풍향, 일사량, 강수량, 자외선지수 |
| **시간 해상도** | 1시간 (ASOS), 10분 (AWS) |
| **공간 해상도** | ASOS 102소, AWS ~510소 |
| **라이선스** | 공공누리 1유형 |
| **데이터 규모** | ASOS 102소 × 8항목 × 24h × 365d × 5y ≈ ~3,600만 레코드 |
| **ICO 매핑** | `ico:envimmune/EnvironmentalExposureEvent` (온도, 습도 인스턴스), `ico:envimmune/AllergenExposureScore` 산출 입력 (습도→진드기 위험) |

**API 호출 예시:**

```python
import requests
from datetime import datetime

KMA_API_KEY = "YOUR_DATA_GO_KR_API_KEY"

def fetch_kma_asos_hourly(stn_id: str = "155", date: str = "20260401", hour: str = "1200"):
    """종관기상관측(ASOS) 시간자료 조회 — 창원 측정소(155)"""
    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    params = {
        "serviceKey": KMA_API_KEY,
        "pageNo": 1,
        "numOfRows": 24,
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": date,
        "startHh": "00",
        "endDt": date,
        "endHh": "23",
        "stnIds": stn_id
    }
    resp = requests.get(url, params=params)
    items = resp.json()["response"]["body"]["items"]["item"]
    # 주요 필드: tm(시각), ta(기온°C), hm(상대습도%), ps(해면기압hPa),
    #            ws(풍속m/s), rn(강수량mm), icsr(일사량MJ/m2)
    return pd.DataFrame(items)

def fetch_kma_uv_index(area_no: str = "4812000000"):
    """자외선지수 조회 (창원시)"""
    url = "http://apis.data.go.kr/1360000/LivingWthrIdxServiceV4/getUVIdxV4"
    params = {
        "serviceKey": KMA_API_KEY,
        "dataType": "JSON",
        "areaNo": area_no,
        "time": datetime.now().strftime("%Y%m%d%H")
    }
    resp = requests.get(url, params=params)
    return resp.json()
```

---

#### 2.A.3 실내공기질 공개데이터 (환경부)

| 항목 | 내용 |
|------|------|
| **데이터명** | 다중이용시설 실내공기질 측정결과 |
| **제공 기관** | 환경부 / 한국환경공단 |
| **URL** | https://iaq.nier.go.kr (실내공기질 정보시스템) |
| **API 포털** | https://data.go.kr — 환경부_다중이용시설_실내공기질_측정결과 |
| **데이터 항목** | PM10, CO2, HCHO, TVOC, CO, 라돈 (시설별) |
| **시간 해상도** | 반기 1회 측정 (법정의무) / IoT 연속측정소 일부 |
| **공간 해상도** | 다중이용시설 ~2만 개소 |
| **라이선스** | 공공누리 1유형 |
| **데이터 규모** | ~2만 시설 × 6항목 × 2회/년 × 5년 ≈ 120만 레코드 |
| **ICO 매핑** | `ico:envimmune/EnvironmentalExposureEvent` (실내 VOC, HCHO 인스턴스), `ico:envimmune/VentilationIndex` 검증 참고 |

**다운로드 방법:**

```python
# 공공데이터포털 API 방식
def fetch_indoor_air_quality(year: int = 2025):
    url = "http://apis.data.go.kr/B552584/IoTAirQltSmrySvc/getIoTAirQltSmry"
    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "numOfRows": 1000,
        "pageNo": 1,
        "year": str(year),
    }
    resp = requests.get(url, params=params)
    return resp.json()

# 벌크 다운로드: iaq.nier.go.kr > 데이터 다운로드 > CSV 파일
# 파일 포맷: facility_id, facility_type, pm10, co2, hcho, tvoc, co, radon, measure_date
```

---

#### 2.A.4 EPA AQS (미국 환경보호청) — VOCs/BTEX 참조 데이터

| 항목 | 내용 |
|------|------|
| **데이터명** | Air Quality System (AQS) — HAPs (Hazardous Air Pollutants) |
| **제공 기관** | U.S. EPA |
| **URL** | https://aqs.epa.gov/aqsweb/airdata/download_files.html |
| **API** | https://aqs.epa.gov/data/api/ (AQS API) |
| **데이터 항목** | Benzene, Toluene, Ethylbenzene, Xylene (BTEX), Formaldehyde, Acetaldehyde 등 |
| **시간 해상도** | 1시간 / 24시간 평균 |
| **공간 해상도** | 미국 전역 ~4,000 모니터 |
| **라이선스** | Public Domain (미국 연방정부 데이터) |
| **데이터 규모** | 연간 ~5,000만 레코드 (전체 HAPs) |
| **ICO 매핑** | `ico:envimmune/EnvironmentalExposureEvent` (BTEX 참조 농도), 한국 실내 VOC 센서 교정 기준치 |

**다운로드 예시:**

```python
import requests

def fetch_epa_btex_data(param_code: str = "45201", year: int = 2024,
                         state: str = "06"):
    """
    EPA AQS API — BTEX 개별 화합물 조회
    param_code: 45201=Benzene, 45202=Toluene, 45203=Ethylbenzene, 45204=m,p-Xylene
    """
    url = "https://aqs.epa.gov/data/api/dailyData/byState"
    params = {
        "email": "your.email@kims.re.kr",
        "key": "YOUR_EPA_AQS_API_KEY",
        "param": param_code,
        "bdate": f"{year}0101",
        "edate": f"{year}1231",
        "state": state
    }
    resp = requests.get(url, params=params)
    return resp.json()["Data"]

# 벌크 다운로드 (연도별 CSV)
# wget https://aqs.epa.gov/aqsweb/airdata/daily_HAPS_2024.zip
```

---

### 2.B 건강/면역 데이터

#### 2.B.1 NHIS 국민건강보험 표본코호트 (100만명)

| 항목 | 내용 |
|------|------|
| **데이터명** | 국민건강보험 표본코호트 DB (NHIS-NSC 2.0) |
| **제공 기관** | 국민건강보험공단 |
| **URL** | https://nhiss.nhis.or.kr (국민건강보험 데이터포럼) |
| **접근 방법** | 연구자 신청 → IRB 승인 → 원격 분석 환경 (NHIS 분석실 또는 원격접속시스템) |
| **데이터 항목** | 자격 DB, 진료 DB (ICD-10), 건강검진 DB, 요양기관 DB |
| **면역질환 ICD-10 코드** | L20(아토피피부염), J45(천식), J30(알레르기비염), L40(건선), H04.1(안구건조증), M05-06(류마티스관절염), L63-64(탈모) |
| **건강검진 항목** | BMI, 혈압, 공복혈당, 총콜레스테롤, AST/ALT, eGFR, 흡연, 음주, 운동 |
| **코호트 규모** | 100만 명 (전 국민의 약 2% 대표 표본) × 14년 추적 (2006-2019) |
| **라이선스** | 연구 목적 사용 허가제 (이용료 있음) |
| **데이터 규모** | 진료 DB: ~8억 건, 건강검진: ~1,400만 건 |
| **ICO 매핑** | `ico:trajectory/DiseaseTrajectory` (ICD-10 코드 시계열), `ico:trajectory/AllergicMarchProgression` (알레르기 마치 패턴 추출) |

**접근 절차:**
1. NHIS 데이터포럼 회원가입 (https://nhiss.nhis.or.kr)
2. 연구계획서 작성 (과제번호 RS-2026-25516000 명시)
3. 기관 IRB 승인서 첨부
4. 데이터 이용 심의 신청 (약 2-3개월 소요)
5. 승인 후 원격 분석 환경(가상화 데스크톱) 접속

**분석 코드 예시 (원격 분석실 내부):**

```python
# NHIS 원격 분석실 내에서 실행 (SAS/R/Python)
import pandas as pd

# 1. 면역질환 진단 코호트 추출
immune_icd = ['L20', 'J45', 'J30', 'L40', 'H041', 'M05', 'M06', 'L63', 'L64']
query = """
SELECT PERSON_ID, RECU_FR_DT AS DIAG_DATE, MAIN_SICK AS ICD_CODE,
       DSBJT_CD AS DEPARTMENT, EDEC_TRMT_CNTS AS VISIT_COUNT
FROM NHI_GY20_T1
WHERE SUBSTR(MAIN_SICK, 1, 3) IN ('L20','J45','J30','L40','M05','M06','L63','L64')
   OR SUBSTR(MAIN_SICK, 1, 4) IN ('H041')
ORDER BY PERSON_ID, DIAG_DATE
"""

# 2. 알레르기 마치 패턴 추출
# L20(아토피) → J45(천식) → J30(알레르기비염) 순차 발생 환자
march_query = """
SELECT a.PERSON_ID,
       MIN(CASE WHEN SUBSTR(MAIN_SICK,1,3)='L20' THEN RECU_FR_DT END) AS AD_ONSET,
       MIN(CASE WHEN SUBSTR(MAIN_SICK,1,3)='J45' THEN RECU_FR_DT END) AS ASTHMA_ONSET,
       MIN(CASE WHEN SUBSTR(MAIN_SICK,1,3)='J30' THEN RECU_FR_DT END) AS RHINITIS_ONSET
FROM NHI_GY20_T1 a
GROUP BY a.PERSON_ID
HAVING AD_ONSET IS NOT NULL AND ASTHMA_ONSET IS NOT NULL
   AND AD_ONSET < ASTHMA_ONSET
"""

# 3. 건강검진 데이터 결합
checkup_query = """
SELECT c.PERSON_ID, c.HME_DT AS CHECKUP_DATE,
       c.HEIGHT, c.WEIGHT, c.BMI, c.BP_HIGH, c.BP_LWST,
       c.BLDS AS FASTING_GLUCOSE, c.TOT_CHOLE, c.SGOT_AST, c.SGPT_ALT,
       c.SMK_STAT_TYPE_RSPS_CD AS SMOKING, c.DRNK_HABIT_RSPS_CD AS DRINKING
FROM NHI_HE_T1 c
"""
```

**예상 추출 규모:**
- 면역질환 진단자: 100만 명 중 약 15-20% = 15-20만 명
- 알레르기 마치 패턴 대상자: 약 2-5만 명
- 건강검진 연계: 약 10-12만 명

---

#### 2.B.2 KoGES 한국인유전체역학조사

| 항목 | 내용 |
|------|------|
| **데이터명** | 한국인유전체역학조사 (Korean Genome and Epidemiology Study) |
| **제공 기관** | 질병관리청 국립보건연구원 |
| **URL** | https://nih.go.kr/ko/main/contents.do?menuNo=300566 |
| **신청 포털** | https://bio.kdca.go.kr (국립중앙인체자원은행) |
| **코호트 유형** | 지역사회 코호트(안산/안성), 도시 코호트, 농촌 코호트, 쌍둥이 코호트 |
| **데이터 항목** | 유전체(GWAS SNP array), 생활습관, 신체계측, 혈액 바이오마커, 질병력 |
| **면역 관련 필드** | IgE, 알레르기 유병여부, 천식/비염/아토피 자가보고, WBC 분획, CRP |
| **코호트 규모** | 약 21만 명, 2-4년 주기 추적관찰 (2001~현재) |
| **유전체 데이터** | Affymetrix 6.0 / KoreanChip (~83만 SNP) |
| **라이선스** | 연구 목적 사용 허가제 (무료, 승인 필요) |
| **ICO 매핑** | `ico:trajectory/ImmuneRiskScore` (유전적 위험 점수), `ico:envimmune/ExposureImmunePath` (환경+유전 교호작용) |

**접근 절차:**
1. 국립중앙인체자원은행 포털 연구자 등록
2. 자원분양 신청서 + 연구계획서
3. 기관 IRB 승인서
4. 자원분양 심의 (약 1-2개월)
5. 승인 후 데이터 파일 수령 (비식별화 처리 완료)

**분석 코드 예시:**

```python
import pandas as pd
import numpy as np

# KoGES 데이터 로드 (승인 후 수령한 파일)
koges_baseline = pd.read_csv("koges_baseline_data.csv")
koges_followup = pd.read_csv("koges_followup_data.csv")
koges_gwas = pd.read_csv("koges_snp_summary.csv")  # SNP 요약통계

# 면역 관련 표현형 추출
immune_pheno = koges_baseline[[
    'ID', 'AGE', 'SEX', 'BMI',
    'ALLERGY_YN',        # 알레르기 유무
    'ASTHMA_YN',         # 천식 유무
    'RHINITIS_YN',       # 비염 유무
    'ATOPIC_YN',         # 아토피 유무
    'IGE_TOTAL',         # 총 IgE
    'WBC', 'EOSINOPHIL', # 백혈구 분획
    'CRP',               # C-반응단백
    'SMOKE_STATUS', 'DRINK_STATUS', 'EXERCISE'
]]

# 유전자-환경 교호작용 분석을 위한 병합
# (거주지 기반 AirKorea 대기질 연계)
koges_with_air = koges_baseline.merge(
    airkorea_annual_avg,  # 거주지별 연평균 대기질
    on='REGION_CODE',
    how='left'
)
```

---

#### 2.B.3 KNHANES 국민건강영양조사

| 항목 | 내용 |
|------|------|
| **데이터명** | 국민건강영양조사 (Korea National Health and Nutrition Examination Survey) |
| **제공 기관** | 질병관리청 |
| **URL** | https://knhanes.kdca.go.kr |
| **접근 방법** | 웹사이트 회원가입 후 즉시 다운로드 가능 (무료) |
| **데이터 항목** | 건강설문, 검진조사, 영양조사 (약 600개 변수) |
| **면역 관련 필드** | 아토피피부염 의사진단, 천식 유병, 알레르기비염 유병, 총 IgE (일부 기수), 폐기능 (FEV1/FVC), WBC, 호산구, CRP (hs-CRP, 제7기~) |
| **규모** | 연간 약 8,000-10,000명, 1998~현재 축적 ~20만 명 |
| **라이선스** | 공개 데이터 (회원가입 후 다운로드) |
| **ICO 매핑** | `ico:trajectory/DiseaseTrajectory` (알레르기 유병률 기준치), `ico:lifelog/ActivityLevel` (신체활동 설문), 바이오마커 참조 범위 |

**다운로드 및 분석 예시:**

```python
import pandas as pd

# KNHANES 원시데이터 다운로드 (SAS/CSV/SPSS)
# URL: https://knhanes.kdca.go.kr/knhanes/sub03/sub03_02_05.do

# 제8기 1차년도(2019) 데이터 로드 예시
knhanes = pd.read_sas("HN19_ALL.sas7bdat")

# 면역질환 관련 변수 추출
immune_vars = knhanes[[
    'ID', 'age', 'sex', 'HE_BMI',
    'DI1_dg',    # 아토피피부염 의사진단 유무
    'DI2_dg',    # 천식 의사진단 유무
    'DI3_dg',    # 알레르기비염 의사진단 유무
    'HE_WBC',    # 백혈구 수
    'HE_RBC',    # 적혈구 수
    'HE_Eosinophil',  # 호산구 (%)
    'HE_CRP',    # hs-CRP (제7기~)
    'HE_FEV1',   # 1초간 강제호기량
    'HE_FVC',    # 강제폐활량
    'BE5_1',     # 음주 빈도
    'BS1_1',     # 현재 흡연 여부
    'BE3_31',    # 걷기 일수/주
    'pa_aerobic', # 유산소 신체활동 실천율
]]

# 알레르기 유병률 산출 (가중치 적용)
from survey import SurveyDesign  # or use statsmodels
prevalence = knhanes.groupby('DI3_dg').apply(
    lambda x: np.average(x['wt_itvex'], weights=x['wt_itvex'])
)
```

---

#### 2.B.4 UK Biobank — 대규모 바이오뱅크

| 항목 | 내용 |
|------|------|
| **데이터명** | UK Biobank |
| **제공 기관** | UK Biobank Ltd. (영국) |
| **URL** | https://www.ukbiobank.ac.uk |
| **접근 방법** | 연구 신청 (Application) → 심의 → 승인 (약 3-6개월) |
| **데이터 항목** | 유전체(imputed ~97M SNPs), 가속도계(7일), 대기오염(PM2.5/NO2/NOx, 주소기반), 혈액 바이오마커(~30종), 진단 이력 |
| **면역 관련 필드** | hs-CRP (Field 30710), WBC/분획 (30000-30130), IgE 일부, 알레르기 자가보고 (Field 6152), 폐기능 (3062/3063), 진단 ICD-10 |
| **규모** | ~500,000명 (40-69세, 2006-2010 등록), ~93,000명 가속도계 |
| **비용** | 연간 접근 비용 있음 (학술 기관 할인) |
| **라이선스** | 연구 사용 허가 (MTA 필요) |
| **ICO 매핑** | `ico:envimmune/ExposureImmunePath` (대기오염-면역마커 종단 연관), `ico:lifelog/ActivityLevel` (가속도계 기반) |

**접근 절차:**
1. UK Biobank Access Management System (AMS) 등록
2. 연구계획서 제출 (Application 번호 발급)
3. 데이터 접근 위원회 심의 (약 2-3개월)
4. 승인 후 UK Biobank Research Analysis Platform (RAP) 접속
5. 또는 벌크 데이터 다운로드 (AWS/DNAnexus)

```python
# UK Biobank 데이터 접근 (승인 후, ukbiobank 패키지 활용)
# pip install ukbb-tools

# RAP 환경 내에서:
import dxpy  # DNAnexus Python API

# 면역 관련 필드 추출
fields_of_interest = {
    30710: "hs_CRP",           # C-reactive protein
    30000: "WBC_count",        # White blood cell count
    30120: "Lymphocyte_count",
    30130: "Monocyte_count",
    30150: "Eosinophil_count",
    30160: "Basophil_count",
    24003: "PM2.5_2010",       # Modelled PM2.5 at residence
    24004: "PM10_2010",
    24005: "PMcoarse_2010",
    24006: "NO2_2010",
    24007: "NOx_2010",
    90012: "accel_overall_avg", # Accelerometer average acceleration
    3062:  "FEV1",
    3063:  "FVC",
}
```

---

### 2.C 바이오마커/분자 데이터

#### 2.C.1 CTD (Comparative Toxicogenomics Database)

| 항목 | 내용 |
|------|------|
| **데이터명** | CTD — 화학물질-유전자-질병 상호작용 DB |
| **제공 기관** | Mount Desert Island Biological Laboratory (MDI) |
| **URL** | https://ctdbase.org |
| **접근 방법** | 웹 다운로드 (무료, 즉시) |
| **데이터 항목** | Chemical-Gene, Chemical-Disease, Gene-Disease 연관, 분자 경로 |
| **면역 관련** | PM2.5→NF-κB→IL6 인과 체인 근거, VOC→면역독성 경로 |
| **데이터 포맷** | TSV / XML / JSON |
| **규모** | ~4,700만 화학물질-유전자-질병 상호작용 |
| **라이선스** | CC-BY (학술 무료) |
| **ICO 매핑** | `ico:envimmune/ExposureImmunePath` 인과 경로 근거, `ico:trajectory/CausalPathway` 검증 |

**다운로드 및 분석 예시:**

```python
import pandas as pd
import requests

# CTD 벌크 다운로드
# wget https://ctdbase.org/reports/CTD_chem_gene_ixns.tsv.gz
# wget https://ctdbase.org/reports/CTD_chemicals_diseases.tsv.gz
# wget https://ctdbase.org/reports/CTD_genes_diseases.tsv.gz

# PM2.5 관련 유전자-질병 상호작용 조회 (API)
def query_ctd_chemical(chemical_name: str = "Particulate Matter"):
    """CTD API로 특정 화학물질의 유전자 상호작용 조회"""
    url = "https://ctdbase.org/tools/batchQuery.go"
    params = {
        "inputType": "chem",
        "inputTerms": chemical_name,
        "report": "genes_curated",
        "format": "json"
    }
    resp = requests.get(url, params=params)
    return resp.json()

# PM2.5 → 면역 관련 유전자 경로 추출
pm25_genes = pd.read_csv("CTD_chem_gene_ixns.tsv.gz", sep="\t", comment="#")
pm25_immune = pm25_genes[
    (pm25_genes["ChemicalName"].str.contains("Particulate Matter")) &
    (pm25_genes["GeneSymbol"].isin(["IL6", "TNF", "NFKB1", "IL4", "IL13", "IL10"]))
]

# VOCs 관련 면역독성 경로
voc_chemicals = ["Benzene", "Toluene", "Formaldehyde", "Xylenes"]
voc_immune = pm25_genes[
    pm25_genes["ChemicalName"].isin(voc_chemicals) &
    pm25_genes["InteractionActions"].str.contains("expression")
]
```

---

#### 2.C.2 Reactome — 면역 신호전달 경로

| 항목 | 내용 |
|------|------|
| **데이터명** | Reactome Pathway Database |
| **제공 기관** | Reactome Consortium (EMBL-EBI, OICR, NYU) |
| **URL** | https://reactome.org |
| **API** | https://reactome.org/ContentService/ (REST API) |
| **데이터 항목** | 생물학적 경로(Pathway), 반응(Reaction), 분자 참여자, 조절 관계 |
| **면역 관련 경로** | R-HSA-168256 (면역계), R-HSA-9607240 (NF-κB 활성화), R-HSA-1280215 (사이토카인 신호전달), R-HSA-1280218 (어댑터 면역) |
| **데이터 포맷** | BioPAX, SBML, JSON, TSV |
| **규모** | ~2,700 경로, ~14,000 반응 (인간) |
| **라이선스** | CC-BY 4.0 |
| **ICO 매핑** | `ico:trajectory/CausalPathway` (NF-κB, Nrf2/Keap1, MAPK 경로 구조), `ico:pmo/PlasmaImmuneModulation` (RONS 관련 경로) |

**API 호출 예시:**

```python
import requests

REACTOME_API = "https://reactome.org/ContentService"

def get_immune_pathways():
    """면역계 하위 경로 전체 조회"""
    url = f"{REACTOME_API}/data/pathway/R-HSA-168256/containedEvents"
    resp = requests.get(url, headers={"Accept": "application/json"})
    pathways = resp.json()
    return [(p["stId"], p["displayName"]) for p in pathways]

def get_nfkb_participants():
    """NF-κB 경로 참여 분자 조회"""
    url = f"{REACTOME_API}/data/participants/R-HSA-9607240"
    resp = requests.get(url, headers={"Accept": "application/json"})
    return resp.json()

def get_pathway_as_biopax(pathway_id: str = "R-HSA-9607240"):
    """BioPAX 형식으로 경로 다운로드 (온톨로지 통합용)"""
    url = f"{REACTOME_API}/data/pathway/{pathway_id}/BioPAX3"
    resp = requests.get(url)
    with open(f"{pathway_id}.owl", "w") as f:
        f.write(resp.text)

# 벌크 다운로드
# wget https://reactome.org/download/current/ReactomePathways.gmt.zip
# wget https://reactome.org/download/current/interactors/reactome.homo_sapiens.interactions.tab-delimited.txt
```

---

#### 2.C.3 Gene Ontology Annotations — 면역 관련 유전자 기능 주석

| 항목 | 내용 |
|------|------|
| **데이터명** | GO Annotations (GOA) — Human |
| **제공 기관** | Gene Ontology Consortium / UniProt-GOA |
| **URL** | https://geneontology.org |
| **다운로드** | https://current.geneontology.org/annotations/ |
| **데이터 항목** | 유전자-GO term 매핑 (Molecular Function, Biological Process, Cellular Component) |
| **면역 관련 GO terms** | GO:0006955 (immune response), GO:0045087 (innate immune), GO:0002250 (adaptive immune), GO:0000302 (response to ROS), GO:0006954 (inflammatory response) |
| **데이터 포맷** | GAF 2.2, GPAD 2.0 |
| **규모** | 인간: ~700,000 주석 (전체: ~18억) |
| **라이선스** | CC-BY 4.0 |
| **ICO 매핑** | `GO` 온톨로지 직접 import (BFO 기반), `ico:trajectory/CausalPathway` 유전자 기능 레이어 |

**다운로드 및 분석 예시:**

```python
import pandas as pd

# GO Annotation 다운로드 (인간)
# wget https://current.geneontology.org/annotations/goa_human.gaf.gz

# GAF 파일 파싱
gaf_cols = ['DB', 'DB_Object_ID', 'DB_Object_Symbol', 'Qualifier',
            'GO_ID', 'DB_Reference', 'Evidence_Code', 'With_From',
            'Aspect', 'DB_Object_Name', 'DB_Object_Synonym',
            'DB_Object_Type', 'Taxon', 'Date', 'Assigned_By',
            'Annotation_Extension', 'Gene_Product_Form_ID']

goa_human = pd.read_csv("goa_human.gaf.gz", sep="\t", comment="!",
                          header=None, names=gaf_cols)

# 면역 관련 GO term 필터링
immune_go_terms = [
    "GO:0006955",  # immune response
    "GO:0045087",  # innate immune response
    "GO:0002250",  # adaptive immune response
    "GO:0000302",  # response to reactive oxygen species
    "GO:0006954",  # inflammatory response
    "GO:0050776",  # regulation of immune response
    "GO:0034097",  # response to cytokine
]

immune_genes = goa_human[goa_human["GO_ID"].isin(immune_go_terms)]
# 예상 결과: ~3,000-5,000개 유전자-GO 주석
```

---

#### 2.C.4 Exposome-Explorer — 노출 바이오마커 데이터

| 항목 | 내용 |
|------|------|
| **데이터명** | Exposome-Explorer |
| **제공 기관** | IARC (International Agency for Research on Cancer) |
| **URL** | http://exposome-explorer.iarc.fr |
| **접근 방법** | 웹 검색 + CSV 다운로드 (무료) |
| **데이터 항목** | 노출 바이오마커, 식이 바이오마커, 화학물질-바이오마커 매핑, 역학 연구 메타데이터 |
| **면역 관련** | 대기오염 바이오마커 (8-OHdG, MDA 등 산화손상 마커), 흡연/음주 바이오마커 |
| **규모** | ~900개 바이오마커, ~14,000 상관 관계 |
| **라이선스** | 학술 무료 |
| **ICO 매핑** | `ico:envimmune/ExposureImmunePath` (노출-바이오마커 연결), 바이오마커 참조 범위 |

```python
# Exposome-Explorer 데이터는 웹 인터페이스에서 CSV 내보내기
# http://exposome-explorer.iarc.fr/search?utf8=✓&query=oxidative+stress

# 또는 벌크 다운로드 (Supplementary Data)
# 예: 산화 스트레스 관련 노출 바이오마커
oxidative_markers = pd.read_csv("exposome_explorer_oxidative.csv")
# 컬럼: biomarker_name, exposure, correlation, study_pmid, sample_size, matrix
```

---

### 2.D 플라즈마 의학 데이터

#### 2.D.1 PubMed/PMC 문헌 마이닝

| 항목 | 내용 |
|------|------|
| **데이터명** | PubMed/PMC — CAP + immune 관련 논문 |
| **제공 기관** | NCBI / NLM |
| **URL** | https://pubmed.ncbi.nlm.nih.gov |
| **API** | E-utilities (https://eutils.ncbi.nlm.nih.gov/entrez/eutils/) |
| **검색 쿼리** | `("cold atmospheric plasma" OR "non-thermal plasma" OR "CAP") AND ("immune" OR "RONS" OR "reactive oxygen" OR "reactive nitrogen") AND ("in vivo" OR "clinical" OR "animal model")` |
| **추출 대상** | RONS 종류/농도, 플라즈마 파라미터 (전압, 주파수, 가스), 면역 마커 변화량, 용량-반응 관계 |
| **예상 논문 수** | ~500-800편 (2015-2026) |
| **ICO 매핑** | `ico:pmo/RONSGeneration` (RONS 생성 파라미터), `ico:pmo/PlasmaImmuneModulation` (면역조절 효과), `ico:pmo/HormesisResponse` (호르메시스 용량-반응) |

**문헌 마이닝 자동화:**

```python
from Bio import Entrez
import xml.etree.ElementTree as ET

Entrez.email = "shlee@kims.re.kr"

def search_cap_immune_papers(max_results: int = 500):
    """CAP + 면역 관련 논문 검색"""
    query = (
        '("cold atmospheric plasma"[Title/Abstract] OR '
        '"non-thermal plasma"[Title/Abstract]) AND '
        '("immune"[Title/Abstract] OR "RONS"[Title/Abstract] OR '
        '"reactive oxygen species"[Title/Abstract]) AND '
        '("in vivo" OR "clinical trial" OR "animal model")'
    )
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results,
                             sort="relevance")
    record = Entrez.read(handle)
    return record["IdList"]

def fetch_paper_details(pmid_list: list):
    """논문 상세 정보 (제목, 초록, MeSH) 가져오기"""
    ids = ",".join(pmid_list[:200])  # API 제한
    handle = Entrez.efetch(db="pubmed", id=ids, rettype="xml")
    tree = ET.parse(handle)
    papers = []
    for article in tree.findall(".//PubmedArticle"):
        title = article.findtext(".//ArticleTitle")
        abstract = article.findtext(".//AbstractText")
        pmid = article.findtext(".//PMID")
        papers.append({"pmid": pmid, "title": title, "abstract": abstract})
    return papers

def extract_rons_data_from_abstract(abstract: str):
    """초록에서 RONS 농도 및 면역 마커 수치 추출 (regex + NLP)"""
    import re
    # RONS 농도 패턴: "NO concentration of 50 μM"
    rons_pattern = r'(NO|OH|O3|H2O2|ONOO|ROS|RNS)\s*(?:concentration|level)?\s*(?:of|=|:)?\s*(\d+\.?\d*)\s*(μM|mM|nM|ppm)'
    rons_matches = re.findall(rons_pattern, abstract, re.IGNORECASE)

    # 면역 마커 변화: "IL-6 decreased by 30%"
    marker_pattern = r'(IL-\d+|TNF-?α?|IgE|CRP|NF-κB)\s*(?:increased|decreased|reduced|elevated)\s*(?:by)?\s*(\d+\.?\d*)\s*(%|fold|pg/mL)'
    marker_matches = re.findall(marker_pattern, abstract, re.IGNORECASE)

    return {"rons": rons_matches, "markers": marker_matches}
```

---

#### 2.D.2 기존 선행연구 데이터 (PI 연구실)

| 항목 | 내용 |
|------|------|
| **데이터명** | PI(이승훈 책임연구원) 기존 플라즈마 실험 데이터 |
| **출처** | KIMS 플라즈마 연구팀 내부 데이터 |
| **관련 논문** | Advanced Science 2022 외 관련 논문 |
| **데이터 항목** | CAP 처리 파라미터 (전압, 주파수, 가스 조성, 처리 시간), RONS 농도 (UV-Vis, EPR), 세포/동물 면역 반응 데이터 |
| **규모** | 실험 세션 ~200-500건 (추정) |
| **ICO 매핑** | `ico:pmo/ColdAtmosphericPlasmaDevice`, `ico:pmo/PlasmaOperatingParameters`, `ico:pmo/RONSSelectivityProfile` |

**데이터 정리 계획:**
1. 기존 실험 노트 및 데이터 파일 인벤토리 작성
2. 표준화된 CSV/JSON 형식으로 변환
3. 각 실험 세션을 ICO 온톨로지 인스턴스로 매핑
4. RONS 선택성 프로파일 (ROS:RNS 비율) 데이터베이스 구축

---

## 3. Tier 2: 자체 센서 데이터 수집 (3-9개월)

### 3.1 IoT 환경 센서 배치 계획

#### 배치 장소 및 규모

| 단계 | 장소 | 센서 세트 수 | 기간 | 대상자 |
|------|------|-----------|------|--------|
| Pilot A | KIMS 연구실 (2실) | 2세트 | 2026.07-09 | 연구원 4명 |
| Pilot B | KIMS 사무실 (3실) | 3세트 | 2026.09-12 | 연구원 6명 |
| 확대 | 자원자 가정 (10가구) | 10세트 | 2027.01-06 | 자원자 10-20명 |

#### 센서 세트 구성 (1세트당)

| 센서 | 모델 | 측정항목 | 가격(추정) | 비고 |
|------|------|---------|---------|------|
| SPS30 | Sensirion SPS30 | PM1.0, PM2.5, PM4.0, PM10 | ~$40 | UART/I2C, 수명 8년 |
| SGP41 | Sensirion SGP41 | VOC Index, NOx Index | ~$10 | 사전 컨디셔닝 필요 |
| SCD41 | Sensirion SCD41 | CO2, 온도, 습도 | ~$50 | NDIR 방식, ±40ppm |
| BME680 | Bosch BME680 | 온도, 습도, 기압, Gas resistance | ~$15 | IAQ 지수 산출 가능 |
| 게이트웨이 | Raspberry Pi 4B (4GB) | 데이터 수집/전송 | ~$60 | Debian OS, Python |
| HAT 보드 | 커스텀 센서보드 | 센서 인터페이스 | ~$30 | I2C 멀티플렉서 |
| 전원 | USB-C 어댑터 | 5V 3A | ~$10 | UPS 배터리 옵션 |

**1세트 총 비용:** ~$215 (약 28만 원)
**15세트 총 비용:** ~$3,225 (약 420만 원)

#### 에지 소프트웨어 스택

```
Raspberry Pi 4B
├── OS: Raspberry Pi OS Lite (64-bit)
├── Runtime: Python 3.11
├── 센서 드라이버
│   ├── sensirion-i2c-sps30 (pip)
│   ├── sensirion-i2c-sgp41 (pip)
│   ├── sensirion-i2c-scd4x (pip)
│   └── bme680 (pip, pimoroni)
├── 데이터 수집: custom collector daemon (systemd)
├── 로컬 저장: SQLite WAL (72h 버퍼)
├── 전송: paho-mqtt (QoS 1)
├── 모니터링: Prometheus node_exporter
└── 원격 관리: SSH + Ansible
```

### 3.2 웨어러블 디바이스 배치 계획

#### 디바이스 선정

| 디바이스 | 측정항목 | SDK/API | 가격(추정) | 선정 사유 |
|---------|---------|---------|---------|---------|
| Galaxy Watch 7 (1차) | HRV, SpO2, 수면, 걸음수, 피부온도 | Samsung Health SDK | ~$300 | 한국 시장 호환성, Health SDK 제공 |
| Oura Ring Gen 3 (보조) | HRV, 수면, 피부온도, 활동 | Oura API (REST) | ~$300 | 착용 순응도 높음, 연속 HRV |
| Fitbit Sense 2 (대안) | HRV, SpO2, EDA, 수면 | Fitbit Web API | ~$200 | 연구 프로그램 지원 |

**파일럿 규모:** 10명 × 6개월 (2026.07-12)
**데이터 수집 프로토콜:**
- 24시간 연속 착용 (샤워/충전 시 제외)
- 최소 착용률 목표: 80% (하루 19.2시간)
- 데이터 동기화: 1일 1회 스마트폰 앱 → 클라우드 → 연구 서버

### 3.3 플라즈마 RONS 측정 데이터 수집 프로토콜

#### 측정 장비

| 측정법 | 장비 | RONS 종 | 정량 범위 | 시간 해상도 |
|--------|------|---------|---------|-----------|
| UV-Vis 분광법 | Ocean Optics HR4000 | O3, NO2, N2O5 | 1-1000 ppm | 0.1초 |
| EPR (전자상자성공명) | Bruker EMXnano | •OH, O2•⁻, NO | μM-mM | 세션별 |
| 형광 프로브 | 형광분광광도계 | ROS 총량 (DCFH-DA) | nM-μM | 분 단위 |
| 화학발광 | Chemiluminescence | NO | ppb-ppm | 초 단위 |

#### 실험 매트릭스

| 변수 | 범위 | 단계 | 조합 수 |
|------|------|------|--------|
| 인가 전압 | 5, 10, 15, 20 kV | 4 | |
| 펄스 주파수 | 1, 10, 50, 100 kHz | 4 | |
| 가스 조성 | Air, He, Ar, He+O2 | 4 | |
| 처리 거리 | 5, 10, 20 mm | 3 | |
| **총 조합** | | | **192** |
| 반복 | 3회/조합 | | **576 세션** |

**세션당 데이터:**
- UV-Vis 스펙트럼: ~100 KB (300초 × 10Hz)
- EPR 스펙트럼: ~50 KB
- 파라미터 로그: ~5 KB
- **총 예상:** 576 × ~155 KB ≈ ~87 MB

### 3.4 데이터 수집 SOP (Standard Operating Procedure)

#### SOP-001: 환경 센서 데이터 수집

| 항목 | 내용 |
|------|------|
| **목적** | 실내 환경 데이터의 표준화된 연속 수집 |
| **적용 범위** | KIMS 내부 센서 배치 및 자원자 가정 배치 |
| **장비** | SPS30 + SGP41 + SCD41 + BME680 + RPi 4B |
| **설치 위치** | 바닥 1.2-1.5m 높이, 직사광선/에어컨 직접 기류 회피, 벽면 30cm 이격 |
| **교정 주기** | SPS30: 6개월 (Sensirion 교정 장비), SCD41: 자동 ASC 활성화 |
| **품질 관리** | 일일 QC: 물리적 범위 점검 (PM2.5: 0-500, CO2: 400-5000), 주간 QC: 센서간 교차검증 |
| **데이터 백업** | 로컬 SQLite (72h) + MQTT → 서버 (중복 저장) |
| **장애 대응** | 게이트웨이 미응답 30분 → Slack 알림, 센서 이상 → 데이터 플래그 |

#### SOP-002: 웨어러블 데이터 수집

| 항목 | 내용 |
|------|------|
| **목적** | 생체 신호 라이프로그의 표준화된 수집 |
| **참여자 교육** | 착용법, 충전법, 데이터 동기화 절차 (30분 교육) |
| **착용 규칙** | 24시간 연속, 충전은 착석 시, 목욕 시 제거 후 즉시 재착용 |
| **데이터 동기화** | 매일 아침 스마트폰 앱 → 클라우드 동기화 확인 |
| **순응도 모니터링** | 주간 착용률 리포트, 80% 미만 시 개별 연락 |
| **탈퇴 기준** | 2주 연속 60% 미만 착용 시 연구 탈퇴 처리 |

#### SOP-003: 플라즈마 RONS 측정

| 항목 | 내용 |
|------|------|
| **목적** | CAP 처리 조건별 RONS 생성 프로파일 표준 측정 |
| **전처리** | 장비 30분 예열, 배경 스펙트럼 측정, 가스 라인 퍼지 |
| **측정 절차** | 1) 파라미터 설정 → 2) 배경 측정(30s) → 3) 플라즈마 점화 → 4) 연속 측정(300s) → 5) 후처리 |
| **데이터 기록** | 자동 로깅 (파라미터+스펙트럼+타임스탬프) → HDF5 파일 |
| **품질 관리** | 표준 가스 (NO 50ppm) 교정 매 측정일, 3회 반복 CV < 10% |

### 3.5 IRB/윤리 승인 요구사항 체크리스트

| # | 항목 | 담당 | 상태 | 기한 |
|---|------|------|------|------|
| 1 | 기관 IRB 신청서 작성 (KIMS 생명윤리위원회) | PI | [ ] | 2026.05 |
| 2 | 연구 참여 동의서 작성 (국/영) | PI + RA | [ ] | 2026.05 |
| 3 | 개인정보영향평가 (PIA) 실시 | PI + 정보보호담당 | [ ] | 2026.06 |
| 4 | 가명처리 절차서 작성 (환자 ID → 연구 ID 매핑) | 데이터매니저 | [ ] | 2026.06 |
| 5 | 데이터관리계획서 (DMP) 작성 | PI + 데이터매니저 | [ ] | 2026.06 |
| 6 | IRB 심의 통과 | IRB | [ ] | 2026.07 |
| 7 | NHIS 데이터 이용 심의 신청 | PI | [ ] | 2026.05 |
| 8 | KoGES 자원분양 신청 | PI | [ ] | 2026.06 |
| 9 | UK Biobank 접근 신청 (Application) | PI | [ ] | 2026.06 |
| 10 | 웨어러블 디바이스 의료기기 해당 여부 검토 | RA | [ ] | 2026.05 |

### 3.6 TimescaleDB 스키마 설계

```sql
-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- 1. 환경 센서 데이터 (하이퍼테이블)
-- ============================================================
CREATE TABLE env_sensor_data (
    time           TIMESTAMPTZ NOT NULL,
    patient_id     TEXT NOT NULL,
    device_id      TEXT NOT NULL,
    location_id    TEXT NOT NULL,
    -- PM
    pm1_0          DOUBLE PRECISION,
    pm2_5          DOUBLE PRECISION,
    pm4_0          DOUBLE PRECISION,
    pm10           DOUBLE PRECISION,
    -- VOC
    voc_index      INTEGER,
    nox_index      INTEGER,
    -- CO2/온습도
    co2_ppm        DOUBLE PRECISION,
    temperature_c  DOUBLE PRECISION,
    humidity_rh    DOUBLE PRECISION,
    -- 기압/가스
    pressure_hpa   DOUBLE PRECISION,
    gas_resistance DOUBLE PRECISION,
    -- 품질 플래그
    qc_flag        SMALLINT DEFAULT 0,  -- 0=OK, 1=suspect, 2=invalid
    PRIMARY KEY (time, patient_id, device_id)
);

SELECT create_hypertable('env_sensor_data', 'time',
    chunk_time_interval => INTERVAL '1 day');

-- 압축 정책 (30일 이상 데이터 자동 압축)
ALTER TABLE env_sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'patient_id, device_id',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('env_sensor_data', INTERVAL '30 days');

-- ============================================================
-- 2. 복합지표 (계산 결과)
-- ============================================================
CREATE TABLE composite_indices (
    time                TIMESTAMPTZ NOT NULL,
    patient_id          TEXT NOT NULL,
    -- 산화스트레스 부하
    osl_value           DOUBLE PRECISION,  -- Oxidative Stress Load (0-1)
    osl_pm25_contrib    DOUBLE PRECISION,
    osl_voc_contrib     DOUBLE PRECISION,
    osl_o3_contrib      DOUBLE PRECISION,
    -- 알레르겐 노출 점수
    aes_value           DOUBLE PRECISION,  -- Allergen Exposure Score (0-1)
    aes_humidity_contrib DOUBLE PRECISION,
    aes_mold_contrib    DOUBLE PRECISION,
    -- 환기 지수
    vi_value            DOUBLE PRECISION,  -- Ventilation Index (0-1)
    vi_co2_decay_rate   DOUBLE PRECISION,
    PRIMARY KEY (time, patient_id)
);

SELECT create_hypertable('composite_indices', 'time',
    chunk_time_interval => INTERVAL '1 day');

-- ============================================================
-- 3. 웨어러블/라이프로그 데이터
-- ============================================================
CREATE TABLE lifelog_data (
    time              TIMESTAMPTZ NOT NULL,
    patient_id        TEXT NOT NULL,
    source_device     TEXT NOT NULL,
    -- HRV
    hrv_rmssd_ms      DOUBLE PRECISION,
    hrv_sdnn_ms       DOUBLE PRECISION,
    -- SpO2
    spo2_pct          DOUBLE PRECISION,
    -- 수면
    sleep_stage       TEXT,           -- 'deep', 'light', 'rem', 'awake'
    sleep_duration_min INTEGER,
    -- 활동
    steps             INTEGER,
    mets              DOUBLE PRECISION,
    -- 피부온도
    skin_temp_c       DOUBLE PRECISION,
    -- 착용 상태
    wearing_status    BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (time, patient_id, source_device)
);

SELECT create_hypertable('lifelog_data', 'time',
    chunk_time_interval => INTERVAL '1 day');

-- ============================================================
-- 4. 바이오마커 데이터
-- ============================================================
CREATE TABLE biomarker_data (
    time           TIMESTAMPTZ NOT NULL,
    patient_id     TEXT NOT NULL,
    assay_method   TEXT NOT NULL,     -- 'ELISA', 'SERS', 'blood_panel'
    loinc_code     TEXT,              -- LOINC 코드
    -- 사이토카인 (pg/mL)
    il6            DOUBLE PRECISION,
    tnf_alpha      DOUBLE PRECISION,
    il4            DOUBLE PRECISION,
    il10           DOUBLE PRECISION,
    il13           DOUBLE PRECISION,
    il5            DOUBLE PRECISION,
    il17           DOUBLE PRECISION,
    -- 알레르기/전신
    ige_total      DOUBLE PRECISION,  -- IU/mL
    crp            DOUBLE PRECISION,  -- mg/L
    -- 산화 손상
    ohdg_8         DOUBLE PRECISION,  -- ng/mL
    mda            DOUBLE PRECISION,  -- nmol/mL
    -- 면역세포 (cells/μL)
    wbc            DOUBLE PRECISION,
    eosinophil     DOUBLE PRECISION,
    neutrophil     DOUBLE PRECISION,
    lymphocyte     DOUBLE PRECISION,
    -- Th1/Th2 비율
    th1_th2_ratio  DOUBLE PRECISION,
    PRIMARY KEY (time, patient_id, assay_method)
);

SELECT create_hypertable('biomarker_data', 'time',
    chunk_time_interval => INTERVAL '30 days');

-- ============================================================
-- 5. 플라즈마 치료 세션 데이터
-- ============================================================
CREATE TABLE plasma_treatment_sessions (
    session_id        TEXT PRIMARY KEY,
    time_start        TIMESTAMPTZ NOT NULL,
    time_end          TIMESTAMPTZ,
    patient_id        TEXT,           -- NULL for in-vitro experiments
    experiment_type   TEXT NOT NULL,  -- 'in_vitro', 'animal', 'clinical'
    -- 장비 파라미터
    device_model      TEXT,
    voltage_kv        DOUBLE PRECISION,
    pulse_freq_khz    DOUBLE PRECISION,
    gas_composition   TEXT,           -- 'Air', 'He', 'Ar', 'He+O2'
    gas_flow_slm      DOUBLE PRECISION,
    treatment_dist_mm DOUBLE PRECISION,
    treatment_dur_sec DOUBLE PRECISION,
    -- RONS 결과
    rons_o3_ppm       DOUBLE PRECISION,
    rons_no_ppm       DOUBLE PRECISION,
    rons_no2_ppm      DOUBLE PRECISION,
    rons_oh_um        DOUBLE PRECISION,
    rons_h2o2_um      DOUBLE PRECISION,
    rons_onoo_um      DOUBLE PRECISION,
    ros_total         DOUBLE PRECISION,
    rns_total         DOUBLE PRECISION,
    ros_rns_ratio     DOUBLE PRECISION,
    -- 스펙트럼 원시 데이터 참조
    uvvis_hdf5_path   TEXT,
    epr_hdf5_path     TEXT
);

-- ============================================================
-- 6. 외부 공공 데이터 (AirKorea, KMA 캐시)
-- ============================================================
CREATE TABLE external_airkorea (
    time           TIMESTAMPTZ NOT NULL,
    station_code   TEXT NOT NULL,
    station_name   TEXT,
    sido           TEXT,
    pm25           DOUBLE PRECISION,
    pm10           DOUBLE PRECISION,
    o3             DOUBLE PRECISION,
    no2            DOUBLE PRECISION,
    so2            DOUBLE PRECISION,
    co             DOUBLE PRECISION,
    PRIMARY KEY (time, station_code)
);

SELECT create_hypertable('external_airkorea', 'time',
    chunk_time_interval => INTERVAL '1 day');

CREATE TABLE external_kma (
    time           TIMESTAMPTZ NOT NULL,
    station_id     TEXT NOT NULL,
    temperature_c  DOUBLE PRECISION,
    humidity_rh    DOUBLE PRECISION,
    pressure_hpa   DOUBLE PRECISION,
    wind_speed_ms  DOUBLE PRECISION,
    precipitation  DOUBLE PRECISION,
    solar_mj       DOUBLE PRECISION,
    uv_index       DOUBLE PRECISION,
    PRIMARY KEY (time, station_id)
);

SELECT create_hypertable('external_kma', 'time',
    chunk_time_interval => INTERVAL '1 day');

-- ============================================================
-- 7. 환자/참여자 정보 (일반 테이블, 비시계열)
-- ============================================================
CREATE TABLE participants (
    patient_id        TEXT PRIMARY KEY,
    enrollment_date   DATE NOT NULL,
    age               INTEGER,
    sex               TEXT,
    bmi               DOUBLE PRECISION,
    smoking_status    TEXT,
    allergy_family_hx BOOLEAN,
    atopy_score       DOUBLE PRECISION,
    residence_region  TEXT,
    nearest_airkorea  TEXT,           -- 가장 가까운 AirKorea 측정소
    nearest_kma       TEXT,           -- 가장 가까운 KMA 측정소
    consent_signed    BOOLEAN DEFAULT FALSE,
    irb_approval_id   TEXT
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX idx_env_patient ON env_sensor_data (patient_id, time DESC);
CREATE INDEX idx_lifelog_patient ON lifelog_data (patient_id, time DESC);
CREATE INDEX idx_biomarker_patient ON biomarker_data (patient_id, time DESC);
CREATE INDEX idx_airkorea_station ON external_airkorea (station_code, time DESC);

-- ============================================================
-- 연속 집계 (Continuous Aggregate) — 일일 요약
-- ============================================================
CREATE MATERIALIZED VIEW daily_env_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    patient_id,
    AVG(pm2_5) AS pm25_mean,
    MAX(pm2_5) AS pm25_max,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY pm2_5) AS pm25_p95,
    AVG(voc_index) AS voc_mean,
    MAX(voc_index) AS voc_max,
    AVG(co2_ppm) AS co2_mean,
    MAX(co2_ppm) AS co2_max,
    AVG(temperature_c) AS temp_mean,
    AVG(humidity_rh) AS humidity_mean,
    MAX(humidity_rh) AS humidity_max,
    COUNT(*) AS n_observations
FROM env_sensor_data
WHERE qc_flag = 0
GROUP BY day, patient_id;

SELECT add_continuous_aggregate_policy('daily_env_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

---

## 4. Tier 3: 협력 기관 데이터 (9-24개월)

### 4.1 창원대 박인규 교수 연구팀 — 유전자 분석 데이터

| 항목 | 내용 |
|------|------|
| **협력 단계** | 2단계 (2028-01 ~ 2029-12) |
| **데이터 유형** | 면역 관련 유전자 발현 데이터 (RNA-seq, qPCR), SNP 분석 |
| **대상** | 면역질환 환자/건강대조군 혈액 샘플 (50-100명) |
| **핵심 변수** | IL-6, TNF-α, IL-4, IL-13, IL-10 mRNA 발현, Th1/Th2 관련 전사인자, NF-κB 활성화 마커 |
| **예상 규모** | RNA-seq: 100 샘플 × ~20,000 유전자, qPCR: 200 샘플 × 30 유전자 |
| **ICO 매핑** | `ico:trajectory/CausalPathway` (유전자 발현 레이어), 모델 피처 `genetic_risk_score` (Layer 7, #103) |
| **데이터 표준** | FASTQ → BAM → Count matrix (DESeq2 표준 분석 파이프라인) |

### 4.2 경북의대 김상현 교수 연구팀 — 면역질환 동물모델/임상 데이터

| 항목 | 내용 |
|------|------|
| **협력 단계** | 3단계 (2030-01 ~ 2033-12), 일부 2단계 예비 공동연구 |
| **데이터 유형** | 면역질환 동물모델 (마우스) 실험 데이터, 향후 소규모 임상 파일럿 |
| **동물 모델** | OVA-유도 천식, DNCB-유도 아토피피부염, IMQ-유도 건선 마우스 |
| **측정 항목** | 혈청 사이토카인 (Luminex), 조직 면역조직화학, 피부/폐 병리소견 점수, RONS 노출 후 면역 변화 |
| **예상 규모** | 동물: 200-500마리 (5-10 실험), 임상: 30-50명 파일럿 |
| **ICO 매핑** | `ico:pmo/PlasmaImmuneModulation` (RONS→면역 조절 in vivo 검증), `ico:pmo/HormesisResponse` (용량-반응 곡선) |

### 4.3 Q-solutions (창업기업) — 실내환경 SaaS 데이터

| 항목 | 내용 |
|------|------|
| **협력 단계** | 1-2단계 (지속) |
| **데이터 유형** | 상용 실내공기질 모니터링 SaaS 데이터 |
| **측정 항목** | PM2.5, PM10, CO2, VOC, 온도, 습도 (다양한 시설) |
| **예상 규모** | 수백-수천 개 시설, 수백만 시계열 포인트 |
| **ICO 매핑** | `ico:envimmune/EnvironmentalExposureEvent` (대규모 실내환경 인스턴스), `ico:envimmune/VentilationIndex` (환기 패턴 분석) |
| **데이터 특성** | 비식별화된 시설 ID, 개인 건강 데이터 미포함 → IRB 불필요 가능성 |

### 4.4 데이터 공유 계약 (DTA) 체크리스트

| # | 항목 | 내용 |
|---|------|------|
| 1 | **데이터 범위** | 공유 데이터 항목, 기간, 대상자 수 명확 정의 |
| 2 | **사용 목적** | "면역 케어 온톨로지 연구 및 AI 모델 학습" 명시 |
| 3 | **접근 권한** | 접근 가능 연구원 명단, 접근 방식 (원격/반출) |
| 4 | **비식별화** | k-anonymity (k≥5), 준식별자 일반화/삭제 절차 |
| 5 | **보관 기간** | 연구 종료 후 데이터 파기 시점 (보통 5년) |
| 6 | **재공유 금지** | 제3자 공유 불가 조항 |
| 7 | **지적재산권** | 파생 데이터/모델의 IP 귀속 (공동 귀속 원칙) |
| 8 | **성과 공유** | 공동 논문 저자권 조건 |
| 9 | **보안 요구사항** | 암호화(전송/저장), 접근 감사 로그, VPN |
| 10 | **위반 시 조치** | 계약 해지, 데이터 반환/파기, 법적 책임 |

### 4.5 OMOP CDM 매핑

모든 임상/건강 데이터는 OMOP CDM (v5.4)으로 표준화한다.

| OMOP 테이블 | 매핑 소스 | ICO 클래스 |
|------------|---------|----------|
| `PERSON` | NHIS 자격DB, 참여자 등록 | `ico:participants` |
| `CONDITION_OCCURRENCE` | NHIS 진료DB (ICD-10), 동물모델 표현형 | `ico:trajectory/DiseaseTrajectory` |
| `MEASUREMENT` | KNHANES/KoGES 바이오마커, 자체 ELISA | `ico:biomarker` → OBI measurement |
| `OBSERVATION` | 설문, 자가보고, 환경 노출 | `ico:envimmune/EnvironmentalExposureEvent` |
| `DEVICE_EXPOSURE` | 웨어러블 착용, 플라즈마 치료 | `ico:lifelog/WearableDevice`, `ico:pmo/ColdAtmosphericPlasmaDevice` |
| `DRUG_EXPOSURE` | NHIS 처방DB | 면역억제제/스테로이드 사용 이력 |
| `PROCEDURE_OCCURRENCE` | 플라즈마 치료 세션 | `ico:pmo/TreatmentProtocol` |

**OMOP 어휘 매핑 예시:**

| 원천 코드 | OMOP Concept ID | Concept Name | 도메인 |
|---------|----------------|--------------|--------|
| ICD-10 L20 | 201820 | Atopic dermatitis | Condition |
| ICD-10 J45 | 317009 | Asthma | Condition |
| ICD-10 J30 | 257007 | Allergic rhinitis | Condition |
| ICD-10 L40 | 140168 | Psoriasis | Condition |
| LOINC 1988-5 | 3020460 | CRP [Mass/volume] in Serum | Measurement |
| LOINC 26881-3 | 3000905 | IL-6 [Mass/volume] in Serum | Measurement |

---

## 5. 데이터별 온톨로지 인스턴스 매핑 상세

### 5.1 데이터 소스 → ICO 클래스 매핑 테이블

| ICO 모듈 | ICO 클래스 | Tier 1 데이터 소스 | Tier 2 데이터 소스 | Tier 3 데이터 소스 | 예상 인스턴스 수 |
|---------|----------|-----------------|-----------------|-----------------|-------------|
| **EnvImmune** | `EnvironmentalExposureEvent` | AirKorea, KMA, EPA AQS, 실내공기질 | IoT 센서 (SPS30, SGP41, SCD41, BME680) | Q-solutions SaaS | ~5,000만+ |
| **EnvImmune** | `OxidativeStressLoad` | AirKorea PM2.5+O3 기반 계산 | IoT 센서 실시간 계산 | — | ~500만 |
| **EnvImmune** | `AllergenExposureScore` | KMA 습도 데이터 기반 계산 | IoT 센서 (BME680 습도) | — | ~500만 |
| **EnvImmune** | `VentilationIndex` | 실내공기질 CO2 데이터 | IoT 센서 (SCD41 CO2) | Q-solutions | ~200만 |
| **EnvImmune** | `ExposureImmunePath` | CTD, Reactome | 문헌 마이닝 | 창원대 유전자 발현 | ~1,000 |
| **Lifelog** | `LifelogObservation` | — | 웨어러블 (Galaxy Watch) | — | ~100만 |
| **Lifelog** | `HRVMeasurement` | UK Biobank (93K 가속도계) | 웨어러블 | — | ~50만 |
| **Lifelog** | `SleepQualityAssessment` | KNHANES 수면 설문 | 웨어러블 수면 추적 | — | ~10만 |
| **Lifelog** | `ActivityLevel` | KNHANES 신체활동, UK Biobank | 웨어러블 걸음수/METs | — | ~30만 |
| **Trajectory** | `DiseaseTrajectory` | NHIS 100만 코호트 ICD-10 | — | 경북의대 임상 | ~20만 |
| **Trajectory** | `AllergicMarchProgression` | NHIS 알레르기 마치 패턴 | — | — | ~2-5만 |
| **Trajectory** | `ImmuneRiskScore` | KoGES 유전체+환경 | 자체 모델 예측값 | — | ~21만 |
| **Trajectory** | `CausalPathway` | CTD, Reactome, GO | 자체 실험 검증 | 공동연구 검증 | ~200 |
| **Trajectory** | `TrajectoryPrediction` | — | TFT 모델 출력 | — | ~모델 추론 시 |
| **PMO** | `ColdAtmosphericPlasmaDevice` | — | KIMS 자체 장비 | — | ~5-10 |
| **PMO** | `PlasmaOperatingParameters` | 문헌 마이닝 | 자체 실험 | — | ~1,000 |
| **PMO** | `RONSGeneration` | 문헌 마이닝 | UV-Vis/EPR 측정 | 경북의대 공동 | ~2,000 |
| **PMO** | `RONSSelectivityProfile` | 문헌 마이닝 | 자체 실험 | — | ~500 |
| **PMO** | `PlasmaImmuneModulation` | 문헌 마이닝 | — | 경북의대 동물모델 | ~500 |
| **PMO** | `HormesisResponse` | 문헌 마이닝 | 자체 실험 | 경북의대 동물모델 | ~200 |

### 5.2 Gap Analysis: 데이터 수집 후 미충족 예상 클래스

| ICO 클래스 | 현재 충족 상태 | Gap 원인 | 해소 전략 |
|----------|------------|--------|---------|
| `TrajectoryPrediction` | 미충족 (모델 미구축) | TFT 모델 학습 필요 | 1단계 후반 모델 학습 후 생성 |
| `HormesisResponse` | 부분 충족 (문헌 수준) | in vivo 데이터 부족 | 3단계 동물/임상 실험으로 채움 |
| `PlasmaImmuneModulation` | 부분 충족 (문헌 수준) | 자체 in vivo 미수행 | 2-3단계 동물모델 PoC |
| `genetic_risk_score` (피처 #103) | 미충족 | 유전체 데이터 2단계 | KoGES GWAS 활용 → 2단계 창원대 협업 |
| SERS 연속 바이오마커 | 미충족 | 장비 개발 중 | 1단계 PoC → 2단계 실용화 |

---

## 6. 데이터 수집 자동화 파이프라인

### 6.1 Cron Job 설계 — 주기적 공개 데이터 수집

```python
# Apache Airflow DAG 정의
# 파일: dags/public_data_collection.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'ico-pipeline',
    'depends_on_past': False,
    'email': ['shlee@kims.re.kr'],
    'email_on_failure': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# ============================================================
# DAG 1: AirKorea 시간별 수집 (매 정각 +5분)
# ============================================================
dag_airkorea = DAG(
    'airkorea_hourly',
    default_args=default_args,
    description='AirKorea 대기질 시간 데이터 수집',
    schedule_interval='5 * * * *',  # 매시 5분
    start_date=days_ago(1),
    catchup=False,
    tags=['tier1', 'environment'],
)

def collect_airkorea(**kwargs):
    """에어코리아 전국 측정소 데이터 수집 → TimescaleDB"""
    from collectors.airkorea import AirKoreaCollector
    collector = AirKoreaCollector(api_key=Variable.get("AIRKOREA_API_KEY"))
    stations = ["창원", "부산", "서울"]  # 연구 관련 측정소
    for station in stations:
        data = collector.fetch_realtime(station)
        collector.insert_to_db(data, table="external_airkorea")

collect_task = PythonOperator(
    task_id='collect_airkorea_data',
    python_callable=collect_airkorea,
    dag=dag_airkorea,
)

# ============================================================
# DAG 2: KMA 기상 시간별 수집 (매 정각 +10분)
# ============================================================
dag_kma = DAG(
    'kma_hourly',
    default_args=default_args,
    description='기상청 시간 기상 데이터 수집',
    schedule_interval='10 * * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['tier1', 'environment'],
)

# ============================================================
# DAG 3: 일일 배치 처리 (매일 새벽 02:00)
# ============================================================
dag_daily = DAG(
    'daily_batch_processing',
    default_args=default_args,
    description='일일 데이터 집계, 복합지표 계산, QC',
    schedule_interval='0 2 * * *',  # 매일 02:00 KST
    start_date=days_ago(1),
    catchup=False,
    tags=['processing'],
)

def compute_daily_features(**kwargs):
    """일일 피처 계산 (TFT 모델 입력용 114D)"""
    from processors.feature_engine import FeatureEngine
    engine = FeatureEngine()
    # 7일 rolling window 피처 계산
    engine.compute_env_features_7d()      # Layer 1: 30D
    engine.compute_composite_indices_7d() # Layer 2: 15D
    engine.compute_lifelog_features_7d()  # Layer 3: 20D
    engine.compute_cross_features()       # Layer 8: 10D

def run_data_quality_checks(**kwargs):
    """일일 데이터 품질 검사"""
    from quality.qc_engine import QCEngine
    qc = QCEngine()
    report = qc.run_daily_checks()
    if report.has_critical_issues:
        qc.send_alert(channel="slack", severity="critical")

compute_task = PythonOperator(
    task_id='compute_daily_features',
    python_callable=compute_daily_features,
    dag=dag_daily,
)

qc_task = PythonOperator(
    task_id='data_quality_checks',
    python_callable=run_data_quality_checks,
    dag=dag_daily,
)

compute_task >> qc_task
```

### 6.2 ETL 파이프라인: 원시 데이터 → 온톨로지 인스턴스

```
[원시 데이터]                    [정제]                      [온톨로지 인스턴스]

AirKorea JSON ─┐               ┌── 결측치 처리 ──┐         ┌── OWL 인스턴스 생성 ──┐
KMA JSON ──────┤               │   이상값 플래그   │         │  (RDFLib + OWL-RL)   │
IoT MQTT ──────┤  → Ingestion  │   시간 정렬      │  → RDF  │  SPARQL INSERT       │
Wearable API ──┤    Layer      │   단위 변환      │  Mapper │  트리플 저장          │
ELISA LIMS ────┤               │   정규화         │         │  (Apache Jena /      │
Plasma HDF5 ───┘               └──────────────────┘         │   GraphDB)           │
                                                            └──────────────────────┘
```

**온톨로지 인스턴스 생성 코드 예시:**

```python
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL
import pandas as pd

# 네임스페이스 정의
ICO = Namespace("http://purl.org/ico/")
ENVIMM = Namespace("http://purl.org/ico/envimmune/")
LIFELOG = Namespace("http://purl.org/ico/lifelog/")
TRAJ = Namespace("http://purl.org/ico/trajectory/")
PMO = Namespace("http://purl.org/ico/pmo/")
OBO = Namespace("http://purl.obolibrary.org/obo/")

def create_env_exposure_instance(g: Graph, row: pd.Series) -> URIRef:
    """환경 노출 이벤트 온톨로지 인스턴스 생성"""
    event_uri = ENVIMM[f"exposure_{row['patient_id']}_{row['time'].strftime('%Y%m%d%H%M')}"]

    g.add((event_uri, RDF.type, ENVIMM.EnvironmentalExposureEvent))
    g.add((event_uri, ENVIMM.hasParticipant, ICO[f"patient/{row['patient_id']}"]))
    g.add((event_uri, ENVIMM.hasTimepoint,
           Literal(row['time'].isoformat(), datatype=XSD.dateTime)))

    # PM2.5 측정값
    if pd.notna(row.get('pm2_5')):
        pm25_node = BNode()
        g.add((event_uri, ENVIMM.hasMeasurement, pm25_node))
        g.add((pm25_node, RDF.type, OBO.ENVO_01000796))  # particulate matter
        g.add((pm25_node, ENVIMM.hasValue,
               Literal(row['pm2_5'], datatype=XSD.double)))
        g.add((pm25_node, ENVIMM.hasUnit, Literal("ug/m3")))

    # VOC Index
    if pd.notna(row.get('voc_index')):
        voc_node = BNode()
        g.add((event_uri, ENVIMM.hasMeasurement, voc_node))
        g.add((voc_node, RDF.type, OBO.CHEBI_134179))  # volatile organic compound
        g.add((voc_node, ENVIMM.hasValue,
               Literal(row['voc_index'], datatype=XSD.integer)))

    return event_uri

def create_disease_trajectory_instance(g: Graph, patient_id: str,
                                         diagnoses: pd.DataFrame) -> URIRef:
    """질병 궤적 온톨로지 인스턴스 생성"""
    traj_uri = TRAJ[f"trajectory/{patient_id}"]
    g.add((traj_uri, RDF.type, TRAJ.DiseaseTrajectory))
    g.add((traj_uri, TRAJ.hasSubject, ICO[f"patient/{patient_id}"]))

    for idx, dx in diagnoses.iterrows():
        stage_uri = TRAJ[f"stage/{patient_id}/{idx}"]
        g.add((traj_uri, TRAJ.hasStage, stage_uri))
        g.add((stage_uri, RDF.type, TRAJ.TrajectoryStage))
        g.add((stage_uri, TRAJ.hasDiagnosis,
               OBO[f"DOID_{icd10_to_doid(dx['icd_code'])}"]))
        g.add((stage_uri, TRAJ.hasOnsetDate,
               Literal(dx['diag_date'], datatype=XSD.date)))

    return traj_uri

def batch_generate_rdf(env_data: pd.DataFrame, output_path: str):
    """배치 RDF 생성 및 파일 저장"""
    g = Graph()
    g.bind("ico", ICO)
    g.bind("envimm", ENVIMM)
    g.bind("traj", TRAJ)
    g.bind("obo", OBO)

    for _, row in env_data.iterrows():
        create_env_exposure_instance(g, row)

    g.serialize(destination=output_path, format="turtle")
    print(f"Generated {len(g)} triples → {output_path}")
```

### 6.3 데이터 품질 모니터링 대시보드 컨셉

| 패널 | 모니터링 항목 | 알림 기준 |
|------|------------|---------|
| **수집 현황** | 데이터 소스별 수집 건수/시간, 지연 시간 | 1시간 미수집 시 경고 |
| **완전성** | 센서별 결측률 (%), 착용률 (%) | 결측률 > 20% 시 경고 |
| **정확성** | 센서 교차 검증 (실내 vs 외부 PM2.5 상관) | 상관계수 < 0.3 시 경고 |
| **적시성** | API 응답 시간, 데이터 최신성 | 응답 > 30초 시 경고 |
| **일관성** | 센서 간 drift 모니터링 (같은 실내 2대 비교) | 편차 > 20% 시 교정 알림 |
| **용량** | DB 저장 용량, 테이블별 행 수, 압축률 | 디스크 80% 시 경고 |
| **온톨로지** | 클래스별 인스턴스 수, 트리플 수, SPARQL 응답 시간 | — |

**구현 도구:** Grafana + TimescaleDB 직접 연결 (Prometheus for system metrics)

### 6.4 데이터셋 버전 관리 (DVC)

```bash
# DVC 초기화
pip install dvc dvc-s3
dvc init

# 데이터 디렉토리 추적
dvc add data/raw/airkorea/
dvc add data/raw/kma/
dvc add data/raw/nhis/
dvc add data/processed/features/
dvc add data/ontology/instances/

# 원격 저장소 설정 (S3 호환 — MinIO or NAS)
dvc remote add -d kims_storage s3://ico-data-store
dvc remote modify kims_storage endpointurl http://nas.kims.internal:9000

# 버전 태그
git tag -a "data-v0.1-airkorea-5yr" -m "AirKorea 5년치 (2021-2025) 원시 데이터"
dvc push

# 데이터 파이프라인 정의
# dvc.yaml
# stages:
#   collect_airkorea:
#     cmd: python src/collectors/airkorea.py --year 2025
#     deps: [src/collectors/airkorea.py]
#     outs: [data/raw/airkorea/2025/]
#   process_features:
#     cmd: python src/processors/feature_engine.py
#     deps: [src/processors/feature_engine.py, data/raw/]
#     outs: [data/processed/features/]
#   generate_rdf:
#     cmd: python src/ontology/instance_generator.py
#     deps: [src/ontology/instance_generator.py, data/processed/]
#     outs: [data/ontology/instances/]
```

---

## 7. 데이터 수집 로드맵 (간트 차트)

### 1단계 월별 계획 (2026.04 - 2027.12)

```
2026                                          2027
  04  05  06  07  08  09  10  11  12  01  02  03  04  05  06  07  08  09  10  11  12
  |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |

Tier 1: 공개 데이터
├─ AirKorea API 세팅/수집 시작
  [====]
├─ KMA API 세팅/수집 시작
  [====]
├─ NHIS 코호트 신청/승인
  [============]····[===승인===]
├─ NHIS 데이터 분석
                         [=================]
├─ KoGES 신청/승인/분석
      [========]····[===승인===][==========]
├─ KNHANES 다운로드/분석
  [====][====]
├─ CTD/Reactome/GO 다운로드
  [====]
├─ 문헌 마이닝 (PubMed)
  [====][====][==========================================================]
├─ UK Biobank 신청
      [============]····················[===승인===][====================]
├─ EPA AQS 다운로드
      [====]

Tier 2: 자체 센서
├─ IRB 신청/승인
      [========]····[=승인=]
├─ 센서 장비 구매/조립
          [========]
├─ Pilot A (KIMS 연구실 2실)
                  [============]
├─ Pilot B (KIMS 사무실 3실)
                          [============]
├─ 웨어러블 파일럿 (10명)
                  [========================]
├─ 가정 확대 배치 (10가구)
                                      [================================]
├─ 플라즈마 RONS 실험
          [====][====][====][====][====][====][====][====][====][====]
├─ TimescaleDB 구축
      [========]
├─ ETL 파이프라인 구축
      [============]
├─ 데이터 품질 대시보드
              [========]

Tier 3: 협력기관 준비
├─ Q-solutions 데이터 공유 협의
                  [========]
├─ 창원대 박인규 교수 공동연구 협의
                                                              [========]
├─ 경북의대 예비 협의
                                                                      [========]

모델 학습
├─ TFT 프로토타입 (공개데이터)
                          [============]
├─ TFT v0.2 (센서 데이터 포함)
                                              [============]
├─ TFT v0.5 (1단계 전체 데이터)
                                                                  [============]

마일스톤
  M1: MVD-1                 M2: MVD-2                           M3: MVD-3         M4
  (공개데이터 통합)          (파일럿 완료)                        (확대 데이터)      (1단계)
  ▼                         ▼                                   ▼                 ▼
  07                        12                                  06                12
```

### 주요 마일스톤

| 마일스톤 | 시점 | 달성 기준 | 데이터 규모 목표 |
|---------|------|---------|-------------|
| **M1: MVD-1** | 2026.07 | AirKorea+KMA API 운영, KNHANES 분석 완료, CTD/Reactome 통합 | 환경 데이터 ~1억 레코드, 건강 데이터 ~20만 레코드 |
| **M2: MVD-2** | 2026.12 | 센서 파일럿 완료, 웨어러블 6개월 데이터, TFT 프로토타입 | 10명 × 90일 센서+웨어러블 시계열 |
| **M3: MVD-3** | 2027.06 | 가정 확대 배치 운영, NHIS 분석 진행, TFT v0.2 | 50명 × 180일, NHIS 100만 코호트 |
| **M4: 1단계 완료** | 2027.12 | 전체 파이프라인 검증, TFT v0.5 AUC≥0.75, ICO v1.0 | 100명 × 365일, 온톨로지 인스턴스 >100만 |

### 데이터 소스 간 의존성

```
AirKorea API ──────┐
KMA API ───────────┤
                   ├──→ 복합지표 계산 (OSL, AES, VI) ──→ TFT 피처 Layer 2
IoT 센서 (Tier 2) ─┘

NHIS 코호트 ───────────→ 질병 궤적 추출 ──→ TFT 학습 레이블 (7개 질환)
                                            │
KNHANES ───────────────→ 바이오마커 참조범위 ──→ 정규화 기준
                                            │
KoGES ─────────────────→ 유전적 위험 점수 ──→ TFT 피처 Layer 7 (#103)

CTD + Reactome + GO ───→ 인과 경로 구축 ──→ TFT Attention Prior 행렬

문헌 마이닝 ────────────→ RONS-면역 데이터 ──→ PMO 온톨로지 인스턴스
```

---

## 8. 최소 필요 데이터 규모 산정

### 8.1 인과 경로별 관측치 (통계적 검정력 분석)

**기본 가정:**
- 유의수준 α = 0.05 (양측검정)
- 검정력 1-β = 0.80
- 효과 크기(Effect Size): 도메인 분석서의 상관계수(r) 기반

| 인과 경로 | 보고된 r | 시간 지연(lag) | 필요 관측치 (n) | 데이터 소스 | 확보 가능성 |
|---------|---------|------------|-------------|---------|---------|
| PM2.5 → ROS → NF-κB → IL-6 | r=0.52 | 6-24h | n=28 (상관분석) / n=200 (시계열) | AirKorea + ELISA | 높음 |
| VOCs → 상피장벽 파괴 → Th2 → IgE | r=0.35 | weeks | n=62 / n=400 | SGP41 + ELISA | 중간 |
| 습도 → 진드기 → Der p1 → IL-13 | r=0.30 | days | n=85 / n=500 | BME680 + ELISA | 중간 |
| HRV ↔ IL-6 | r=-0.42 | hours | n=44 / n=250 | 웨어러블 + ELISA | 높음 |
| SpO2 ↔ CRP | r=-0.35 | hours | n=62 / n=350 | 웨어러블 + ELISA | 높음 |
| 수면질 ↔ TNF-α | r=-0.38 | days | n=53 / n=300 | 웨어러블 + ELISA | 높음 |
| 활동량 ↔ TNF-α | r=-0.28 | days | n=99 / n=500 | 웨어러블 + ELISA | 높음 |
| 피부온도 ↔ 일주기 리듬 | r=0.31 | hours | n=80 / n=450 | 웨어러블 | 높음 |
| PM2.5 → 아토피피부염 (L20) | HR~1.10 | months | n=5,000 (코호트) | NHIS + AirKorea | 높음 |
| PM2.5 → 천식 (J45) | HR~1.15 | months | n=3,500 (코호트) | NHIS + AirKorea | 높음 |
| PM2.5 → 알레르기비염 (J30) | HR~1.08 | months | n=8,000 (코호트) | NHIS + AirKorea | 높음 |
| RONS → NF-κB 활성화 | dose-response | minutes | n=30 (in vitro) | 자체 실험 | 높음 |
| RONS → IL-10 증가 (항염증) | dose-response | hours | n=30 (in vitro) | 자체 실험 | 높음 |
| RONS → Nrf2/Keap1 경로 | dose-response | hours | n=30 (in vitro) | 자체 실험 | 높음 |
| CAP → 호르메시스 (저용량 자극) | U-shape | hours | n=50 (다중 용량) | 자체 실험 | 중간 |

**통계적 검정력 계산 공식:**

```python
from scipy import stats
import math

def required_sample_size_correlation(r: float, alpha: float = 0.05,
                                       power: float = 0.80) -> int:
    """상관분석을 위한 최소 표본 크기 (Fisher's z 변환)"""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    z_r = 0.5 * math.log((1 + abs(r)) / (1 - abs(r)))  # Fisher's z
    n = ((z_alpha + z_beta) / z_r) ** 2 + 3
    return math.ceil(n)

def required_sample_size_cox(hr: float, event_rate: float = 0.10,
                              alpha: float = 0.05, power: float = 0.80) -> int:
    """생존분석(Cox regression)을 위한 최소 이벤트 수 (Schoenfeld)"""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    d = ((z_alpha + z_beta) ** 2) / (math.log(hr) ** 2)  # 필요 이벤트 수
    n = d / event_rate  # 전체 표본 크기
    return math.ceil(n)

# 예시
print(f"PM2.5→IL-6 (r=0.52): n={required_sample_size_correlation(0.52)}")
# 출력: n=28
print(f"PM2.5→천식 (HR=1.15, event_rate=0.05): n={required_sample_size_cox(1.15, 0.05)}")
# 출력: n=약 7,600
```

### 8.2 TFT 모델 학습 최소 데이터

**모델 규모 기준 (model_architecture.md 참조):**
- 입력: 114 시계열 차원 + 8 정적 변수 = 122D
- Lookback window: 90일
- 예측 수평선: 4개 (1일, 1주, 1개월, 3개월)
- 출력: 7개 질환 × 4개 수평선 = 28 출력 뉴런 + ImmuneRiskScore

| 요소 | 최소 요구량 | 권장량 | 산정 근거 |
|------|---------|--------|---------|
| **전체 학습 샘플 수** | 5,000명 × 90일 = 450K 시퀀스 | 20,000명 × 90일 | 10× 파라미터 수 규칙 (~500K params) |
| **질환당 양성 레이블** | 500명 이상 | 2,000명 이상 | Multi-task 학습 시 class imbalance 고려 |
| **시계열 길이** | 90일 (lookback) | 365일+ | Temporal attention 학습 충분성 |
| **검증 세트** | 전체의 15% (750명) | 전체의 15% | Stratified by disease |
| **테스트 세트** | 전체의 15% (750명) | 전체의 15% | Hold-out, unseen patients |
| **환경 센서 해상도** | 일별 집계 | 시간별 원시 보존 | 7일 rolling 피처 계산용 |

**단계별 데이터 확보 전략:**

| 단계 | 데이터 소스 | 환자 수 | 시계열 길이 | 모델 용도 |
|------|---------|--------|---------|---------|
| **프로토타입 (2026.Q3)** | NHIS + AirKorea (환경-질환 상관만) | 100K (NHIS 코호트 일부) | 연 단위 | 기준선 로지스틱 회귀, 피처 선별 |
| **TFT v0.1 (2026.Q4)** | Pilot 센서 + 웨어러블 10명 | 10 | 90일 | 파이프라인 검증, 과적합 확인 |
| **TFT v0.2 (2027.Q1)** | 센서 확대 + NHIS 전체 | 100K + 50 | 180일 | Transfer learning, 코호트→개인 |
| **TFT v0.5 (2027.Q4)** | 전체 Tier 1+2 | 100K + 100 | 365일 | AUC ≥ 0.75 목표 |

### 8.3 온톨로지 검증 최소 인스턴스

| ICO 모듈 | 최소 인스턴스/클래스 | 검증 기준 | 비고 |
|---------|---------------|---------|------|
| **EnvImmune** (5 클래스) | 100개/클래스 | SPARQL 쿼리 정상 작동, 추론 일관성 | Tier 1 즉시 충족 가능 |
| **Lifelog** (5 클래스) | 50개/클래스 | Open mHealth 스키마 호환성 | Tier 2 파일럿으로 충족 |
| **ImmuneTrajectory** (6 클래스) | 200개/클래스 | 질병 궤적 패턴 최소 3개 이상 표현 | NHIS 데이터로 충족 |
| **PMO** (6 클래스) | 30개/클래스 | RONS 프로파일 최소 4종 표현 | 자체 실험 + 문헌 마이닝 |

**온톨로지 검증 방법:**
1. **구조적 검증**: HermiT/ELK 추론기 실행 → 불일치(inconsistency) 없음 확인
2. **인스턴스 검증**: 대표 SPARQL 쿼리 10종 정상 실행 확인
3. **역공학 검증**: 인스턴스로부터 알려진 인과 경로 재현 가능 여부
4. **전문가 검토**: 도메인 전문가 (면역학, 환경의학) 2인 이상 평가

**대표 검증 SPARQL 쿼리:**

```sparql
# Q1: 특정 환자의 PM2.5 노출과 IL-6 변화 시계열 조회
PREFIX ico: <http://purl.org/ico/>
PREFIX envimm: <http://purl.org/ico/envimmune/>
PREFIX traj: <http://purl.org/ico/trajectory/>

SELECT ?time ?pm25 ?il6 WHERE {
    ?exposure a envimm:EnvironmentalExposureEvent ;
              envimm:hasParticipant ico:patient/P001 ;
              envimm:hasTimepoint ?time ;
              envimm:hasMeasurement ?pm .
    ?pm envimm:hasValue ?pm25 .
    FILTER(?pm rdf:type obo:ENVO_01000796)  # particulate matter

    OPTIONAL {
        ?biomarker a ico:biomarker/IL6Measurement ;
                   envimm:hasParticipant ico:patient/P001 ;
                   envimm:hasTimepoint ?btime ;
                   envimm:hasValue ?il6 .
        FILTER(ABS(?time - ?btime) < "PT24H"^^xsd:duration)
    }
}
ORDER BY ?time

# Q2: 알레르기 마치 패턴을 보이는 환자 수 조회
SELECT (COUNT(DISTINCT ?patient) AS ?march_count) WHERE {
    ?traj a traj:AllergicMarchProgression ;
          traj:hasSubject ?patient ;
          traj:hasStage ?s1, ?s2, ?s3 .
    ?s1 traj:hasDiagnosis obo:DOID_3310 ;  # atopic dermatitis
        traj:hasOnsetDate ?d1 .
    ?s2 traj:hasDiagnosis obo:DOID_2841 ;  # asthma
        traj:hasOnsetDate ?d2 .
    ?s3 traj:hasDiagnosis obo:DOID_4481 ;  # allergic rhinitis
        traj:hasOnsetDate ?d3 .
    FILTER(?d1 < ?d2 && ?d2 < ?d3)
}

# Q3: RONS 용량에 따른 면역 조절 효과 조회 (호르메시스)
PREFIX pmo: <http://purl.org/ico/pmo/>

SELECT ?dose ?ros_total ?il10_change ?effect_type WHERE {
    ?session a pmo:PlasmaImmuneModulation ;
             pmo:hasRONSDose ?dose ;
             pmo:hasROSTotal ?ros_total ;
             pmo:hasImmuneResponse ?resp .
    ?resp pmo:hasMarkerChange ?il10_change ;
          pmo:hasMarkerName "IL-10" ;
          pmo:hasEffectType ?effect_type .
}
ORDER BY ?dose
```

---

## 부록 A: 데이터 소스별 API 키 관리

| 서비스 | API 키 발급 URL | 예상 할당량 | 비고 |
|--------|-------------|---------|------|
| data.go.kr (AirKorea, KMA, 실내공기질) | https://www.data.go.kr/ugs/selectPublicDataUseGuideView.do | 일 1,000건 (일반), 무제한 (인증) | 기관 인증 신청 권장 |
| EPA AQS | https://aqs.epa.gov/aqsweb/documents/data_api.html | 무제한 | 이메일 기반 인증 |
| PubMed E-utilities | https://www.ncbi.nlm.nih.gov/account/ | 초당 10건 (API key), 3건 (없으면) | NCBI 계정 필요 |
| Reactome Content Service | 키 불필요 | 초당 20건 | — |
| UK Biobank | Application 기반 | — | 승인 후 RAP 접근 |

## 부록 B: 예상 저장 용량

| 데이터 유형 | 기간 | 원시 크기 | 압축 후 | 비고 |
|-----------|------|---------|--------|------|
| AirKorea (5년) | 2021-2025 | ~40 GB | ~8 GB | TimescaleDB 압축 80% |
| KMA ASOS (5년) | 2021-2025 | ~15 GB | ~3 GB | |
| IoT 센서 (15세트, 1년) | 2026.07-2027.07 | ~30 GB | ~6 GB | 10초 집계 기준 |
| 웨어러블 (10명, 1년) | 2026.07-2027.07 | ~5 GB | ~1 GB | |
| 바이오마커 | 1단계 전체 | ~100 MB | ~20 MB | 구조화 정량값 |
| 플라즈마 실험 | 576 세션 | ~100 MB | ~50 MB | HDF5 포함 |
| NHIS 코호트 분석 결과 | — | ~10 GB | ~2 GB | 원격 분석실 내 |
| 온톨로지 RDF/OWL | 1단계 전체 | ~5 GB | ~1 GB | Turtle 포맷 |
| **총 예상** | | **~105 GB** | **~21 GB** | |

**권장 인프라:** NAS 1TB + 클라우드 백업 (S3 호환)

---

*본 문서는 1단계 시드연구(2026.04-2027.12) 데이터 수집 전략을 정의하며,
연구 진행에 따라 지속적으로 업데이트한다.*

*문서 작성: 2026-03-30*
*다음 검토 예정: 2026-05-01 (Tier 1 수집 시작 시)*
