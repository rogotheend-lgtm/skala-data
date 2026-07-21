"""
================================================================================
프로그램명 : 종합 실습 실무형 파이프라인 유닛 테스트 자동화 스크립트
소      속 : 광주캠퍼스 2반
작  성  자 : 이명로
최초 작성일 : 2026-07-20
최종 수정일 : 2026-07-20
주요 기능  :
    1. pytest 프레임워크 기반의 데이터 검증 레이어 독립 단위 테스트(Unit Test)
    2. WeatherModel의 복합 데이터 구조(Union 타입 및 중첩 Dict/List) 정상 검증 평가
    3. CountryModel의 API 필드 역직렬화(Alias 매핑) 및 Fallback 데이터 구조 정합성 검증
    4. IPModel의 필수 필드(query) 누락 상황에 대한 ValidationError 예외 포착 테스트
변경 이력  :
    - 2026-07-20 | 이명로 | 최초 유닛 테스트 코드 구현 및 스키마 검증 시나리오 설계 완료
    - 2026-07-20 | 이명로 | Pytest-9.1.1 환경 구동 테스트 및 3건 전원 PASSED 확인 완료
================================================================================
"""

import pytest
from pydantic import ValidationError
from pipeline import WeatherModel, CountryModel, IPModel


def test_weather_model_validation_success():
    """
    [Test Case 1] Weather 모델의 정상 데이터 및 다형성 타입 검증
    - 목적: 복잡한 런타임 환경에서 문자열(str)과 숫자형(float, int)이 혼재된 Union 구조를
           Pydantic v2 가 안전하게 유효성 검증을 통과시키는지 확인
    """
    valid_data = {
        "latitude": 37.5665,
        "longitude": 126.978,
        "timezone": "Asia/Seoul",
        "hourly": {
            "time": [
                "2026-07-21T12:00",
                "2026-07-21T13:00",
            ],  # ISO 타임스탬프 문자열 수용 검증
            "temperature_2m": [24.5, 25.0],  # 부동 소수점 데이터 수용 검증
        },
    }
    # 데이터 파싱 및 객체화 수행
    model = WeatherModel(**valid_data)

    # 정적 타이핑 및 값 검증 단언(Assert)
    assert model.latitude == 37.5665
    assert "time" in model.hourly


def test_country_model_fallback_structure():
    """
    [Test Case 2] Country 모델의 필드 매핑 및 Fallback 데이터 규격 검증
    - 목적: API 제공처의 로우(Raw) 필드명('alpha2')이 내부 데이터 표준 스키마 필드명('alpha2Code')으로
           Alias 매핑 규칙에 따라 결함 없이 역직렬화되는지 검증
    """
    mock_api_data = {
        "name": "South Korea (Fallback)",
        "alpha2": "KR",  # 스키마 내부에서 alpha2Code로 변환되어야 함
        "capital": "Seoul",
    }
    # 데이터 파싱 및 객체화 수행
    model = CountryModel(**mock_api_data)

    # Alias 필드 매핑 정합성 단언(Assert)
    assert model.name == "South Korea (Fallback)"
    assert model.alpha2Code == "KR"


def test_ip_model_validation_failure():
    """
    [Test Case 3] IP 모델의 필수 필드 누락 시 방어 로직 검증
    - 목적: 시스템의 핵심 키 값인 클라이언트 IP 주소('query')가 누락된 비정상 데이터 유입 시,
           임의로 처리되지 않고 Pydantic의 ValidationError를 명확하게 발생시켜 데이터 오염을 막는지 확인
    """
    invalid_data = {
        "status": "fail",
        "country": "United States",
        # 의도적으로 필수 필드인 'query'를 누락시켜 에러 시뮬레이션 수행
    }

    # 예외(ValidationError)가 반드시 발생해야 패스되는 컨텍스트 매니저 구성
    with pytest.raises(ValidationError):
        IPModel(**invalid_data)
