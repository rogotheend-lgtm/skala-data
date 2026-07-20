"""
======================================================================
[프로그램 전체 설명 및 변경내역]
- 시스템 명: 대용량 판매 데이터 집계 및 메모리 최적화 검증 모듈 (Practice 1)
- 최초 작성일: 2026-07-20
- 작성자: 실무 개발자 (이명로)
- 변경 내역:
    - 2026-07-20: 초안 코드 기반 예외 처리 강화 및 주석 고도화
    - 2026-07-20: 'Counter.most_common()'을 통한 지역별 건수 정렬 기능 추가
    - 2026-07-20: 'category_amount' 기준 상위 3개(top3) 금액 내림차순 정렬 요구사항 반영
======================================================================
"""

import sys
import ast
from collections import Counter, defaultdict

def load_data_safely(file_path): 
    """
    [함수 개요] 파일 시스템으로부터 판매 데이터를 안전하게 로드합니다.
    [상세 설명] 
        - 순수 JSON 형식이 아닌 'sales = [...]' 형태의 파이썬 리터럴 구조를 처리합니다.
        - 파일 부재 및 파싱 에러에 대해 시스템 다운(Crash)을 방지하는 방어적 코딩을 적용했습니다.
    [매개 변수] file_path (str): 읽어올 데이터 파일의 경로
    [반환 값] list: 파싱된 데이터 리스트 (오류 발생 시 빈 리스트 [] 반환)
    """
    try:
        with open(file_path, 'r', encoding="utf-8") as f:
            content = f.read().strip()

            # 파이썬 할당 연산자 분리 및 순수 리스트 추출
            if content.startswith('sales = '):
                content = content.replace('sales =', '', 1).strip()

            # ast.literal_eval을 통한 안전한 파이썬 객체 변환
            data = ast.literal_eval(content)
            return data
            
    except FileNotFoundError: 
        print(f"[Error] 파일을 찾을 수 없습니다: {file_path}")
        return []
    except Exception as e: 
        print(f"[Error] 데이터 파싱 중 예외 발생: {e}")
        return []

def analyze_sales(data): 
    """
    [함수 개요] 로드된 데이터를 기반으로 통계 집계 및 메모리 최적화 검증을 수행합니다.
    [상세 설명]
        - Counter를 활용하여 지역별 건수를 카운팅하고 빈도수 기준 정렬을 수행합니다.
        - defaultdict를 활용하여 카테고리별 누적 금액을 계산하고, 상위 3개 항목을 내림차순 정렬합니다.
        - 리스트 컴프리헨션과 제너레이터의 메모리 점유 크기를 sys.getsizeof로 비교 증명합니다.
    [매개 변수] data (list): 분석 대상 데이터 리스트
    """
    if not data:
        print("[Warning] 분석할 데이터가 존재하지 않습니다.")
        return
    
    print("=" * 50)
    print(" [1] 데이터 집계 및 최적화 (Counter / defaultdict)")
    print("=" * 50)

    # 1) Counter.most_common()을 적용하여 빈도수 기준 순서 정확도 확보 
    region_counter = Counter(item.get('region', '미분류') for item in data)
    print("■ 지역별 판매 건수 (빈도순):")
    for region, count in region_counter.most_common():
        print(f"  - {region}: {count}건")

    # 2) defaultdict를 이용한 카테고리별 집계 
    category_amount = defaultdict(int)
    for item in data:
        category = item.get('category', '미분류')
        amount = item.get('amount', 0)
        category_amount[category] += amount

    # 3) 상위 3개(top3) 금액 내림차순 정렬 정확도 확보 
    # sorted_categories 구조: [('전자', 55100), ('의류', 33220), ...]
    sorted_categories = sorted(category_amount.items(), key=lambda x: x[1], reverse=True)[:3]

    print('\n■ 카테고리별 총 판매 금액 (Top 3 내림차순):')
    for category, total in sorted_categories:
        print(f"  - {category}: {total:,}원")

    print("\n" + "=" * 50)
    print(' [2] 메모리 최적화 검증 (sys.getsizeof)')
    print("=" * 50)

    # 4) 리스트 컴프리헨션 vs 제너레이터 표현식 선언 
    list_comp = [item for item in data if item.get('amount', 0) >= 1000]
    gen_expr = (item for item in data if item.get('amount', 0) >= 1000)

    # 5) 메모리 크기 측정 및 검증
    size_list = sys.getsizeof(list_comp)
    size_gen = sys.getsizeof(gen_expr)

    print(f"■ 리스트 컴프리헨션 메모리 크기: {size_list} bytes")
    print(f"■ 제너레이터 표현식 메모리 크기: {size_gen} bytes")

    # 단언문을 통한 메모리 효율성 실증 
    assert size_gen < size_list, "[AssertionError] 제너레이터가 리스트보다 메모리를 더 점유하고 있습니다."
    print("\n-> [성공] 제너레이터의 메모리 최적화 효과가 검증되었습니다.")
    print("=" * 50)

# 메인 엔트리 포인트 설정
if __name__ == "__main__": 
    FILE_PATH = "Python_Practice2_Data.json"
    sales_data = load_data_safely(FILE_PATH)
    analyze_sales(sales_data)