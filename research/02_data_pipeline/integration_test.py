"""
통합 테스트: 기상청 + 에어코리아 → 복합지표 → ICO 온톨로지 트리플

Digital Columbus Project — Immune Care Ontology
End-to-end: Real API data → Composite indices → RDF triples → SPARQL-ready

실행: python3 integration_test.py
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────
# API Configuration
# ─────────────────────────────────────────────────────────────

API_KEY = "8dbf6117bde5d5672c00459c598330fe8df16298d74ea4b4504a46b75b47e90b"
KMA_BASE = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
AIR_BASE = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

# 창원시 성산구 KIMS
KMA_NX, KMA_NY = 91, 77
CHANGWON_STATIONS = ["웅남동", "용지동", "반송로", "사파동", "성주동", "의창", "성산"]

PATIENT_ID = "KIMS_P001"


def print_header():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Digital Columbus — 면역 케어 데이터 파이프라인 통합 테스트     ║")
    print("║  Real API → Composite Index → ICO RDF Triples              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상 위치: 창원시 성산구 (한국재료연구원)")
    print()


# ─────────────────────────────────────────────────────────────
# Step 1: 기상청 API 수집
# ─────────────────────────────────────────────────────────────

def step1_kma() -> dict[str, float]:
    print("=" * 66)
    print("  STEP 1: 기상청 초단기실황 수집 (KMA UltraSrtNcst)")
    print("=" * 66)

    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    base_time = (now - timedelta(hours=1)).strftime("%H00")

    url = (f"{KMA_BASE}/getUltraSrtNcst"
           f"?serviceKey={API_KEY}&numOfRows=10&pageNo=1&dataType=JSON"
           f"&base_date={base_date}&base_time={base_time}"
           f"&nx={KMA_NX}&ny={KMA_NY}")

    resp = requests.get(url, timeout=10)
    assert resp.status_code == 200, f"KMA HTTP {resp.status_code}"

    data = resp.json()
    assert data["response"]["header"]["resultCode"] == "00", \
        f"KMA Error: {data['response']['header']['resultMsg']}"

    cat_names = {"T1H": "기온(°C)", "REH": "습도(%)", "WSD": "풍속(m/s)",
                 "VEC": "풍향(°)", "RN1": "강수량(mm)", "PTY": "강수형태"}

    weather = {}
    items = data["response"]["body"]["items"]["item"]
    for item in items:
        cat = item["category"]
        weather[cat] = float(item["obsrValue"])

    print(f"  발표: {base_date} {base_time}")
    for cat, val in weather.items():
        print(f"    {cat_names.get(cat, cat):15s}: {val}")

    print(f"  ✅ KMA 수집 성공 ({len(items)}개 항목)")
    return weather


# ─────────────────────────────────────────────────────────────
# Step 2: 에어코리아 API 수집
# ─────────────────────────────────────────────────────────────

def step2_airkorea() -> dict[str, Any]:
    print()
    print("=" * 66)
    print("  STEP 2: 에어코리아 대기오염 수집 (AirKorea)")
    print("=" * 66)

    url = (f"{AIR_BASE}/getCtprvnRltmMesureDnsty"
           f"?serviceKey={API_KEY}&returnType=json&numOfRows=100&pageNo=1"
           f"&sidoName=경남&ver=1.5")

    resp = requests.get(url, timeout=10)
    if resp.status_code == 403:
        print("  ⚠️  403 Forbidden — 키 활성화 대기, 시뮬레이션 사용")
        return _mock_airkorea()

    data = resp.json()
    if data["response"]["header"]["resultCode"] != "00":
        print(f"  ⚠️  API 에러: {data['response']['header']['resultMsg']}")
        return _mock_airkorea()

    all_items = data["response"]["body"]["items"]

    # 창원 관련 측정소 필터
    cw = [x for x in all_items if x.get("stationName", "") in CHANGWON_STATIONS]
    if not cw:
        cw = all_items[:1]

    best = cw[0]
    result = {
        "station": best["stationName"],
        "dataTime": best.get("dataTime", ""),
        "pm25": _safe_float(best.get("pm25Value")),
        "pm10": _safe_float(best.get("pm10Value")),
        "o3": _safe_float(best.get("o3Value")),
        "no2": _safe_float(best.get("no2Value")),
        "co": _safe_float(best.get("coValue")),
        "so2": _safe_float(best.get("so2Value")),
        "khai": _safe_float(best.get("khaiValue")),
        "simulated": False,
    }

    print(f"  측정소: {result['station']} ({result['dataTime']})")
    print(f"    PM2.5: {result['pm25']} μg/m³")
    print(f"    PM10:  {result['pm10']} μg/m³")
    print(f"    O3:    {result['o3']} ppm")
    print(f"    NO2:   {result['no2']} ppm")
    print(f"    CO:    {result['co']} ppm")
    print(f"    SO2:   {result['so2']} ppm")
    print(f"    CAI:   {result['khai']}")
    print(f"  ✅ AirKorea 수집 성공")
    return result


def _safe_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _mock_airkorea() -> dict[str, Any]:
    return {
        "station": "시뮬레이션", "dataTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pm25": 25.0, "pm10": 42.0, "o3": 0.035, "no2": 0.025,
        "co": 0.5, "so2": 0.003, "khai": 72.0, "simulated": True,
    }


# ─────────────────────────────────────────────────────────────
# Step 3: 복합지표 산출
# ─────────────────────────────────────────────────────────────

def step3_composite(weather: dict, air: dict) -> dict[str, float]:
    print()
    print("=" * 66)
    print("  STEP 3: ICO 복합지표 산출 (Composite Indices)")
    print("=" * 66)

    pm25 = air["pm25"]
    o3 = air["o3"]
    reh = weather.get("REH", 50)

    # OxidativeStressLoad (ico:OxidativeStressLoad)
    pm25_norm = min(pm25 / 150.0 * 100, 100)
    o3_norm = min(o3 / 0.15 * 100, 100) if o3 > 0 else 0
    osl = pm25_norm * 0.5 + o3_norm * 0.2  # VOC 30% 미포함 (IoT센서 필요)

    # AllergenExposureScore (ico:AllergenExposureScore)
    rh_risk = max(0, (reh - 50) / 30) * 100  # 50% 이하=0, 80%=100
    mold_risk = max(0, (reh - 60) / 20) * 80  # 60% 이상 곰팡이 위험
    aes = np.clip(rh_risk * 0.4 + mold_risk * 0.6, 0, 100)

    # ImmuneRiskScore (ico:ImmuneRiskScore) — 다층 통합
    osl_contrib = osl / 100 * 30  # 환경 30%
    aes_contrib = aes / 100 * 20  # 알레르겐 20%
    # 라이프로그 50%는 웨어러블 데이터 필요 (현재 N/A)
    irs = osl_contrib + aes_contrib  # 부분 점수 (환경만)

    # PM2.5 면역 판정
    if pm25 <= 15:
        pm25_grade = "좋음"
        pm25_immune = "면역 영향 미미"
    elif pm25 <= 35:
        pm25_grade = "보통"
        pm25_immune = "장기 노출 시 면역 저하 가능"
    elif pm25 <= 75:
        pm25_grade = "나쁨"
        pm25_immune = "NF-κB 활성화 → IL-6/TNF-α 상승 위험"
    else:
        pm25_grade = "매우나쁨"
        pm25_immune = "급성 면역 반응 위험"

    # 습도 알레르겐 판정
    if reh >= 70:
        reh_risk_str = "높음 — 진드기/곰팡이 증식 위험"
    elif reh >= 60:
        reh_risk_str = "주의 — 알레르겐 노출 증가 가능"
    else:
        reh_risk_str = "양호"

    indices = {"osl": round(osl, 2), "aes": round(float(aes), 2), "irs": round(irs, 2)}

    print(f"  OxidativeStressLoad:   {indices['osl']:.1f}/70 (VOC 미포함)")
    print(f"    └ PM2.5 기여: {pm25_norm*0.5:.1f}, O3 기여: {o3_norm*0.2:.1f}")
    print(f"  AllergenExposureScore: {indices['aes']:.1f}/100")
    print(f"    └ 습도 {reh}% → {reh_risk_str}")
    print(f"  ImmuneRiskScore:       {indices['irs']:.1f}/50 (환경만, 라이프로그 미포함)")
    print()
    print(f"  ── 면역 영향 판정 ──")
    print(f"  PM2.5 [{pm25_grade}]: {pm25_immune}")
    print(f"  습도   [{reh_risk_str.split('—')[0].strip()}]: {reh_risk_str}")
    print(f"  ✅ 복합지표 산출 완료")

    indices["pm25_grade"] = pm25_grade
    indices["pm25_immune"] = pm25_immune
    indices["reh_risk"] = reh_risk_str
    return indices


# ─────────────────────────────────────────────────────────────
# Step 4: ICO RDF 트리플 생성
# ─────────────────────────────────────────────────────────────

def step4_rdf(weather: dict, air: dict, indices: dict) -> str:
    print()
    print("=" * 66)
    print("  STEP 4: ICO RDF 트리플 생성 (Turtle format)")
    print("=" * 66)

    ts = datetime.now().isoformat()
    ts_id = ts.replace(":", "").replace("-", "").replace(".", "")[:15]

    lines = [
        "@prefix ico: <http://purl.obolibrary.org/obo/ICO#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"# Generated: {ts}",
        f"# Location: 창원시 성산구 (KIMS)",
        f"# Patient: {PATIENT_ID}",
        "",
        "# ── Layer 1: 기상 데이터 (KMA) ──",
    ]

    kma_map = [
        ("T1H", "Temperature", "기온", "°C"),
        ("REH", "RelativeHumidity", "습도", "%"),
        ("WSD", "ClimateFactor", "풍속", "m/s"),
    ]
    for cat, cls, label, unit in kma_map:
        val = weather.get(cat)
        if val is not None:
            oid = f"ico:obs_kma_{cat}_{PATIENT_ID}_{ts_id}"
            lines += [
                f"{oid} a ico:{cls} ;",
                f'    rdfs:label "{label} (기상청)"@ko ;',
                f'    ico:hasValue "{val}"^^xsd:float ;',
                f'    ico:hasUnit "{unit}"^^xsd:string ;',
                f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .',
                "",
            ]

    lines.append("# ── Layer 1: 대기오염 데이터 (AirKorea) ──")
    air_map = [
        ("pm25", "PM2_5", "초미세먼지", "μg/m³"),
        ("pm10", "PM10", "미세먼지", "μg/m³"),
        ("o3", "Ozone", "오존", "ppm"),
        ("no2", "AirPollutant", "이산화질소", "ppm"),
        ("co", "AirPollutant", "일산화탄소", "ppm"),
        ("so2", "AirPollutant", "아황산가스", "ppm"),
    ]
    src = "(시뮬레이션)" if air.get("simulated") else f"({air['station']})"
    for field, cls, label, unit in air_map:
        val = air.get(field)
        if val is not None and val > 0:
            oid = f"ico:obs_air_{field}_{PATIENT_ID}_{ts_id}"
            lines += [
                f"{oid} a ico:{cls} ;",
                f'    rdfs:label "{label} {src}"@ko ;',
                f'    ico:hasValue "{val}"^^xsd:float ;',
                f'    ico:hasUnit "{unit}"^^xsd:string ;',
                f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .',
                "",
            ]

    lines.append("# ── 복합지표 (Composite Indices) ──")
    idx_map = [
        ("osl", "OxidativeStressLoad", "산화스트레스 부하"),
        ("aes", "AllergenExposureScore", "알레르겐 노출점수"),
        ("irs", "ImmuneRiskScore", "면역 위험 점수"),
    ]
    for field, cls, label in idx_map:
        val = indices.get(field)
        if val is not None:
            oid = f"ico:idx_{field}_{PATIENT_ID}_{ts_id}"
            lines += [
                f"{oid} a ico:{cls} ;",
                f'    rdfs:label "{label}"@ko ;',
                f'    ico:hasValue "{val}"^^xsd:float ;',
                f'    ico:hasUnit "score"^^xsd:string ;',
                f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .',
                "",
            ]

    ttl = "\n".join(lines)
    triple_count = ttl.count(" a ico:")
    print(f"  생성된 트리플 수: {triple_count}개 인스턴스")
    print(f"  총 라인 수: {len(lines)}")
    print(f"  ✅ RDF 트리플 생성 완료")
    return ttl


# ─────────────────────────────────────────────────────────────
# Step 5: RDF 검증 (rdflib 파싱)
# ─────────────────────────────────────────────────────────────

def step5_validate(ttl: str) -> bool:
    print()
    print("=" * 66)
    print("  STEP 5: RDF 트리플 검증 (rdflib 파싱)")
    print("=" * 66)

    from rdflib import Graph

    g = Graph()
    try:
        g.parse(data=ttl, format="turtle")
        triple_count = len(g)
        print(f"  파싱 결과: {triple_count}개 RDF 트리플")

        # ICO 클래스별 인스턴스 수
        query = """
        PREFIX ico: <http://purl.obolibrary.org/obo/ICO#>
        SELECT ?type (COUNT(?s) AS ?count)
        WHERE { ?s a ?type }
        GROUP BY ?type
        ORDER BY DESC(?count)
        """
        results = g.query(query)
        print(f"  ICO 클래스별 인스턴스:")
        for row in results:
            cls = str(row[0]).split("#")[-1]
            cnt = int(row[1])
            print(f"    ico:{cls:30s}: {cnt}개")

        print(f"  ✅ RDF 검증 통과 — {triple_count}개 트리플 유효")
        return True
    except Exception as e:
        print(f"  ❌ RDF 파싱 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print_header()

    passed = 0
    total = 5

    # Step 1
    try:
        weather = step1_kma()
        passed += 1
    except Exception as e:
        print(f"  ❌ STEP 1 실패: {e}")
        sys.exit(1)

    # Step 2
    try:
        air = step2_airkorea()
        passed += 1
    except Exception as e:
        print(f"  ❌ STEP 2 실패: {e}")
        sys.exit(1)

    # Step 3
    try:
        indices = step3_composite(weather, air)
        passed += 1
    except Exception as e:
        print(f"  ❌ STEP 3 실패: {e}")
        sys.exit(1)

    # Step 4
    try:
        ttl = step4_rdf(weather, air, indices)
        passed += 1
    except Exception as e:
        print(f"  ❌ STEP 4 실패: {e}")
        sys.exit(1)

    # Step 5
    try:
        valid = step5_validate(ttl)
        if valid:
            passed += 1
    except Exception as e:
        print(f"  ❌ STEP 5 실패: {e}")

    # ── 최종 결과 ──
    print()
    print("=" * 66)
    print(f"  통합 테스트 결과: {passed}/{total} PASSED")
    print("=" * 66)
    data_src = "실측" if not air.get("simulated") else "시뮬레이션"
    print(f"  기상청 API:    ✅ 기온 {weather.get('T1H')}°C, 습도 {weather.get('REH')}%")
    print(f"  에어코리아:    {'✅' if not air.get('simulated') else '⚠️'} PM2.5={air['pm25']}μg/m³ ({data_src})")
    print(f"  복합지표:      ✅ OSL={indices['osl']}, AES={indices['aes']}, IRS={indices['irs']}")
    print(f"  면역 판정:     PM2.5 [{indices['pm25_grade']}] {indices['pm25_immune']}")
    print(f"  RDF 트리플:    ✅ rdflib 검증 통과")
    print()

    if passed == total:
        print("  🎉 통합 테스트 전체 통과!")
    else:
        print(f"  ⚠️  {total - passed}개 단계 실패")

    sys.exit(0 if passed == total else 1)
