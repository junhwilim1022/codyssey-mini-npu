"""십자가와 X 패턴을 MAC 점수로 판별하는 콘솔 프로그램."""

import json
import re
from pathlib import Path
from time import perf_counter
from math import isfinite


DATA_PATH = Path(__file__).resolve().parent / "data.json"
EPSILON = 1e-9
REPEATS = 10
SIZES = (3, 5, 13, 25)


def check_matrix(matrix, size):
    """행렬이 지정한 크기의 숫자 배열인지 확인한다."""
    if not isinstance(matrix, list) or len(matrix) != size:
        raise ValueError(f"행 수가 {size}개가 아닙니다.")
    for row_number, row in enumerate(matrix, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(f"{row_number}번째 행의 열 수가 {size}개가 아닙니다.")
        if any(type(value) not in (int, float) or not isfinite(value) for value in row):
            raise ValueError(f"{row_number}번째 행에 유효하지 않은 숫자가 있습니다.")


def mac(pattern, filter_matrix):
    """같은 위치의 값을 곱해서 모두 더한다. (외부 라이브러리 미사용)"""
    total = 0.0
    size = len(pattern)
    for row in range(size):
        for col in range(size):
            total += pattern[row][col] * filter_matrix[row][col]
    return total


def normalize_label(value):
    """데이터에 사용된 +/cross/x를 Cross/X로 통일한다."""
    if not isinstance(value, str):
        raise ValueError("라벨이 문자열이 아닙니다.")
    name = value.strip().lower()
    if name in ("+", "cross"):
        return "Cross"
    if name == "x":
        return "X"
    raise ValueError(f"지원하지 않는 라벨: {value!r}")


def decide(score_a, score_b, name_a="A", name_b="B"):
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return name_a if score_a > score_b else name_b


def create_pattern(size, kind):
    """성능 측정에 사용할 십자가 또는 X 패턴을 만든다."""
    center = size // 2
    result = []
    for row in range(size):
        values = []
        for col in range(size):
            if kind == "Cross":
                on = row == center or col == center
            else:
                on = row == col or row + col == size - 1
            values.append(1.0 if on else 0.0)
        result.append(values)
    return result


def average_mac_ms(pattern, filter_matrix, repeats=REPEATS):
    """파일 읽기와 출력 시간을 제외하고 MAC 호출만 측정한다."""
    # 초기 실행의 영향은 줄이되 워밍업 시간은 측정에 포함하지 않는다.
    for _ in range(3):
        mac(pattern, filter_matrix)
    durations = []
    for _ in range(repeats):
        start = perf_counter()
        mac(pattern, filter_matrix)
        durations.append((perf_counter() - start) * 1000)
    return sum(durations) / len(durations), min(durations), max(durations)


def performance_report(filters=None):
    print("\n[성능 분석] (각 크기별 MAC 10회 평균)")
    print(f"{'크기':<10} {'평균(ms)':>12} {'최소(ms)':>12} {'최대(ms)':>12} {'연산 횟수(N²)':>16}")
    print("-" * 70)
    for size in SIZES:
        sample = create_pattern(size, "Cross")
        filter_matrix = sample
        if filters is not None and size != 3:
            group = filters.get(f"size_{size}")
            if isinstance(group, dict) and "cross" in group:
                try:
                    check_matrix(group["cross"], size)
                    filter_matrix = group["cross"]
                except ValueError:
                    pass
        average, minimum, maximum = average_mac_ms(sample, filter_matrix)
        print(f"{size}×{size:<7} {average:>12.6f} {minimum:>12.6f} {maximum:>12.6f} {size * size:>16}")
    print("※ 실행 환경에 따라 측정 시간은 달라질 수 있습니다.")


def read_matrix(title, size=3):
    print(f"\n{title} ({size}줄, 한 줄에 숫자 {size}개)")
    matrix = []
    while len(matrix) < size:
        try:
            raw = input(f"{len(matrix) + 1}행> ").split()
            if len(raw) != size:
                raise ValueError(f"각 줄에 {size}개의 숫자가 필요합니다.")
            row = [float(value) for value in raw]
            if not all(isfinite(value) for value in row):
                raise ValueError("유한한 숫자만 입력할 수 있습니다.")
            matrix.append(row)
        except ValueError:
            print(f"입력 형식 오류: 각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요.")
            print("올바른 예시: 0 1 0")
    return matrix


def manual_mode():
    print("\n[1] 필터 입력")
    a = read_matrix("필터 A")
    b = read_matrix("필터 B")
    print("\n필터 A, B 저장 완료")
    print("\n[2] 패턴 입력")
    pattern = read_matrix("패턴")
    score_a = mac(pattern, a)
    score_b = mac(pattern, b)
    result = decide(score_a, score_b)
    print("\n[3] MAC 결과")
    print(f"A 점수: {score_a:.16g}")
    print(f"B 점수: {score_b:.16g}")
    print("판정: " + ("판정 불가 (UNDECIDED)" if result == "UNDECIDED" else result))
    average, minimum, maximum = average_mac_ms(pattern, a)
    print(f"연산 시간(평균/10회): {average:.6f} ms (A 필터 기준)")
    print("\n[성능 분석: 입력한 3×3 패턴 기준]")
    print(f"3×3 | 평균 {average:.6f} ms | 최소 {minimum:.6f} ms | 최대 {maximum:.6f} ms | 연산 횟수 9")


def get_filters(data):
    filters = data.get("filters")
    if not isinstance(filters, dict):
        raise ValueError("filters가 없거나 객체 형태가 아닙니다.")
    result = {}
    print("\n[1] 필터 로드")
    for size in (5, 13, 25):
        size_key = f"size_{size}"
        group = filters.get(size_key)
        if not isinstance(group, dict):
            print(f"! {size_key}: 필터 정보 없음")
            continue
        try:
            normalized = {}
            for raw_label, matrix in group.items():
                label = normalize_label(raw_label)
                if label in normalized:
                    raise ValueError(f"{label} 필터가 중복됩니다.")
                check_matrix(matrix, size)
                normalized[label] = matrix
            if set(normalized) != {"Cross", "X"}:
                raise ValueError("Cross와 X 필터가 모두 필요합니다.")
            result[size_key] = normalized
            print(f"✓ {size_key}: Cross, X 로드 완료")
        except ValueError as exc:
            print(f"! {size_key}: 필터 오류 ({exc})")
    return result


def analyze_case(case_id, case, filters):
    matched = re.fullmatch(r"size_(\d+)_(\d+)", case_id)
    if not matched:
        raise ValueError("케이스 키 형식 오류 (size_N_idx 필요)")
    size = int(matched.group(1))
    key = f"size_{size}"
    if key not in filters:
        raise ValueError(f"{key} 필터가 없거나 유효하지 않습니다.")
    if not isinstance(case, dict):
        raise ValueError("케이스 데이터 형식 오류")
    pattern = case.get("input")
    check_matrix(pattern, size)
    expected = normalize_label(case.get("expected"))
    cross = mac(pattern, filters[key]["Cross"])
    x_score = mac(pattern, filters[key]["X"])
    prediction = decide(cross, x_score, "Cross", "X")
    if prediction != expected:
        reason = "동점 처리 규칙에 따른 판정 불가" if prediction == "UNDECIDED" else "예상 라벨과 판정 결과 불일치"
    else:
        reason = ""
    return cross, x_score, prediction, expected, reason


def json_mode():
    try:
        with DATA_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("최상위 JSON은 객체여야 합니다.")
        patterns = data.get("patterns")
        if not isinstance(patterns, dict):
            raise ValueError("patterns가 없거나 객체 형태가 아닙니다.")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"data.json을 읽을 수 없습니다: {exc}")
        return

    filters = get_filters(data)
    total = len(patterns)
    passed = 0
    failures = []
    print("\n[2] 패턴 분석")
    for case_id, case in patterns.items():
        print(f"\n--- {case_id} ---")
        try:
            cross, x_score, prediction, expected, reason = analyze_case(case_id, case, filters)
            print(f"Cross 점수: {cross:.16g}")
            print(f"X 점수: {x_score:.16g}")
            status = "PASS" if not reason else "FAIL"
            print(f"판정: {prediction} | expected: {expected} | {status}" + (f" ({reason})" if reason else ""))
            if reason:
                failures.append((case_id, reason, cross, x_score, expected, prediction))
            else:
                passed += 1
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            reason = str(exc)
            print(f"FAIL ({reason})")
            failures.append((case_id, reason, None, None, None, None))

    performance_report(data["filters"] if isinstance(data.get("filters"), dict) else None)
    print("\n[4] 결과 요약")
    print(f"총 테스트: {total}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(failures)}개")
    if failures:
        print("실패 케이스:")
        for name, reason, cross, x_score, expected, prediction in failures:
            print(f"- {name}: {reason}")
            if cross is not None:
                print(f"  Cross={cross:.16g}, X={x_score:.16g}, expected={expected}, 판정={prediction}")
    else:
        print("실패 케이스 없음")


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3×3)")
    print("2. data.json 분석")
    while True:
        choice = input("선택: ").strip()
        if choice == "1":
            manual_mode()
            break
        if choice == "2":
            json_mode()
            break
        print("1 또는 2를 입력하세요.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n프로그램을 종료합니다.")
