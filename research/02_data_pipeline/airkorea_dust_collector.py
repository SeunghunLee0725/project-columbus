"""
에어코리아 대기오염정보 수집기 (AirKorea Air Pollution Collector)

Digital Columbus Project — Immune Care Ontology
KIMS, PI: Seunghoon Lee

API: ArpltnInforInqireSvc (한국환경공단_에어코리아_대기오염정보)
Endpoint: http://apis.data.go.kr/B552584/ArpltnInforInqireSvc

수집 항목 및 ICO 매핑:
  - PM2.5 (초미세먼지)  → ico:PM2_5     (OxidativeStressLoad 50%)
  - PM10 (미세먼지)     → ico:PM10
  - O3 (오존)          → ico:Ozone     (OxidativeStressLoad 20%)
  - NO2 (이산화질소)    → ico:AirPollutant
  - CO (일산화탄소)     → ico:AirPollutant
  - SO2 (아황산가스)    → ico:AirPollutant

상태: API 키 활성화 대기 중 (신청 후 1-2시간 ~ 최대 24시간)
"""

import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

API_KEY = "8dbf6117bde5d5672c00459c598330fe8df16298d74ea4b4504a46b75b47e90b"
BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

# 창원시 주요 측정소
STATIONS = {
    "seongsan": {"name": "성산", "name_en": "Seongsan", "desc": "창원시 성산구 (KIMS 인근)"},
    "uichanggu": {"name": "의창", "name_en": "Uichang", "desc": "창원시 의창구"},
    "masan": {"name": "마산", "name_en": "Masan", "desc": "창원시 마산"},
}

DEFAULT_STATION = "seongsan"

# ICO 매핑
ICO_MAPPING = {
    "pm25Value": {"ico_class": "ico:PM2_5", "name_ko": "초미세먼지", "unit": "μg/m³",
                  "immune_role": "ROS→NF-κB→IL-6 (r=+0.52, lag 6-24h)"},
    "pm10Value": {"ico_class": "ico:PM10", "name_ko": "미세먼지", "unit": "μg/m³",
                  "immune_role": "기도 염증 유발"},
    "o3Value":   {"ico_class": "ico:Ozone", "name_ko": "오존", "unit": "ppm",
                  "immune_role": "OxidativeStressLoad 20% 가중치"},
    "no2Value":  {"ico_class": "ico:AirPollutant", "name_ko": "이산화질소", "unit": "ppm",
                  "immune_role": "기도 염증, 천식 악화"},
    "coValue":   {"ico_class": "ico:AirPollutant", "name_ko": "일산화탄소", "unit": "ppm",
                  "immune_role": "산소 운반 장애"},
    "so2Value":  {"ico_class": "ico:AirPollutant", "name_ko": "아황산가스", "unit": "ppm",
                  "immune_role": "기도 자극, 천식 유발"},
}

# PM2.5 면역 영향 등급 (WHO 2021 가이드라인 기반)
PM25_IMMUNE_GRADES = [
    (15,  "좋음", "면역 영향 미미"),
    (35,  "보통", "장기 노출 시 면역 저하 가능"),
    (75,  "나쁨", "NF-κB 활성화 위험, IL-6/TNF-α 상승 예상"),
    (150, "매우나쁨", "급성 면역반응, 즉각적 환경 개선 필요"),
    (999, "위험", "심각한 면역 손상 위험"),
]


# ─────────────────────────────────────────────────────────────
# API Functions
# ─────────────────────────────────────────────────────────────

def _build_url(operation: str, **params) -> str:
    """URL 직접 조립 (이중 인코딩 방지)."""
    url = f"{BASE_URL}/{operation}?serviceKey={API_KEY}"
    for k, v in params.items():
        url += f"&{k}={v}"
    return url


def fetch_station_realtime(
    station: str = DEFAULT_STATION,
    data_term: str = "DAILY",
) -> list[dict[str, Any]]:
    """측정소별 실시간 측정정보 조회.

    Args:
        station: STATIONS 딕셔너리 키 또는 측정소 한글명.
        data_term: DAILY(1일), MONTH(1개월), 3MONTH(3개월).

    Returns:
        List of measurement dicts (최신순).
    """
    if station in STATIONS:
        station_name = STATIONS[station]["name"]
    else:
        station_name = station

    url = _build_url(
        "getMsrstnAcctoRltmMesureDnsty",
        returnType="json", numOfRows=24, pageNo=1,
        stationName=station_name, dataTerm=data_term, ver="1.5",
    )

    resp = requests.get(url, timeout=10)

    if resp.status_code == 403:
        raise PermissionError(
            "API 접근 거부 (403). API 키가 아직 활성화되지 않았을 수 있습니다.\n"
            "data.go.kr 마이페이지에서 '에어코리아_대기오염정보' 신청 상태를 확인하세요."
        )
    resp.raise_for_status()

    data = resp.json()
    header = data["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"API Error: {header['resultCode']} {header['resultMsg']}")

    return data["response"]["body"]["items"]


def fetch_sido_realtime(
    sido: str = "경남",
    num_rows: int = 50,
) -> pd.DataFrame:
    """시도별 실시간 측정정보 조회.

    Args:
        sido: 시도명 (서울, 부산, 경남 등).

    Returns:
        DataFrame with all stations in the specified region.
    """
    url = _build_url(
        "getCtprvnRltmMesureDnsty",
        returnType="json", numOfRows=num_rows, pageNo=1,
        sidoName=sido, ver="1.5",
    )

    resp = requests.get(url, timeout=10)
    if resp.status_code == 403:
        raise PermissionError("API 키 미활성화. data.go.kr에서 신청 상태 확인 필요.")
    resp.raise_for_status()

    data = resp.json()
    items = data["response"]["body"].get("items", [])
    return pd.DataFrame(items)


def get_current_air_quality(station: str = DEFAULT_STATION) -> dict[str, Any]:
    """현재 대기질을 구조화된 딕셔너리로 반환."""
    items = fetch_station_realtime(station)
    if not items:
        return {}

    latest = items[0]
    result = {
        "timestamp": latest.get("dataTime", ""),
        "station": latest.get("stationName", station),
    }

    for api_field, meta in ICO_MAPPING.items():
        raw = latest.get(api_field, "-")
        try:
            val = float(raw)
        except (ValueError, TypeError):
            val = None
        result[api_field] = val
        result[f"{api_field}_grade"] = latest.get(api_field.replace("Value", "Grade"), "-")

    result["khaiValue"] = latest.get("khaiValue", "-")
    result["khaiGrade"] = latest.get("khaiGrade", "-")

    # PM2.5 면역 영향 판정
    pm25 = result.get("pm25Value")
    if pm25 is not None:
        for threshold, grade, comment in PM25_IMMUNE_GRADES:
            if pm25 <= threshold:
                result["pm25_immune_grade"] = grade
                result["pm25_immune_comment"] = comment
                break

    return result


# ─────────────────────────────────────────────────────────────
# Composite Index Integration
# ─────────────────────────────────────────────────────────────

def compute_oxidative_stress_load(
    pm25: float,
    voc_index: float = 0.0,
    o3_ppm: float = 0.0,
) -> float:
    """OxidativeStressLoad 산출 (ico:OxidativeStressLoad).

    공식: OSL = PM2.5_norm × 0.5 + VOC_norm × 0.3 + O3_norm × 0.2
    정규화: PM2.5 max=150μg/m³, VOC max=500, O3 max=0.15ppm

    Args:
        pm25: PM2.5 농도 (μg/m³)
        voc_index: VOC index (0-500). 에어코리아에서 미제공, IoT센서 필요.
        o3_ppm: 오존 농도 (ppm)

    Returns:
        OSL score (0-100)
    """
    pm25_norm = min(pm25 / 150.0 * 100, 100)
    voc_norm = min(voc_index / 500.0 * 100, 100)
    o3_norm = min(o3_ppm / 0.15 * 100, 100) if o3_ppm > 0 else 0

    osl = pm25_norm * 0.5 + voc_norm * 0.3 + o3_norm * 0.2
    return round(float(np.clip(osl, 0, 100)), 2)


# ─────────────────────────────────────────────────────────────
# RDF Triple Generation
# ─────────────────────────────────────────────────────────────

def air_quality_to_ico_triples(aq: dict[str, Any], patient_id: str = "P001") -> str:
    """대기질 데이터를 ICO RDF 트리플(Turtle)로 변환."""
    ts = aq.get("timestamp", datetime.now().isoformat())
    ts_clean = ts.replace(":", "").replace("-", "").replace(" ", "T")[:15]

    lines = [
        "@prefix ico: <http://purl.obolibrary.org/obo/ICO#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]

    for api_field, meta in ICO_MAPPING.items():
        val = aq.get(api_field)
        if val is not None:
            obs_id = f"ico:airkorea_{api_field}_{patient_id}_{ts_clean}"
            lines.append(f"{obs_id} a {meta['ico_class']} ;")
            lines.append(f'    rdfs:label "{meta["name_ko"]} 측정"@ko ;')
            lines.append(f'    ico:hasValue "{val}"^^xsd:float ;')
            lines.append(f'    ico:hasUnit "{meta["unit"]}"^^xsd:string ;')
            lines.append(f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .')
            lines.append("")

    # OSL 복합지표
    pm25 = aq.get("pm25Value")
    o3 = aq.get("o3Value")
    if pm25 is not None:
        osl = compute_oxidative_stress_load(pm25, 0, o3 or 0)
        lines.append(f"ico:airkorea_osl_{patient_id}_{ts_clean} a ico:OxidativeStressLoad ;")
        lines.append(f'    rdfs:label "산화스트레스 부하 (에어코리아)"@ko ;')
        lines.append(f'    ico:hasValue "{osl}"^^xsd:float ;')
        lines.append(f'    ico:hasUnit "score_0_100"^^xsd:string ;')
        lines.append(f'    ico:hasTimestamp "{ts}"^^xsd:dateTime .')
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  에어코리아 대기오염 수집기 — Digital Columbus / KIMS         ║")
    print("║  AirKorea Collector for Immune Care Ontology                ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    try:
        # 실시간 데이터 조회
        print("=== 1. 창원 성산 실시간 대기질 ===")
        aq = get_current_air_quality()
        for k, v in aq.items():
            print(f"  {k:25s}: {v}")
        print()

        # 경남 전체
        print("=== 2. 경남 시도별 측정 ===")
        df = fetch_sido_realtime("경남")
        cols = ["stationName", "pm25Value", "pm10Value", "o3Value", "no2Value", "dataTime"]
        print(df[cols].head(10).to_string(index=False))
        print()

        # ICO 트리플
        print("=== 3. ICO RDF 트리플 ===")
        ttl = air_quality_to_ico_triples(aq)
        print(ttl)

    except PermissionError as e:
        print(f"⚠️  API 접근 거부: {e}")
        print()
        print("=== API 키 미활성화 — 시뮬레이션 모드 ===")
        print()

        # 시뮬레이션 데이터로 기능 검증
        mock_aq = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "station": "성산 (시뮬레이션)",
            "pm25Value": 28.0,
            "pm25Value_grade": "2",
            "pm10Value": 45.0,
            "pm10Value_grade": "2",
            "o3Value": 0.035,
            "o3Value_grade": "1",
            "no2Value": 0.025,
            "coValue": 0.5,
            "so2Value": 0.003,
            "khaiValue": "72",
            "khaiGrade": "2",
            "pm25_immune_grade": "보통",
            "pm25_immune_comment": "장기 노출 시 면역 저하 가능",
        }

        print("--- 시뮬레이션 대기질 데이터 ---")
        for k, v in mock_aq.items():
            print(f"  {k:25s}: {v}")
        print()

        osl = compute_oxidative_stress_load(mock_aq["pm25Value"], 0, mock_aq["o3Value"])
        print(f"  OxidativeStressLoad: {osl}/100 (VOC 미포함)")
        print()

        print("--- ICO RDF 트리플 (시뮬레이션) ---")
        ttl = air_quality_to_ico_triples(mock_aq)
        print(ttl)

        print()
        print("=== 활성화 확인 방법 ===")
        print("  1. https://www.data.go.kr 로그인")
        print("  2. 마이페이지 → API 활용 → 승인 상태 확인")
        print("  3. '승인' 확인 후 이 스크립트 재실행")
        print()
        print("✅ 수집기 코드 준비 완료 — API 키 활성화 대기 중")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"⚠️  403 Forbidden — API 키 활성화 대기 중")
            print("  data.go.kr에서 '에어코리아_대기오염정보' 신청 상태 확인 필요")
        else:
            raise
