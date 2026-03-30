# NHIS 공공데이터 다운로드 안내

이 폴더에 data.go.kr에서 다운로드한 NHIS 파일데이터를 저장하세요.

## 다운로드 방법
1. https://www.data.go.kr 로그인
2. 아래 링크에서 각 데이터셋의 '파일데이터 다운로드' 클릭
3. 다운로드된 파일을 이 폴더에 저장

## 즉시 다운로드 대상 (우선순위순)

| 파일명 규칙 | 데이터 | 링크 |
|-----------|--------|------|
| `atopy_*.csv` | 환경성질환(아토피) 의료이용정보 | https://www.data.go.kr/data/15104805/fileData.do |
| `asthma_*.csv` | 환경성질환(천식) 의료이용정보 | https://www.data.go.kr/data/15104806/fileData.do |
| `rhinitis_*.csv` | 환경성질환(비염) 의료이용정보 | https://www.data.go.kr/data/15104804/fileData.do |
| `health_checkup_*.csv` | 건강검진정보 (100만명) | https://www.data.go.kr/data/15007122/fileData.do |
| `medical_treatment_*.csv` | 진료내역정보 | https://www.data.go.kr/data/15007115/fileData.do |
| `disease_code_*.csv` | 특정 상병별 진료환자 정보H | https://www.data.go.kr/data/15130088/fileData.do |

## 별도 신청 필요 (nhiss.nhis.or.kr)

| DB명 | 신청처 | 비고 |
|------|--------|------|
| 표본코호트 2.0 DB | https://nhiss.nhis.or.kr/bd/ab/bdaba002cv.do | IRB 필요, 심의 2-3개월 |
| 건강검진 코호트 DB | 동일 | IRB 필요 |
| 맞춤형 DB | 동일 | IRB + 연구계획서 |
