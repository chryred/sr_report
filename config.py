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

# 업무유형(FTE) → 문의유형 매핑 (운영업무분류 시트 기반)
FTE_TYPE_TO_INQUIRY_TYPE = {
    "DB 작업 및 관리": "3. 데이터 추출 및 수정",
    "개발환경 셋팅": "5. 운영관리(시스템/품질/보안)",
    "개선/개발 사전 검토": "4. 신규개발 및 개선",
    "계정 및 권한 처리": "3. 데이터 추출 및 수정",
    "교육": "2. 단순조치/운영지원",
    "기능변경": "4. 신규개발 및 개선",
    "기타": "2. 단순조치/운영지원",
    "단순 처리": "2. 단순조치/운영지원",
    "데이터 변경": "3. 데이터 추출 및 수정",
    "데이터 이관/적재": "3. 데이터 추출 및 수정",
    "데이터 점검": "3. 데이터 추출 및 수정",
    "데이터 추출": "3. 데이터 추출 및 수정",
    "라이선스 관리": "2. 단순조치/운영지원",
    "문서 작성": "2. 단순조치/운영지원",
    "문의 대응": "2. 단순조치/운영지원",
    "서버 작업 및 관리": "5. 운영관리(시스템/품질/보안)",
    "시스템 분석": "5. 운영관리(시스템/품질/보안)",
    "시스템 점검/모니터링": "5. 운영관리(시스템/품질/보안)",
    "신규개발": "4. 신규개발 및 개선",
    "업무 보고/회의": "5. 운영관리(시스템/품질/보안)",
    "영향도 검토": "5. 운영관리(시스템/품질/보안)",
    "오류 처리": "2. 단순조치/운영지원",
    "오류수정": "2. 단순조치/운영지원",
    "외주 유지보수 관리": "5. 운영관리(시스템/품질/보안)",
    "월마감": "2. 단순조치/운영지원",
    "일부개발": "4. 신규개발 및 개선",
    "장애예방활동": "5. 운영관리(시스템/품질/보안)",
    "점포 운영": "5. 운영관리(시스템/품질/보안)",
    "점포 장비 관리": "5. 운영관리(시스템/품질/보안)",
    "정보보안 대응": "5. 운영관리(시스템/품질/보안)",
    "품질 강화": "5. 운영관리(시스템/품질/보안)",
    "프로젝트 관리": "5. 운영관리(시스템/품질/보안)",
    "프로젝트 지원/대응": "5. 운영관리(시스템/품질/보안)",
}

# 업무유형(FTE)이 비어있을 때 기본 문의유형
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
