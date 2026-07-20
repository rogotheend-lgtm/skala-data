"""
================================================================================
프로그램명 : 종합 실습 실무형 비동기 수집·검증·성능평가 파이프라인
소      속 : 광주캠퍼스 2반
작  성  자 : 이명로
최초 작성일 : 2026-07-20
최종 수정일 : 2026-07-20
주요 기능  :
    1. asyncio 및 httpx를 이용한 I/O Bound 외부 API 비동기 병렬 수집 (속도 최적화)
    2. Pydantic v2 기반의 다중 도메인(Weather/Country/IP) 스키마 정의 및 Union 검증
    3. 외부 API 장애 상황에 대응하는 try-except 기반 가상 데이터 매핑(Fallback) 레이어 구현
    4. 대용량(5,000행 확장) 시뮬레이션 환경 구축을 통한 CSV 및 Parquet I/O 성능 벤치마크
    5. ruff 정적 분석 규격 및 typing.Any 제거를 통한 정적 타이핑 무결성 확보
변경 이력  :
    - 2026-07-20 | 이명로 | 최초 비동기 파이프라인 및 스키마 검증 설계 완료
    - 2026-07-20 | 이명로 | typing.Any 제거 및 Ruff 린터 컨벤션 준수 리팩토링 완료
    - 2026-07-20 | 이명로 | 외부 API 장애 전파 방지를 위한 결함 허용(Fallback) 메커니즘 고도화
================================================================================
"""

import os
import time
import asyncio
from typing import Dict, Optional, List, Union
from dotenv import load_dotenv
import httpx
import pandas as pd
from pydantic import BaseModel, Field

# 환경 변수 로드 (.env 보안 격리)
load_dotenv()

# ==========================================
# [Step 1] Pydantic v2 데이터 스키마 정의
# ==========================================

class WeatherModel(BaseModel):
    """날씨 API 응답 스키마: 유연한 데이터 처리를 위해 리스트 내부 Union 타입 적용"""
    latitude: float
    longitude: float
    timezone: str
    # API 제공처의 사정에 따라 데이터 타입이 혼재될 수 있으므로 Union 설정
    hourly: Dict[str, List[Union[str, float, int]]]

class CountryModel(BaseModel):
    """국가 API 응답 스키마: 필드명 매핑 및 유효성 검증"""
    name: str
    # API의 'alpha2' 필드를 내부적으로 'alpha2Code'로 매핑하여 일관성 유지
    alpha2Code: str = Field(alias="alpha2")
    capital: str

class IPModel(BaseModel):
    """IP API 응답 스키마: 필수 필드 누락 검증"""
    status: str
    country: str
    query: str  # 클라이언트의 실제 IP 주소가 담기는 필수 필드


# ==========================================
# [Step 2] 비동기 데이터 수집 및 Fallback 엔진
# ==========================================

async def fetch_weather() -> Dict:
    """Open-Meteo 비동기 날씨 데이터 수집 (장애 시 가상 데이터 반환)"""
    url = "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&hourly=temperature_2m"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                return response.json()
            raise httpx.HTTPStatusError("API 응답 에러", request=response.request, response=response)
        except Exception as e:
            print(f"[⚠] Weather API 장애 발생 -> Fallback 데이터로 전환: {e}")
            # 시스템 중단을 막기 위한 정상 규격의 가상(Fallback) 데이터 매핑
            return {
                "latitude": 37.5665, "longitude": 126.978, "timezone": "Asia/Seoul",
                "hourly": {"time": ["2026-07-20T16:00"], "temperature_2m": [25.0]}
            }

async def fetch_country() -> Dict:
    """국가 정보 API 비동기 수집 (장애 시 가상 데이터 반환)"""
    url = "https://api.api-ninjas.com/v1/country?name=south korea"
    headers = {"X-Api-Key": os.getenv("NINJA_API_KEY", "")}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200 and response.json():
                return response.json()[0]
            raise httpx.HTTPStatusError("API 응답 에러", request=response.request, response=response)
        except Exception as e:
            print(f"[⚠] Country API 장애 발생 -> Fallback 데이터로 전환: {e}")
            return {"name": "South Korea (Fallback)", "alpha2": "KR", "capital": "Seoul"}

async def fetch_ip() -> Dict:
    """IP-API 비동기 수집 (장애 시 가상 데이터 반환)"""
    url = "http://ip-api.com/json/"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                return response.json()
            raise httpx.HTTPStatusError("API 응답 에러", request=response.request, response=response)
        except Exception as e:
            print(f"[⚠] IP API 장애 발생 -> Fallback 데이터로 전환: {e}")
            return {"status": "success", "country": "South Korea", "query": "127.0.0.1"}


# ==========================================
# [Step 3] 비동기 오케스트레이션 및 메인 파이프라인
# ==========================================

async def main():
    print("[🚀] 비동기 동시성 기반 데이터 파이프라인 가동 시작...")
    start_time = time.time()

    # asyncio.gather를 통한 3대 API 병렬 요청 최적화 (가장 느린 API 시간으로 수집 수렴)
    raw_weather, raw_country, raw_ip = await asyncio.gather(
        fetch_weather(),
        fetch_country(),
        fetch_ip()
    )
    
    print(f"[✔] 비동기 동시성 수집 완료! 소요 시간: {time.time() - start_time:.4f}초")

    # Pydantic을 이용한 데이터 엄격 검증 및 객체 변환 (Any 타입 완전 배제)
    weather_obj = WeatherModel(**raw_weather)
    country_obj = CountryModel(**raw_country)
    ip_obj = IPModel(**raw_ip)
    print("[✔] Pydantic v2 데이터 유효성 검증 레이어 전원 통과")

    # 통합 데이터 가공 (Pandas 변환용 딕셔너리 구조화)
    integrated_data = {
        "user_ip": ip_obj.query,
        "country_name": country_obj.name,
        "country_code": country_obj.alpha2Code,
        "capital": country_obj.capital,
        "target_latitude": weather_obj.latitude,
        "target_longitude": weather_obj.longitude,
        "current_temp": weather_obj.hourly["temperature_2m"][0]
    }

    # 5,000행 대용량 확장 시뮬레이션 (스토리지 I/O 벤치마크 목적)
    print("\n[📊] 5,000행 대용량 데이터 파일 포맷별 I/O 성능 비교 테스트 시작...")
    df_large = pd.DataFrame([integrated_data] * 5000)

    # 1) CSV 포맷 입출력 및 성능 분석
    csv_start = time.time()
    df_large.to_csv("pipeline_result.csv", index=False, encoding="utf-8-sig")
    csv_write_time = time.time() - csv_start

    csv_read_start = time.time()
    _ = pd.read_csv("pipeline_result.csv")
    csv_read_time = time.time() - csv_read_start
    print(f"  - [CSV] 쓰기 속도: {csv_write_time:.4f}초 | 읽기 속도: {csv_read_time:.4f}초")

    # 2) Parquet 포맷 입출력 및 성능 분석 (고부가 스토리지 포맷)
    parquet_start = time.time()
    df_large.to_parquet("pipeline_result.parquet", index=False, compression="snappy")
    parquet_write_time = time.time() - parquet_start

    parquet_read_start = time.time()
    _ = pd.read_parquet("pipeline_result.parquet")
    parquet_read_time = time.time() - parquet_read_start
    print(f"  - [Parquet] 쓰기 속도: {parquet_write_time:.4f}초 | 읽기 속도: {parquet_read_time:.4f}초")
    
    print("\n[🏁] 종합 파이프라인 전체 프로세스가 정상 종료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())