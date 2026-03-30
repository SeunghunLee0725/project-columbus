# 국민건강보험공단 공공데이터 — 면역 케어 온톨로지 활용 리스트

**조사일**: 2026-03-30
**출처**: [data.go.kr 국민건강보험공단 데이터셋](https://www.data.go.kr/tcs/dss/selectDataSetList.do?dType=FILE&org=%EA%B5%AD%EB%AF%BC%EA%B1%B4%EA%B0%95%EB%B3%B4%ED%97%98%EA%B3%B5%EB%8B%A8)

---

## A. 핵심 활용 데이터 (면역 질환 직접 관련)

### A-1. 환경성 질환 의료이용정보 ⭐⭐⭐

본 연구의 대상 질환과 직접 매칭되는 핵심 데이터.

| # | 데이터명 | URL | ICD코드 | ICO 매핑 | 활용도 |
|---|---------|-----|---------|---------|-------|
| 1 | **환경성질환(아토피) 의료이용정보** | [15104805](https://www.data.go.kr/data/15104805/fileData.do) | L20 | `ico:AtopicDermatitis` | ⭐⭐⭐ |
| 2 | **환경성질환(천식) 의료이용정보** | [15104806](https://www.data.go.kr/data/15104806/fileData.do) | J45, J46 | `ico:Asthma` | ⭐⭐⭐ |
| 3 | **환경성질환(비염) 의료이용정보** | [15104804](https://www.data.go.kr/data/15104804/fileData.do) | J30 | `ico:AllergicRhinitis` | ⭐⭐⭐ |
| 4 | **아토피(L20) 진료인원 및 총진료비 현황** | [15124055](https://www.data.go.kr/data/15124055/fileData.do) | L20 | `ico:AtopicDermatitis` | ⭐⭐⭐ |

**데이터 구성**: 월별, 인구학적 특성(성별/연령/지역), 의료이용 특성(입원/외래) 포함
**활용**: 알레르기 마치(AD→천식→비염) 궤적 검증, 계절/지역별 면역질환 발생 패턴 분석

### A-2. 건강검진 정보 ⭐⭐⭐

바이오마커 데이터 (혈당, 콜레스테롤, 혈색소 등) 포함.

| # | 데이터명 | URL | 규모 | ICO 매핑 | 활용도 |
|---|---------|-----|------|---------|-------|
| 5 | **건강검진정보** | [15007122](https://www.data.go.kr/data/15007122/fileData.do) | 100만명/년 | `ico:Biomarker` 전반 | ⭐⭐⭐ |
| 6 | **직역별 성별 연령별 건강검진정보** | [15144521](https://www.data.go.kr/data/15144521/fileData.do) | 통계 집계 | `ico:Biomarker` | ⭐⭐ |
| 7 | **건강검진통계연보** | [15103039](https://www.data.go.kr/data/15103039/fileData.do) | 연도별 통계 | 참조 | ⭐⭐ |

**데이터 구성**: 시도코드, 성별, 연령대, 키, 체중, 혈압, 혈당, 총콜레스테롤, 혈색소 등
**활용**: 면역 관련 바이오마커 기준값 설정, 건강검진 결과와 면역질환 상관분석

### A-3. 진료내역/처방 정보 ⭐⭐⭐

면역질환 진료 및 처방 패턴 분석.

| # | 데이터명 | URL | ICO 매핑 | 활용도 |
|---|---------|-----|---------|-------|
| 8 | **진료내역정보** | [15007115](https://www.data.go.kr/data/15007115/fileData.do) | `ico:ImmuneDisease` 전반 | ⭐⭐⭐ |
| 9 | **의약품처방정보** | [15007117](https://www.data.go.kr/data/15007117/fileData.do) | `ico:TreatmentProtocol` | ⭐⭐⭐ |
| 10 | **진료건수 정보** | [15083145](https://www.data.go.kr/data/15083145/fileData.do) | `ico:ImmuneDisease` | ⭐⭐ |

**활용**: ICD-10 코드 기반 면역질환(L20, J45, J30, L40, H04.1, M05/M06) 진료 추이 분석

---

## B. 상병/수술 코드별 분석 데이터 (면역질환 세부 분석)

| # | 데이터명 | URL | ICO 매핑 | 활용도 |
|---|---------|-----|---------|-------|
| 11 | **특정 상병 및 수가코드 그룹별 진료환자 정보H** | [15130088](https://www.data.go.kr/data/15130088/fileData.do) | `ico:DiseaseTrajectory` | ⭐⭐⭐ |
| 12 | **특정 상병 및 수가코드 그룹별 진료환자 정보G** | [15127926](https://www.data.go.kr/data/15127926/fileData.do) | `ico:DiseaseTrajectory` | ⭐⭐ |
| 13 | **특정 상병 및 수가코드 그룹별 진료환자 정보I** | [15130569](https://www.data.go.kr/data/15130569/fileData.do) | `ico:DiseaseTrajectory` | ⭐⭐ |
| 14 | **특정 질병코드분류별 수술 진료환자수** | [15117754](https://www.data.go.kr/data/15117754/fileData.do) | 참조 | ⭐ |
| 15 | **특정 질병 진료환자수 및 진료건수A** | [15120971](https://www.data.go.kr/data/15120971/fileData.do) | `ico:ImmuneDisease` | ⭐⭐ |
| 16 | **특정 의약품이 처방된 상병별 진료내역B** | [15128000](https://www.data.go.kr/data/15128000/fileData.do) | `ico:TreatmentProtocol` | ⭐⭐ |
| 17 | **의료급여상병기호** | [15121266](https://www.data.go.kr/data/15121266/fileData.do) | 코드 매핑 참조 | ⭐ |

**활용**: 면역질환 ICD-10 코드별 진료환자 추이, 복합 상병 패턴 (알레르기 마치 검증)

---

## C. 통계/지역별 분석 데이터

| # | 데이터명 | URL | 활용도 |
|---|---------|-----|-------|
| 18 | **건강보험 및 의료급여 구분별 진료통계** | [15139916](https://www.data.go.kr/data/15139916/fileData.do) | ⭐⭐ |
| 19 | **건강보험주요통계** | [15103019](https://www.data.go.kr/data/15103019/fileData.do) | ⭐ |
| 20 | **건강보험통계연보** | [15103018](https://www.data.go.kr/data/15103018/fileData.do) | ⭐ |
| 21 | **지역별의료이용통계** | [15103036](https://www.data.go.kr/data/15103036/fileData.do) | ⭐⭐ |
| 22 | **건강보험 급여현황(시도)** | [15095099](https://www.data.go.kr/data/15095099/fileData.do) | ⭐ |
| 23 | **의료급여통계연보** | [15103020](https://www.data.go.kr/data/15103020/fileData.do) | ⭐ |
| 24 | **내외국인 건강보험료 부과 및 급여 현황** | [15138933](https://www.data.go.kr/data/15138933/fileData.do) | ⭐ |

**활용**: 지역별(창원시) 면역질환 의료이용 패턴, 환경 데이터(AirKorea)와 지역 매칭

---

## D. 기타 참조 데이터

| # | 데이터명 | URL | 활용도 |
|---|---------|-----|-------|
| 25 | **NHIS 발간자료** | [15095102](https://www.data.go.kr/data/15095102/fileData.do) | 참조 |
| 26 | **전자처방전조제일반정보** | [15122300](https://www.data.go.kr/data/15122300/fileData.do) | ⭐ |
| 27 | **건강정보조회로그** | [15121221](https://www.data.go.kr/data/15121221/fileData.do) | ⭐ |
| 28 | **자료보관신청** | [15122147](https://www.data.go.kr/data/15122147/fileData.do) | 참조 |
| 29 | **일반통계** | [15103030](https://www.data.go.kr/data/15103030/fileData.do) | 참조 |
| 30 | **검진기관기본정보** | [15133044](https://www.data.go.kr/data/15133044/fileData.do) | 참조 |

---

## E. NHIS 별도 신청 데이터 (nhiss.nhis.or.kr)

data.go.kr 외에 [국민건강보험자료 공유서비스](https://nhiss.nhis.or.kr/)에서 별도 신청 가능한 심층 데이터.

| # | DB명 | 내용 | 규모 | 신청 방법 |
|---|------|------|------|---------|
| 31 | **표본코호트 2.0 DB** | 자격, 보험료, 진료, 건강검진, 요양기관 등 19개 테이블 | 100만명 | nhiss.nhis.or.kr 신청 |
| 32 | **건강검진 코호트 DB** | 건강검진 수검자 종단 추적 | 51만명 | nhiss.nhis.or.kr 신청 |
| 33 | **맞춤형 DB** | 연구 목적에 맞는 커스텀 추출 | 전 국민 | IRB + nhiss 신청 |

**표본코호트 2.0 테이블 (19개)**:
자격/보험료, 출생/사망, 진료(입원/외래/약국), 건강검진, 요양기관, 장기요양, 암등록, 희귀난치성질환 등

---

## F. 우선순위 추천 — 면역 케어 온톨로지 관점

### 즉시 다운로드 (Tier 1, 0-3개월)

| 순위 | 데이터 | 이유 |
|------|--------|------|
| **1** | 환경성질환(아토피) 의료이용정보 (#1) | 핵심 대상질환 L20, 월별/지역별 데이터 |
| **2** | 환경성질환(천식) 의료이용정보 (#2) | 알레르기 마치 2단계 J45 |
| **3** | 환경성질환(비염) 의료이용정보 (#3) | 알레르기 마치 3단계 J30 |
| **4** | 건강검진정보 (#5) | 100만명 바이오마커 (혈당, 콜레스테롤 등) |
| **5** | 진료내역정보 (#8) | ICD-10 기반 면역질환 전체 진료 추이 |
| **6** | 특정 상병별 진료환자 정보H (#11) | 복합 상병 패턴 → 궤적 검증 |

### 별도 신청 필요 (Tier 3, 9-24개월)

| 순위 | 데이터 | 이유 |
|------|--------|------|
| **7** | 표본코호트 2.0 DB (#31) | 종단 추적 가능, TFT 모델 학습 핵심 |
| **8** | 건강검진 코호트 DB (#32) | 검진 바이오마커 시계열 |
| **9** | 맞춤형 DB (#33) | 면역질환 특화 추출 (IRB 필요) |

---

## G. 데이터-ICO 클래스 매핑 요약

| ICO 클래스 | 매핑 가능 데이터 (# 번호) |
|-----------|----------------------|
| `ico:AtopicDermatitis` | #1, #4, #8, #11 |
| `ico:Asthma` | #2, #8, #11 |
| `ico:AllergicRhinitis` | #3, #8, #11 |
| `ico:Psoriasis` | #8, #11, #15 |
| `ico:DryEyeDisease` | #8, #11, #15 |
| `ico:RheumatoidArthritis` | #8, #11, #15 |
| `ico:Biomarker` | #5, #6, #7 |
| `ico:TreatmentProtocol` | #9, #16, #26 |
| `ico:DiseaseTrajectory` | #11, #12, #13, #31 |
| `ico:ImmuneRiskScore` | #5 + AirKorea + KMA 통합 |
