"""
기상청 단기예보 API 수집기 (KMA Short-term Forecast Collector)

Digital Columbus Project — Immune Care Ontology
KIMS, PI: Seunghoon Lee

API: VilageFcstInfoService_2.0
Endpoint: http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0

수집 항목 및 ICO 매핑:
  - T1H/TMP (기온)      → ico:Temperature
  - REH (습도)           → ico:RelativeHumidity → AllergenExposureScore 입력
  - WSD/VEC (풍속/풍향)   → ico:ClimateFactor → 오염물질 확산 모델
  - POP/PCP (강수확률/량) → ico:ClimateFactor → PhysicalActivityLevel 예측
  - SKY (하늘상태)        → ico:ClimateFactor → 자외선/비타민D/면역

주의: URL에 serviceKey를 직접 포함해야 함 (requests params dict 사용 시 이중인코딩 발생)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

API_KEY = "8dbf6117bde5d5672c00459c598330fe8df16298d74ea4b4504a46b75b47e90b"
BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

# 창원시 성산구 한국재료연구원 (위도 35.228, 경도 128.681)
LOCATIONS = {
    "changwon_seongsan": {"nx": 91, "ny": 77, "name": "창원시 성산구 (KIMS)"},
    "seoul_jongno": {"nx": 60, "ny": 127, "name": "서울시 종로구"},
    "busan_haeundae": {"nx": 99, "ny": 75, "name": "부산시 해운대구"},
}

DEFAULT_LOCATION = "changwon_seongsan"

# 카테고리 매핑
ULTRA_SRT_NCST_CATEGORIES = {
    "T1H": {"name_ko": "기온", "unit": "°C", "ico_class": "ico:Temperature"},
    "RN1": {"name_ko": "1시간강수량", "unit": "mm", "ico_class": "ico:ClimateFactor"},
    "UUU": {"name_ko": "동서바람", "unit": "m/s", "ico_class": "ico:ClimateFactor"},
    "VVV": {"name_ko": "남북바람", "unit": "m/s", "ico_class": "ico:ClimateFactor"},
    "REH": {"name_ko": "습도", "unit": "%", "ico_class": "ico:RelativeHumidity"},
    "PTY": {"name_ko": "강수형태", "unit": "코드", "ico_class": "ico:ClimateFactor"},
    "VEC": {"name_ko": "풍향", "unit": "°", "ico_class": "ico:ClimateFactor"},
    "WSD": {"name_ko": "풍속", "unit": "m/s", "ico_class": "ico:ClimateFactor"},
}

VILAGE_FCST_CATEGORIES = {
    "POP": {"name_ko": "강수확률", "unit": "%"},
    "PTY": {"name_ko": "강수형태", "unit": "코드"},
    "PCP": {"name_ko": "1시간강수량", "unit": "mm"},
    "REH": {"name_ko": "습도", "unit": "%"},
    "SNO": {"name_ko": "1시간신적설", "unit": "cm"},
    "SKY": {"name_ko": "하늘상태", "unit": "코드"},
    "TMP": {"name_ko": "기온", "unit": "°C"},
    "TMN": {"name_ko": "최저기온", "unit": "°C"},
    "TMX": {"name_ko": "최고기온", "unit": "°C"},
    "UUU": {"name_ko": "동서바람", "unit": "m/s"},
    "VVV": {"name_ko": "남북바람", "unit": "m/s"},
    "WAV": {"name_ko": "파고", "unit": "M"},
    "VEC": {"name_ko": "풍향", "unit": "°"},
    "WSD": {"name_ko": "풍속", "unit": "m/s"},
}

PTY_CODES = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기",
             5: "빗방울", 6: "빗방울눈날림", 7: "눈날림"}
SKY_CODES = {1: "맑음", 3: "구름많음", 4: "흐림"}


# ─────────────────────────────────────────────────────────────
# API Call Functions
# ─────────────────────────────────────────────────────────────

def _build_url(operation: str, **params) -> str:
    """Build API URL with serviceKey directly embedded (avoids double-encoding)."""
    url = f"{BASE_URL}/{operation}?serviceKey={API_KEY}"
    for k, v in params.items():
        url += f"&{k}={v}"
    return url


def fetch_ultra_srt_ncst(
    base_date: str | None = None,
    base_time: str | None = None,
    location: str = DEFAULT_LOCATION,
) -> list[dict[str, Any]]:
    """초단기실황조회 — 현재 기상 관측값.

    Args:
        base_date: 발표일자 (YYYYMMDD). None이면 현재 시각 기준.
        base_time: 발표시각 (HH00, 매시 정각). None이면 현재-1시간.
        location: LOCATIONS 딕셔너리 키.

    Returns:
        List of dicts with category, value, unit, ico_class.
    """
    now = datetime.now()
    if base_date is None:
        base_date = now.strftime("%Y%m%d")
    if base_time is None:
        base_time = (now - timedelta(hours=1)).strftime("%H00")

    loc = LOCATIONS[location]
    url = _build_url(
        "getUltraSrtNcst",
        numOfRows=10, pageNo=1, dataType="JSON",
        base_date=base_date, base_time=base_time,
        nx=loc["nx"], ny=loc["ny"],
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    header = data["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"API Error: {header['resultCode']} {header['resultMsg']}")

    items = data["response"]["body"]["items"]["item"]
    results = []
    for item in items:
        cat = item["category"]
        meta = ULTRA_SRT_NCST_CATEGORIES.get(cat, {})
        results.append({
            "category": cat,
            "name_ko": meta.get("name_ko", cat),
            "value": item["obsrValue"],
            "unit": meta.get("unit", ""),
            "ico_class": meta.get("ico_class", ""),
            "base_date": item["baseDate"],
            "base_time": item["baseTime"],
            "location": loc["name"],
            "nx": item["nx"],
            "ny": item["ny"],
        })
    return results


def fetch_vilage_fcst(
    base_date: str | None = None,
    base_time: str | None = None,
    location: str = DEFAULT_LOCATION,
    num_rows: int = 300,
) -> pd.DataFrame:
    """단기예보조회 — 3일 예보.

    발표시각: 02, 05, 08, 11, 14, 17, 20, 23시 (하루 8회)
    API 제공: 발표시각 + 10분 이후

    Returns:
        DataFrame with columns: fcst_datetime, category, value + pivot-friendly format.
    """
    now = datetime.now()
    if base_date is None:
        base_date = now.strftime("%Y%m%d")
    if base_time is None:
        fcst_hours = [2, 5, 8, 11, 14, 17, 20, 23]
        fcst_base = max([h for h in fcst_hours if h <= now.hour], default=23)
        base_time = f"{fcst_base:02d}00"

    loc = LOCATIONS[location]
    url = _build_url(
        "getVilageFcst",
        numOfRows=num_rows, pageNo=1, dataType="JSON",
        base_date=base_date, base_time=base_time,
        nx=loc["nx"], ny=loc["ny"],
    )

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    header = data["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"API Error: {header['resultCode']} {header['resultMsg']}")

    items = data["response"]["body"]["items"]["item"]

    rows = []
    for item in items:
        rows.append({
            "fcst_datetime": pd.Timestamp(f"{item['fcstDate']} {item['fcstTime'][:2]}:{item['fcstTime'][2:]}"),
            "category": item["category"],
            "value": item["fcstValue"],
            "base_date": item["baseDate"],
            "base_time": item["baseTime"],
        })

    df = pd.DataFrame(rows)
    return df


def get_current_weather(location: str = DEFAULT_LOCATION) -> dict[str, Any]:
    """현재 기상 실황을 딕셔너리로 반환.

    Returns:
        Dict with keys: temperature, humidity, wind_speed, wind_dir,
        precipitation, precip_type, and derived immune_relevance fields.
    """
    items = fetch_ultra_srt_ncst(location=location)
    weather = {}
    for item in items:
        cat = item["category"]
        try:
            weather[cat] = float(item["value"])
        except (ValueError, TypeError):
            weather[cat] = 0.0

    result = {
        "timestamp": datetime.now().isoformat(),
        "location": LOCATIONS[location]["name"],
        "temperature_c": weather.get("T1H", None),
        "humidity_pct": weather.get("REH", None),
        "wind_speed_ms": weather.get("WSD", None),
        "wind_dir_deg": weather.get("VEC", None),
        "precipitation_mm": weather.get("RN1", 0),
        "precip_type": PTY_CODES.get(int(weather.get("PTY", 0)), "없음"),
    }

    # 면역 관련 파생 지표
    reh = result["humidity_pct"]
    if reh is not None:
        if reh >= 70:
            result["allergen_risk"] = "high"
            result["allergen_comment"] = "진드기/곰팡이 증식 위험 (습도 ≥70%)"
        elif reh >= 60:
            result["allergen_risk"] = "moderate"
            result["allergen_comment"] = "알레르겐 노출 증가 가능 (습도 ≥60%)"
        else:
            result["allergen_risk"] = "low"
            result["allergen_comment"] = "양호"

    return result


def get_forecast_dataframe(location: str = DEFAULT_LOCATION) -> pd.DataFrame:
    """단기예보를 피벗된 DataFrame으로 반환.

    Returns:
        DataFrame indexed by fcst_datetime with columns: TMP, REH, POP, SKY, WSD, etc.
    """
    df = fetch_vilage_fcst(location=location)
    if df.empty:
        return df

    pivot = df.pivot_table(
        index="fcst_datetime", columns="category", values="value", aggfunc="first"
    )

    # 숫자 변환
    for col in pivot.columns:
        pivot[col] = pd.to_numeric(pivot[col], errors="coerce")

    return pivot


# ─────────────────────────────────────────────────────────────
# ICO Ontology Mapping
# ─────────────────────────────────────────────────────────────

def weather_to_ico_triples(weather: dict[str, Any], patient_id: str = "P001") -> str:
    """현재 기상 데이터를 ICO RDF 트리플(Turtle)로 변환."""
    ts = weather.get("timestamp", datetime.now().isoformat())
    ts_clean = ts.replace(":", "").replace("-", "").replace(".", "")[:15]

    triples = []
    triples.append("@prefix ico: <http://purl.obolibrary.org/obo/ICO#> .")
    triples.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    triples.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    triples.append("")

    mapping = [
        ("temperature_c", "Temperature", "°C"),
        ("humidity_pct", "RelativeHumidity", "%"),
        ("wind_speed_ms", "ClimateFactor", "m/s"),
    ]

    for field, ico_class, unit in mapping:
        val = weather.get(field)
        if val is not None:
            obs_id = f"ico:kma_obs_{field}_{patient_id}_{ts_clean}"
            triples.append(f"{obs_id} a ico:{ico_class} ;")
            triples.append(f'    rdfs:label "KMA {field}"@en ;')
            triples.append(f'    ico:hasValue "{val}"^^xsd:float ;')
            triples.append(f'    ico:hasUnit "{unit}"^^xsd:string ;')
            triples.append(f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .')
            triples.append("")

    return "\n".join(triples)


# ─────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  기상청 단기예보 수집기 — Digital Columbus / KIMS            ║")
    print("║  KMA Weather Collector for Immune Care Ontology             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # 1. 현재 날씨
    print("=== 1. 현재 기상 실황 (창원시 성산구) ===")
    weather = get_current_weather()
    for k, v in weather.items():
        print(f"  {k:25s}: {v}")
    print()

    # 2. 단기예보
    print("=== 2. 단기예보 (12시간) ===")
    fcst = get_forecast_dataframe()
    if not fcst.empty:
        cols = [c for c in ["TMP", "REH", "POP", "SKY", "WSD"] if c in fcst.columns]
        print(fcst[cols].head(12).to_string())
    print()

    # 3. ICO 트리플
    print("=== 3. ICO RDF 트리플 ===")
    ttl = weather_to_ico_triples(weather)
    print(ttl)

    # 4. 미세먼지 API 상태
    print("=== 4. 미세먼지(에어코리아) API 상태 ===")
    print("  서비스: 한국환경공단_에어코리아_대기오염정보")
    print("  End Point: http://apis.data.go.kr/B552584/ArpltnInforInqireSvc")
    print("  항목: PM2.5, PM10, O3, NO2, CO, SO2")
    print("  상태: ❌ 별도 API 활용 신청 필요 (기상청 키와 별개)")
    print("  신청: https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15073861")
    print("  → '활용신청' 버튼 클릭 후 승인 대기 (보통 자동승인)")
    print()
    print("  ICO 매핑 (신청 후 활용 가능):")
    print("    PM2.5 → ico:PM2_5 (OxidativeStressLoad 핵심 입력)")
    print("    PM10  → ico:PM10")
    print("    O3    → ico:Ozone (OxidativeStressLoad 입력)")
    print("    NO2   → ico:AirPollutant")
    print()
    print("✅ 기상청 API 수집기 정상 작동")
