# SR 리포팅 자동화 도구

Jira에서 SR(서비스 요청) 데이터를 수집하고, 자동으로 정제·분석하여 Excel 리포트와 웹 대시보드를 생성하는 도구입니다.

---

## 주요 기능

- **Jira 자동 연동**: JQL 기반으로 지정 프로젝트의 SR 데이터를 자동 수집
- **Excel 파일 입력**: 기존 RAW 데이터 Excel 파일도 바로 사용 가능
- **데이터 자동 정제**: 상태 매핑, 문의유형 분류, 처리시간 계산 등 자동 처리
- **Excel 리포트 생성**: 서식이 적용된 3개 시트 리포트 자동 생성
- **웹 대시보드**: Streamlit 기반 인터랙티브 대시보드 제공

---

## 사전 요구사항

- Python 3.11 이상
- 가상환경 (`venv/`)

```bash
# 의존성 설치
venv/bin/pip install -r requirements.txt
```

---

## 빠른 시작

### 방법 1 — 웹 대시보드 (권장)

```bash
venv/bin/streamlit run app.py --server.port 8501
```

브라우저에서 `http://localhost:8501` 접속 후:

1. 팀 이름 및 리포트 대상 월 설정
2. **Excel 파일 업로드** 또는 **Jira 직접 연동** 선택
3. **리포트 생성** 버튼 클릭
4. 우상단 **Excel 리포트 다운로드** 버튼으로 결과물 저장

### 방법 2 — CLI (명령줄)

```bash
# Excel 파일로 리포트 생성
venv/bin/python main.py --excel ./RAW데이터.xlsx --month 2026-02

# Jira에서 직접 데이터 수집 후 리포트 생성
venv/bin/python main.py --project AMDP1 --from-date 2025-01-01 --month 2026-02

# 상세 로그 출력
venv/bin/python main.py --excel ./RAW데이터.xlsx --month 2026-02 -v
```

---

## Jira 연동 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 접속 정보를 입력합니다.

```bash
cp .env.example .env
```

```dotenv
JIRA_BASE_URL=https://jira.sinc.co.kr
JIRA_USERNAME=your_id
JIRA_PASSWORD=your_password
```

> **커스텀 필드 ID 확인**: Jira 환경마다 커스텀 필드 ID가 다릅니다.
> 아래 명령으로 실제 ID를 확인한 후 `config.py`의 `CUSTOM_FIELD_MAP`을 수정하세요.
>
> ```bash
> venv/bin/python main.py --list-fields
> ```

---

## CLI 옵션 전체 목록

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--project` | Jira 프로젝트 코드 (Jira 연동 시) | — |
| `--excel` | RAW 데이터 Excel 파일 경로 | — |
| `--list-fields` | Jira 커스텀 필드 ID 목록 조회 | — |
| `--from-date` | 데이터 수집 시작일 (Jira 연동 시) | `2025-01-01` |
| `--month` | 리포트 대상 월 (YYYY-MM) | 현재 월 |
| `--team-name` | 리포트에 표시할 팀 이름 | `백화점CX팀` |
| `--output` | 출력 파일 경로 | `output/SR_Report_*.xlsx` |
| `-v` / `--verbose` | 상세 로그 출력 | — |

---

## 데이터 정제 규칙

RAW 데이터는 다음 규칙에 따라 자동 정제됩니다.

| 규칙 | 내용 |
|------|------|
| 상태 제외 | `변경이관` 상태 행 제거 |
| 처리상태 변환 | `미해결` → 미접수 / `완료` → 완료 / 그 외 → 접수 |
| 서비스 제외 | `사이먼`으로 시작하는 서비스 행 제거 |
| 문의유형 분류 | 업무유형(FTE) 기준 32개 항목을 5개 유형으로 매핑 |
| 처리시간(접수) | `접수일 − 생성일` (일 단위, 최소 1일) |
| 처리시간(해결) | `해결일 − 생성일` (일 단위, 최소 1일) |

### 문의유형 분류 체계

| 문의유형 | 포함 업무유형(FTE) 예시 |
|----------|------------------------|
| 1. 기능문의 | — (현재 매핑 없음, 추후 추가 가능) |
| 2. 단순조치/운영지원 | 문의 대응, 오류수정, 월마감, 단순 처리, 교육 등 |
| 3. 데이터 추출 및 수정 | 데이터 추출/변경/이관/적재, DB 작업, 계정 처리 등 |
| 4. 신규개발 및 개선 | 신규개발, 기능변경, 일부개발, 개선/개발 사전 검토 |
| 5. 운영관리(시스템/품질/보안) | 시스템 분석/점검, 서버 관리, 보안 대응, 라이선스 관리 등 |

---

## 출력 결과물

### Excel 리포트 (`output/SR_Report_YYYY-MM_*.xlsx`)

| 시트명 | 내용 |
|--------|------|
| 정제 데이터 | 필터/정렬 가능한 전체 정제 데이터 (22개 컬럼) |
| SR 처리 현황(상세) | 시스템명 × 문의유형 × 처리상태 매트릭스 |
| SR 집계(요약) | 전체/당월 건수 · 접수율/처리율 · 장기미처리 · 평균처리시간 |

### 웹 대시보드 탭 구성

| 탭 | 내용 |
|----|------|
| 요약 대시보드 | KPI 카드 · 처리상태/문의유형 차트 · 접수율/처리율 테이블 |
| SR 처리 현황(상세) | 시스템별 피벗 테이블 · 처리상태 stacked bar |
| 장기 미처리 | 90일 이상 미처리 SR 목록 |
| 원본 데이터 | 필터링 가능한 전체 데이터 테이블 |

---

## 프로젝트 구조

```
sr_repoting/
├── app.py                  # Streamlit 웹 대시보드
├── main.py                 # CLI 진입점
├── config.py               # 전체 설정 및 매핑 테이블
├── jira_client.py          # Jira REST API 연동 / Excel 로드
├── data_processor.py       # 데이터 정제 및 통계 계산
├── report_generator.py     # Excel 리포트 생성 (서식 포함)
├── requirements.txt        # Python 의존성
├── .env.example            # 환경변수 예시
├── .gitignore
├── .claude/
│   └── launch.json         # 개발 서버 실행 설정
└── output/                 # 생성된 리포트 저장 경로
```

---

## 자주 묻는 질문

**Q. 문의유형이 "미분류"로 나오는 데이터가 있어요.**
A. 업무유형(FTE) 값이 비어있거나 매핑 테이블에 없는 경우입니다. 해당 SR은 아직 담당자가 업무유형을 입력하지 않은 상태(예: 영향도 분석 중, 미해결)입니다. `config.py`의 `FTE_TYPE_TO_INQUIRY_TYPE`에 항목을 추가하면 분류됩니다.

**Q. 새로운 서비스나 시스템을 제외하려면 어떻게 하나요?**
A. `config.py`의 `EXCLUDED_SERVICE_PREFIXES` 리스트에 접두사를 추가하세요.

**Q. 장기 미처리 기준 90일을 변경하려면?**
A. `config.py`의 `LONG_PENDING_THRESHOLD_DAYS` 값을 수정하세요.
