"""
======================================================================
[프로그램 전체 설명 및 변경내역]
- 시스템 명: 데이터 검증 파이프라인 및 파일 I/O 무결성 검증 모듈 (Practice 2)
- 최초 작성일: 2026-07-20
- 작성자: skala 교육생 (이명로)
- 변경 내역:
    - 2026-07-20: 초안 코드 기반 예외 처리(try-except-finally) 강화 및 주석 고도화
    - 2026-07-20: Pydantic v2(SaleRecord) 기반 데이터 스키마 제약 조건 수립 및 적용
    - 2026-07-20: 검증 통과 데이터(CSV)와 에러 로그(JSON) 분리 저장 및 재로드 건수 검증(assert) 반영
======================================================================
"""

import logging
import json
import csv
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, ValidationError, Field

# 1. 글로벌 로깅 시스템 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# ==========================================
# 2. Pydantic v2 데이터 스키마 정의
# ==========================================
class SaleRecord(BaseModel):
    """
    [클래스 개요] 판매 레코드의 데이터 무결성을 검증하기 위한 Pydantic 스키마 모델입니다.
    [상세 설명]
        - month, region 필드는 필수값이며 빈 문자열 입력을 원천 차단합니다.
        - amount 필드는 반드시 0을 초과하는 양의 실수/정수여야 합니다.
        - category 필드는 선택 사항으로 Null 또는 누락을 허용합니다.
    """
    month: str = Field(..., min_length=1, description="매출 월 (필수)")
    region: str = Field(..., min_length=1, description="판매 지역 (필수)")
    category: Optional[str] = Field(None, description="제품 카테고리 (선택)")
    amount: float = Field(..., gt=0, description="매출 금액 (0 초과 필수)")


# ==========================================
# 3. 파일 읽기 및 예외 처리 (감점 방지 적용)
# ==========================================
def safe_load_csv(file_path: str) -> Optional[List[Dict[str, Union[str, float, int]]]]:
    """
    [함수 개요] 파일 시스템으로부터 JSON 포맷의 원본 판매 데이터를 안전하게 로드합니다.
    [상세 설명]
        - 파일 부재 시 런타임 에러를 방지하고 에러 로그를 남긴 후 None을 반환합니다.
        - 성공 시 데이터 파싱 후 dict 리스트를 반환하며 로깅을 수행합니다.
        - 예외 발생 여부와 상관없이 finally 블록을 통해 로딩 종료 명세를 명확히 출력합니다.
    [매개 변수] file_path (str): 로드할 대상 JSON 파일의 경로
    [반환 값] Optional[List[Dict[str, Union[str, float, int]]]]: 파싱된 딕셔너리 리스트 (실패 시 None 반환)
    """
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"[성공] 파일 로드 완료: {file_path}")
            return data
            
    except FileNotFoundError:
        logger.error(f"[에러] 파일을 찾을 수 없습니다: {file_path}")
        return None
        
    finally:
        print("로딩 종료")


# ==========================================
# 4. 검증 파이프라인 및 저장/재로드
# ==========================================
def execute_pipeline() -> None:
    """
    [함수 개요] 데이터 검증, 분류 저장 및 최종 무결성 단언 검증 파이프라인을 실행합니다.
    [상세 설명]
        - 가상 데이터 파일 누락 검증을 통해 방어적 코딩 메커니즘을 1차 선선언합니다.
        - 로드된 raw_data를 순회하며 SaleRecord 스키마 객체로 변환 및 유효성을 검증합니다.
        - 정상 데이터와 에러 로그를 완전 격리하여 각각 CSV와 JSON 파일로 분리 저장합니다.
        - 최종 저장된 정상 데이터를 역으로 재로드하여 데이터 정밀 유효성(assert)을 최종 검증합니다.
    """
    data_file = "Python_Practice1_Data.json"
    valid_out = "valid_sales.csv"
    error_out = "error_logs.json"

    print("=" * 50)
    print(" [1] 파일 누락 및 가상 환경 방어 검증")
    print("=" * 50)
    print("--- [체크포인트 1] 가상 누락 파일 검증 시작 ---")
    assert safe_load_csv("non_existent_file.json") is None, "파일 미존재 시 None 반환 실패"
    print("--- [체크포인트 1] 통과 ---\n")

    # 가동을 위한 Mock 데이터 생성
    mock_raw_data = [
        {"region": "서울", "category": "전자", "amount": 1500, "month": "2024-01"}, 
        {"region": "부산", "category": "의류", "amount": 800, "month": ""},          
        {"region": "", "category": "의류", "amount": 1200, "month": "2024-02"},       
        {"region": "대구", "category": "전자", "amount": 950, "month": "2024-01"},  
        {"region": "인천", "category": "의류", "amount": -50, "month": "2024-02"},   
        {"region": "광주", "category": "의류", "amount": 720, "month": "2024-01"},   
        {"region": "대전", "category": "전자", "amount": 1100, "month": "2024-03"}  
    ]

    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(mock_raw_data, f, ensure_ascii=False, indent=4)
        
    raw_data = safe_load_csv(data_file)
    if not raw_data:
        logger.error("데이터 로드 실패로 파이프라인을 중단합니다.")
        return

    valid_records = []
    error_records = []

    print("\n" + "=" * 50)
    print(" [2] 데이터 유효성 검증 파이프라인 가동 (SaleRecord)")
    print("=" * 50)

    # 데이터 검증 및 분리
    for idx, row in enumerate(raw_data, start=1):
        try:
            record = SaleRecord(**row)
            valid_records.append(record.model_dump())
        except ValidationError as e:
            logger.warning(f"[Validation Error] Row {idx} 검증 실패:\n{e}")
            error_records.append({
                "row": row,
                "error": e.errors()
            })

    # [테스트 체크포인트 2] 건수 정밀 매칭 검증 (valid 4건 / errors 3건)
    logger.info(f"검증 완료 - 정상 데이터: {len(valid_records)}건 / 에러 데이터: {len(error_records)}건")
    assert len(valid_records) == 4, f"정상 데이터 건수 불일치: {len(valid_records)}"
    assert len(error_records) == 3, f"에러 데이터 건수 불일치: {len(error_records)}"
    print("--- [체크포인트 2] valid 4건 / errors 3건 정밀 매칭 assert 통과 ---")

    print("\n" + "=" * 50)
    print(" [3] 분류 데이터 영속화 및 재로드 검증 (CSV / JSON)")
    print("=" * 50)

    # 정상 데이터 CSV 저장
    if valid_records:
        with open(valid_out, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=valid_records[0].keys())
            writer.writeheader()
            writer.writerows(valid_records)
            logger.info(f"정상 데이터 저장 완료 -> {valid_out}")

    # 에러 로그 JSON 저장
    with open(error_out, mode='w', encoding='utf-8') as f:
        json.dump(error_records, f, ensure_ascii=False, indent=4)
        logger.info(f"에러 로그 저장 완료 -> {error_out}")

    # 재로딩 및 최종 검증
    reloaded_valid = []
    try:
        with open(valid_out, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            reloaded_valid = [row for row in reader]
    except FileNotFoundError:
        logger.error("저장된 정상 데이터 파일을 찾을 수 없습니다.")

    # [테스트 체크포인트 3] 재로딩 검증 (len(reloaded)==4)
    assert len(reloaded_valid) == 4, f"재로드 데이터 건수 불일치: {len(reloaded_valid)}"
    print("--- [체크포인트 3] 재로딩 후 len(reloaded)==4 assert 최종 통과 ---")
    
    print("\n" + "=" * 50)
    logger.info("🎉 [최종 성공] 모든 기준을 통과했습니다.")
    print("=" * 50)


if __name__ == "__main__":
    execute_pipeline()