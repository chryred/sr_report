# CLAUDE.md — SR 리포팅 자동화 프로젝트 컨텍스트

이 파일은 Claude가 이 프로젝트를 유지보수할 때 참조하는 핵심 컨텍스트입니다.

---

## 프로젝트 개요

**목적**: Jira SR 데이터를 자동 수집·정제하여 Excel 리포트 및 Streamlit 대시보드를 생성
**언어**: Python 3.11+
**가상환경**: `venv/` (항상 `venv/bin/python` 또는 `venv/bin/streamlit` 사용)
**실행 진입점**: `main.py` (CLI), `app.py` (웹 대시보드)

---

## 모듈 역할 및 의존 관계

```
config.py           ← 모든 모듈이 import. 상수·매핑 테이블 단일 관리
    ↓
jira_client.py      ← Jira REST API 수집 / Excel 파일 로드
    ↓
data_processor.py   ← 정제(process) + 통계 생성(generate_summary_stats)
    ↓
report_generator.py ← openpyxl 기반 Excel 리포트 생성 (서식 포함)

app.py              ← Streamlit UI. data_processor + report_generator 호출
main.py             ← argparse CLI. jira_client + data_processor + report_generator 호출
```

**의존 방향은 단방향**입니다. 하위 모듈이 상위 모듈을 import하면 안 됩니다.
예: `data_processor.py`는 `app.py`나 `main.py`를 절대 import하지 않습니다.

---

## 핵심 데이터 흐름

```
[Jira API / Excel 파일]
        ↓  jira_client.load_from_excel() 또는 JiraClient.fetch_issues()
  pd.DataFrame (RAW, ~30컬럼)
        ↓  data_processor.process()
  pd.DataFrame (정제됨: +처리상태, +문의유형, +처리시간_접수(일), +처리시간_해결(일))
        ↓  data_processor.generate_summary_stats()
  dict (stats: total, monthly, rates, inquiry_rates, long_pending, avg_times, ...)
        ↓
  report_generator.generate_report()  →  .xlsx 파일
  app.py 대시보드 렌더링
```

---

## 설정 변경 위치 (config.py)

모든 비즈니스 규칙은 `config.py`에만 존재합니다. 로직 파일을 수정하지 말고 이 파일을 수정하세요.

| 변경 목적 | 수정 위치 |
|-----------|-----------|
| 제외할 Jira 상태 추가 | `EXCLUDED_STATUSES` |
| 제외할 서비스 접두사 추가 | `EXCLUDED_SERVICE_PREFIXES` |
| 상태 → 처리상태 매핑 변경 | `STATUS_MAP` / `DEFAULT_STATUS` |
| 업무유형(FTE) → 문의유형 매핑 추가/변경 | `FTE_TYPE_TO_INQUIRY_TYPE` |
| 문의유형 표시 순서 변경 | `INQUIRY_TYPE_ORDER` |
| 장기 미처리 기준일 변경 | `LONG_PENDING_THRESHOLD_DAYS` |
| Jira 커스텀 필드 ID 수정 | `CUSTOM_FIELD_MAP` |

---

## 코드 컨벤션

### 일반

- **들여쓰기**: 스페이스 4칸
- **최대 줄 길이**: 100자
- **문자열 따옴표**: 큰따옴표(`"`) 우선 사용
- **타입 힌트**: 함수 시그니처에 반드시 사용. 반환형 생략 금지
- **docstring**: 모든 public 함수에 한국어 docstring 작성. 1줄 요약 + Args/Returns 명시

```python
# 좋은 예
def process(df: pd.DataFrame) -> pd.DataFrame:
    """
    RAW 데이터를 정제하여 분석 가능한 형태로 변환

    Args:
        df: Jira에서 수집한 RAW DataFrame

    Returns:
        pd.DataFrame: 처리상태·문의유형·처리시간 컬럼이 추가된 DataFrame
    """
```

### 임포트 순서

```python
# 1. 표준 라이브러리
import os
import logging
from datetime import datetime

# 2. 서드파티
import pandas as pd
import streamlit as st

# 3. 프로젝트 내부 (config 먼저)
from config import INQUIRY_TYPE_ORDER
from data_processor import process
```

### 로깅

- `print()` 사용 금지. 반드시 `logging` 모듈 사용
- 모듈 최상단에 `logger = logging.getLogger(__name__)` 선언
- 레벨 기준: `DEBUG` 상세 내부 값, `INFO` 진행 상황, `WARNING` 데이터 이상, `ERROR` 처리 불가

```python
logger = logging.getLogger(__name__)

# 좋은 예
logger.info(f"데이터 정제 시작: {len(df)}건")
logger.warning(f"날짜 파싱 실패: {value}")

# 나쁜 예
print(f"데이터 정제 시작: {len(df)}건")
```

### 날짜 처리

날짜 파싱은 반드시 `data_processor._parse_datetime()`을 사용합니다.
Jira 생성일 형식(`"2026/02/25 8:08 오전"`)과 Timestamp 객체를 모두 처리합니다.
새로운 날짜 파싱 로직을 별도로 작성하지 마세요.

```python
# 좋은 예
from data_processor import _parse_datetime
ts = _parse_datetime(row["생성일"])

# 나쁜 예 — 직접 파싱 시도 금지
pd.to_datetime(row["생성일"])  # 오전/오후 형식 처리 불가
```

### DataFrame 조작

- `df.copy()`를 명시적으로 호출하여 원본 변경을 방지합니다
- 컬럼명은 Jira 원본 한글명을 유지합니다 (`상태`, `생성일`, `시스템명` 등)
- 정제 후 추가되는 컬럼은 한글 + 의미 명확히: `처리상태`, `문의유형`, `처리시간_접수(일)`

```python
# 좋은 예
df = df[~mask].copy()

# 나쁜 예 — 경고 발생 가능
df = df[~mask]
df["처리상태"] = ...
```

### Excel 서식 (report_generator.py)

- 모든 서식 상수(`HEADER_FILL_DARK`, `FONT_HEADER_WHITE` 등)는 파일 최상단에 선언
- 셀 스타일 적용은 반드시 `_apply_cell_style()` 헬퍼를 통해 수행
- 새 시트 추가 시 함수명은 `_write_*_sheet(wb, ...)` 패턴 유지

### Streamlit (app.py)

- 무거운 연산(데이터 로드, 정제)은 반드시 `@st.cache_data`로 캐싱
- 사이드바 설정값은 `st.session_state`를 통해 메인 화면으로 전달
- 차트는 `plotly`만 사용 (`matplotlib` 추가 금지)
- 섹션 구분 제목은 `_section_title()` 대신 아래 패턴 통일:

```python
st.markdown('<div class="section-title">■ 제목</div>', unsafe_allow_html=True)
```

---

## 주요 데이터 특성 (현재 환경 기준)

### Jira 상태값 목록
`미해결`, `완료`, `진행 중`, `개발 중`, `배포`, `반려`, `영향도 분석`, `I&C 확인`, `GDC이관`, `중단`

### 처리상태 매핑 결과
| Jira 상태 | 처리상태 |
|-----------|---------|
| 미해결 | 미접수 |
| 완료 | 완료 |
| 그 외 전부 | 접수 |

### 업무구분(FTE) 고유값
`프로그램개선/개발`, `운영 업무`, `일반 업무`, `데이터 작업`, `프로젝트 지원/관리`

> `업무유형(FTE)`이 없는 행(미해결·영향도 분석 상태)은 `문의유형 = "미분류"`로 처리됩니다.
> 이는 정상 케이스이므로 에러 처리하지 않습니다.

### 날짜 컬럼 형식 혼재 주의
- `생성일`, `변경일`: 문자열 `"2026/02/25 8:08 오전"` 형식
- `접수일`, `해결일`, `합의완료일`: `pandas.Timestamp` 또는 `datetime` 객체

---

## 자주 발생하는 실수

### 1. 당월 필터에서 날짜 형식 오류
`생성일`은 `"2026/02/25 8:08 오전"` 형식이므로 단순 문자열 비교(`str(x)[:7]`)로 필터하면 동작하지 않습니다.
반드시 `_parse_datetime()` → `.strftime("%Y-%m")` 경로를 사용하세요.

```python
# 현재 올바른 구현 (data_processor.py)
def _month_of(x) -> str | None:
    ts = _parse_datetime(x)
    return ts.strftime("%Y-%m") if ts else None

df_month = df[df["생성일"].apply(lambda x: _month_of(x) == report_month)]
```

### 2. Excel 로드 시 중복 컬럼명
원본 Excel에는 `상태`, `해결책`, `시스템명` 컬럼이 각각 2개씩 존재합니다.
`jira_client.load_from_excel()`에서 `상태_1` → `상태`로 정규화한 후 `_1` 접미사 컬럼을 제거합니다.
이 처리를 건너뛰면 `처리상태 매핑`이 전부 `접수`로 잘못 처리됩니다.

### 3. openpyxl 수식 셀 읽기
`data_only=True` 옵션을 사용해야 수식이 아닌 캐시된 값을 읽습니다.
없으면 `처리상태`, `문의유형` 컬럼이 수식 문자열(`=IFERROR(...)`)로 읽힙니다.

```python
# jira_client.py — 반드시 data_only=True
wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
```

---

## 테스트 방법

단위 테스트 프레임워크는 없으므로, 변경 후 아래 명령으로 동작을 검증합니다.

```bash
# 전체 파이프라인 테스트 (예시 파일 필요)
venv/bin/python main.py \
  --excel "/Users/youwonji/Downloads/RAW데이터 예시.xlsx" \
  --month 2026-02 \
  -v

# 기대 출력 확인 항목
# - 처리상태: {'완료': 327, '접수': 48, '미접수': 10}
# - 접수율: 97.4%, 처리율: 84.9%
# - 평균처리시간(당월): 접수 1.3일, 해결 1.6일
# - output/ 디렉토리에 .xlsx 생성 확인
```

---

## 확장 시 가이드

### 새 문의유형 추가
1. `config.py` → `FTE_TYPE_TO_INQUIRY_TYPE`에 `"업무유형명": "N. 신규유형"` 추가
2. `config.py` → `INQUIRY_TYPE_ORDER`에 표시 순서에 맞게 추가
3. `config.py` → `INQUIRY_SHORT_NAMES`에 단축명 추가 (`report_generator.py` 상단)

### 새 Excel 시트 추가
1. `report_generator.py`에 `_write_새시트명_sheet(wb, df, stats, ...)` 함수 추가
2. `generate_report()` 내 `_write_*` 호출 목록에 추가
3. 함수 내 컬럼 너비·헤더 서식은 기존 패턴(`_apply_cell_style`) 동일하게 적용

### 새 Jira 프로젝트 지원
- `config.py`의 `JIRA_ISSUE_TYPES`는 이슈 유형 필터이므로 프로젝트별로 다를 수 있습니다
- CLI에서 `--project` 인자로 프로젝트 코드만 바꾸면 됩니다
- 커스텀 필드 ID가 다른 경우 `CUSTOM_FIELD_MAP` 수정이 필요합니다
