"""SR 리포팅 자동화 설정"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Jira 접속 설정 ──────────────────────────────────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://jira.sinc.co.kr")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD", "")

# ── Jira 검색 설정 ──────────────────────────────────────────
JIRA_ISSUE_TYPES = ["변경관리", "서비스요청관리"]
JIRA_MAX_RESULTS = 100  # 한 번에 가져올 최대 건수 (페이지네이션)

# Jira에서 가져올 필드 목록
JIRA_FIELDS = [
    "project",
    "summary",
    "issuetype",
    "key",
    "assignee",
    "status",
    "resolution",
    "reporter",
    "created",
    "updated",
    "resolutiondate",
    "description",
    # 커스텀 필드는 Jira 환경에 따라 ID가 다를 수 있음
    # 아래는 예시이며, 실제 환경에서 확인 필요
    "customfield_10100",  # 요청구분
    "customfield_10101",  # 완료희망일
    "customfield_10102",  # JSM요청자
    "customfield_10103",  # 합의완료일
    "customfield_10104",  # 관계사
    "customfield_10105",  # 시스템 부서(구)
    "customfield_10106",  # 시스템명(구)
    "customfield_10107",  # 시작일(cal)
    "customfield_10108",  # 종료예정일(cal)
    "customfield_10109",  # 요청생성일
    "customfield_10110",  # 처리유형(변경관리)
    "customfield_10111",  # 처리유형(서비스요청)
    "customfield_10112",  # 접수일
    "customfield_10113",  # 시스템명
    "customfield_10114",  # 시스템 부서
    "customfield_10115",  # 서비스
    "customfield_10116",  # 서비스등급
    "customfield_10117",  # 이슈유형
    "customfield_10118",  # 업무유형(FTE)
    "customfield_10119",  # 업무구분(FTE)
]

# ── 커스텀 필드 → 한글 컬럼명 매핑 ────────────────────────
# 실제 Jira 환경에서 /rest/api/2/field 호출하여 확인 후 수정 필요
CUSTOM_FIELD_MAP = {
    "customfield_10100": "요청구분",
    "customfield_10101": "완료희망일",
    "customfield_10102": "JSM요청자",
    "customfield_10103": "합의완료일",
    "customfield_10104": "관계사",
    "customfield_10105": "시스템 부서(구)",
    "customfield_10106": "시스템명(구)",
    "customfield_10107": "시작일(cal)",
    "customfield_10108": "종료예정일(cal)",
    "customfield_10109": "요청생성일",
    "customfield_10110": "처리유형(변경관리)",
    "customfield_10111": "처리유형(서비스요청)",
    "customfield_10112": "접수일",
    "customfield_10113": "시스템명",
    "customfield_10114": "시스템 부서",
    "customfield_10115": "서비스",
    "customfield_10116": "서비스등급",
    "customfield_10117": "이슈유형",
    "customfield_10118": "업무유형(FTE)",
    "customfield_10119": "업무구분(FTE)",
}

# ── 데이터 정제 규칙 ────────────────────────────────────────

# 상태 → 처리상태 매핑
STATUS_MAP = {
    "미해결": "미접수",
    "완료": "완료",
    # 그 외 모든 상태는 "접수"로 처리
}
DEFAULT_STATUS = "접수"

# 상태가 "미해결"(→미접수)이더라도 이 이슈 유형이면 "접수"로 재분류
# 예: 변경관리 이슈는 미해결 상태여도 이미 접수된 것으로 간주
ACCEPTED_ISSUE_TYPES_FOR_UNRESOLVED = ["변경관리"]

# 제외할 상태값
EXCLUDED_STATUSES = ["변경이관", "반려", "프로젝트이관"]

# 제외할 서비스 접두사
EXCLUDED_SERVICE_PREFIXES = ["사이먼", "[사]"]

# 업무구분(FTE) → 문의유형 기본 매핑
# ※ "일반 업무"는 업무유형(FTE)에 따라 세분화하므로 이 딕셔너리에서 제외
FTE_DIVISION_INQUIRY_MAP = {
    "데이터 작업":               "3. 데이터 추출 및 수정",
    "프로그램개선/개발":         "4. 신규개발 및 개선",
    "운영 업무":                 "5. 운영관리(시스템/품질/보안)",
    "품질관리":                  "5. 운영관리(시스템/품질/보안)",
    "프로젝트 지원/관리":        "5. 운영관리(시스템/품질/보안)",
    "IT 운영 사업 기획 및 관리": "5. 운영관리(시스템/품질/보안)",
    "정기 업무 지원":            "2. 단순조치/운영지원",
}

# "일반 업무" 내 업무유형(FTE) → 문의유형 세분화 매핑
# 이 딕셔너리에 없는 업무유형은 FTE_GENERAL_TASK_DEFAULT 로 처리
FTE_GENERAL_TASK_INQUIRY_MAP = {
    "문의 대응": "1. 기능문의",
    # 계정 및 권한 처리, 단순 처리, 오류 처리 → FTE_GENERAL_TASK_DEFAULT (2. 단순조치/운영지원)
}
FTE_GENERAL_TASK_DEFAULT = "2. 단순조치/운영지원"

# 업무구분(FTE)·업무유형(FTE) 모두 비어있을 때 기본 문의유형
DEFAULT_INQUIRY_TYPE = "미분류"

# ── 리포트 설정 ─────────────────────────────────────────────

# 문의유형 표시 순서 (리포트 컬럼 순서)
INQUIRY_TYPE_ORDER = [
    "1. 기능문의",
    "2. 단순조치/운영지원",
    "3. 데이터 추출 및 수정",
    "4. 신규개발 및 개선",
    "5. 운영관리(시스템/품질/보안)",
]

# 처리상태 표시 순서
PROCESS_STATUS_ORDER = ["미접수", "접수", "완료"]

# 장기 미처리 기준 (일)
LONG_PENDING_THRESHOLD_DAYS = 90

# 출력 디렉토리
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# ── 프로젝트(팀) 설정 ─────────────────────────────────────────

# 프로젝트명 → 표시용 팀 이름 매핑
PROJECT_TEAM_NAME_MAP = {
    "백화점CX팀 업무 관리": "백화점CX팀",
    "백화점DX팀 업무 관리": "백화점DX팀",
    "신세계POS팀 업무 관리": "신세계POS팀",
    "신세계SAP팀 업무 관리": "신세계SAP팀",
}

# 프로젝트명 → Excel 시트 접두사 (31자 제한 고려한 단축 코드)
PROJECT_SHEET_PREFIX_MAP = {
    "백화점CX팀 업무 관리": "CX",
    "백화점DX팀 업무 관리": "DX",
    "신세계POS팀 업무 관리": "POS",
    "신세계SAP팀 업무 관리": "SAP",
}
