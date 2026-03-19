"""데이터 정제 및 변환 모듈"""

import logging
import math
from datetime import datetime

import pandas as pd

from config import (
    STATUS_MAP,
    DEFAULT_STATUS,
    ACCEPTED_ISSUE_TYPES_FOR_UNRESOLVED,
    EXCLUDED_STATUSES,
    EXCLUDED_SERVICE_PREFIXES,
    FTE_NEXTGEN_MAPPING_PROJECTS,
    FTE_TYPE_TO_INQUIRY_TYPE,
    FTE_DIVISION_INQUIRY_MAP,
    FTE_GENERAL_TASK_INQUIRY_MAP,
    FTE_GENERAL_TASK_DEFAULT,
    ISSUE_TYPE_NO_DIVISION_INQUIRY_MAP,
    DEFAULT_INQUIRY_TYPE,
    INQUIRY_TYPE_ORDER,
    LONG_PENDING_THRESHOLD_DAYS,
)

logger = logging.getLogger(__name__)


def _parse_datetime(value) -> pd.Timestamp | None:
    """다양한 날짜 형식을 파싱"""
    if pd.isna(value) or value is None:
        return None

    if isinstance(value, datetime):
        return pd.Timestamp(value)

    s = str(value).strip()
    if not s:
        return None

    # "2026/02/25 8:08 오전" 형식
    for fmt in [
        "%Y/%m/%d %I:%M %p",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]:
        try:
            # 오전/오후 → AM/PM 변환
            converted = s.replace("오전", "AM").replace("오후", "PM")
            return pd.Timestamp(datetime.strptime(converted, fmt))
        except ValueError:
            continue

    # pandas 자동 파싱 시도
    try:
        return pd.Timestamp(s)
    except Exception:
        logger.warning(f"날짜 파싱 실패: {value}")
        return None


def _calc_days(start, end) -> int | None:
    """두 날짜 간 일수 계산 (최소 1일)"""
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)

    if start_dt is None or end_dt is None:
        return None

    diff = (end_dt - start_dt).total_seconds() / 86400
    return max(1, math.ceil(diff))


def process(df: pd.DataFrame) -> pd.DataFrame:
    """
    RAW 데이터를 정제하여 분석 가능한 형태로 변환

    정제 규칙:
    1. "변경이관" 상태 제외
    2. 처리상태 컬럼 생성 (미해결→미접수, 완료→완료, 그외→접수)
    3. "사이먼" 서비스 제외
    4. 문의유형 매핑 (업무유형(FTE) 기반)
    5. 평균처리시간 계산

    Args:
        df: RAW DataFrame

    Returns:
        pd.DataFrame: 정제된 DataFrame
    """
    original_count = len(df)
    logger.info(f"데이터 정제 시작: {original_count}건")

    # ── 1. "변경이관" 상태 제외 ──
    for status in EXCLUDED_STATUSES:
        mask = df["상태"].astype(str).str.strip() == status
        excluded = mask.sum()
        if excluded > 0:
            df = df[~mask].copy()
            logger.info(f"  '{status}' 상태 {excluded}건 제외")

    # ── 2. 처리상태 컬럼 생성 ──
    def map_status(row) -> str:
        status = row.get("상태")
        issue_type = str(row.get("이슈 유형") or "").strip()

        if pd.isna(status) or status is None:
            base = "미접수"
        elif status == "반려":
            base = "완료"
        else:
            base = STATUS_MAP.get(str(status).strip(), DEFAULT_STATUS)

        # 미해결(→미접수)이라도 지정된 이슈 유형이면 "접수"로 재분류
        if base == "미접수" and issue_type in ACCEPTED_ISSUE_TYPES_FOR_UNRESOLVED:
            return DEFAULT_STATUS

        return base

    df["처리상태"] = df.apply(map_status, axis=1)
    logger.info(f"  처리상태 매핑 완료: {df['처리상태'].value_counts().to_dict()}")

    # ── 3. "사이먼" 서비스 제외 ──
    if "서비스" in df.columns:
        for prefix in EXCLUDED_SERVICE_PREFIXES:
            mask = df["서비스"].astype(str).str.startswith(prefix)
            excluded = mask.sum()
            if excluded > 0:
                df = df[~mask].copy()
                logger.info(f"  '{prefix}' 서비스 {excluded}건 제외")

    if "시스템명" in df.columns:
        for prefix in EXCLUDED_SERVICE_PREFIXES:
            mask = df["시스템명"].astype(str).str.startswith(prefix)
            excluded = mask.sum()
            if excluded > 0:
                df = df[~mask].copy()
                logger.info(f"  '{prefix}' 시스템명 {excluded}건 제외")

    # ── 4. 문의유형 매핑 ──
    # 우선순위:
    #   1) 업무구분 == "일반 업무" → 프로젝트 무관하게 신 방식 적용
    #      (일반업무+문의대응 → 1.기능문의 / 그외 → 2.단순조치/운영지원)
    #   2) 차세대 프로젝트(DX·SAP) + 일반업무 외 → 업무유형 단독 매핑(차세대 방식)
    #   3) 그 외 프로젝트 + 일반업무 외 → 업무구분 기반 매핑(신 방식)
    def map_inquiry_type(row) -> str:
        project  = str(row.get("프로젝트") or "").strip()
        division = str(row.get("업무구분(FTE)") or "").strip()
        fte_type = str(row.get("업무유형(FTE)") or "").strip()

        # ── 1) "일반 업무": 프로젝트 무관하게 신 방식 ──
        if division == "일반 업무":
            return FTE_GENERAL_TASK_INQUIRY_MAP.get(fte_type, FTE_GENERAL_TASK_DEFAULT)

        # ── 2) 차세대 프로젝트: 업무유형 단독 매핑 ──
        if project in FTE_NEXTGEN_MAPPING_PROJECTS:
            if not fte_type:
                issue_type = str(row.get("이슈 유형") or "").strip()
                if issue_type in ISSUE_TYPE_NO_DIVISION_INQUIRY_MAP:
                    return ISSUE_TYPE_NO_DIVISION_INQUIRY_MAP[issue_type]
                return DEFAULT_INQUIRY_TYPE
            return FTE_TYPE_TO_INQUIRY_TYPE.get(fte_type, DEFAULT_INQUIRY_TYPE)

        # ── 3) 신 방식: 업무구분 기반 매핑 ──
        if not division:
            # 업무구분이 없고 이슈 유형이 매핑 테이블에 있으면 이슈 유형 기반 매핑
            # 예: 이슈 유형 "변경관리" → "4. 신규개발 및 개선"
            issue_type = str(row.get("이슈 유형") or "").strip()
            if issue_type in ISSUE_TYPE_NO_DIVISION_INQUIRY_MAP:
                return ISSUE_TYPE_NO_DIVISION_INQUIRY_MAP[issue_type]
            return DEFAULT_INQUIRY_TYPE
        return FTE_DIVISION_INQUIRY_MAP.get(division, DEFAULT_INQUIRY_TYPE)

    df["문의유형"] = df.apply(map_inquiry_type, axis=1)
    logger.info(f"  문의유형 매핑 완료: {df['문의유형'].value_counts().to_dict()}")

    # ── 5. 평균처리시간 계산 ──
    df["처리시간_접수(일)"] = df.apply(
        lambda row: _calc_days(row.get("생성일"), row.get("접수일")), axis=1
    )
    df["처리시간_해결(일)"] = df.apply(
        lambda row: _calc_days(row.get("생성일"), row.get("해결일")), axis=1
    )

    logger.info(
        f"데이터 정제 완료: {original_count}건 → {len(df)}건 "
        f"({original_count - len(df)}건 제외)"
    )
    return df


def generate_summary_stats(df: pd.DataFrame, report_month: str = None) -> dict:
    """
    리포트에 필요한 통계 데이터 생성

    Args:
        df: 정제된 DataFrame
        report_month: 당월 기준 (예: "2025-02"). None이면 현재 월.

    Returns:
        dict: 각종 통계 데이터
    """
    if report_month is None:
        report_month = datetime.now().strftime("%Y-%m")

    stats = {}

    # ── SR 건수 집계(요약) ──
    total_counts = df["처리상태"].value_counts()
    stats["total"] = {
        "미접수": int(total_counts.get("미접수", 0)),
        "접수": int(total_counts.get("접수", 0)),
        "완료": int(total_counts.get("완료", 0)),
        "합계": len(df),
    }

    # 당월 필터 (생성일 형식: "2026/02/25 8:08 오전" 또는 Timestamp 모두 처리)
    def _month_of(x) -> str | None:
        if pd.isna(x) or x is None:
            return None
        ts = _parse_datetime(x)
        return ts.strftime("%Y-%m") if ts else None

    df_month = df[df["생성일"].apply(lambda x: _month_of(x) == report_month)]
    month_counts = df_month["처리상태"].value_counts()
    stats["monthly"] = {
        "미접수": int(month_counts.get("미접수", 0)),
        "접수": int(month_counts.get("접수", 0)),
        "완료": int(month_counts.get("완료", 0)),
        "합계": len(df_month),
    }

    # ── 접수율 및 처리율 ──
    total = stats["total"]["합계"]
    accepted = stats["total"]["접수"] + stats["total"]["완료"]
    completed = stats["total"]["완료"]
    stats["rates"] = {
        "접수율": round(accepted / total * 100, 1) if total > 0 else 0,
        "처리율": round(completed / total * 100, 1) if total > 0 else 0,
    }

    # 문의유형별 접수율/처리율
    inquiry_rates = {}
    for itype in INQUIRY_TYPE_ORDER:
        df_type = df[df["문의유형"] == itype]
        t = len(df_type)
        if t > 0:
            type_counts = df_type["처리상태"].value_counts()
            a = int(type_counts.get("접수", 0)) + int(type_counts.get("완료", 0))
            c = int(type_counts.get("완료", 0))
            inquiry_rates[itype] = {
                "건수": t,
                "접수율": round(a / t * 100, 1),
                "처리율": round(c / t * 100, 1),
            }
        else:
            inquiry_rates[itype] = {"건수": 0, "접수율": 0, "처리율": 0}
    stats["inquiry_rates"] = inquiry_rates

    # ── 장기 미처리 SR ──
    today = datetime.now()
    threshold_date = today - pd.Timedelta(days=LONG_PENDING_THRESHOLD_DAYS)

    def is_long_pending(row):
        if row["처리상태"] == "완료":
            return False
        created = _parse_datetime(row.get("생성일"))
        if created is None:
            return False
        return created < threshold_date

    long_pending = df[df.apply(is_long_pending, axis=1)].copy()
    stats["long_pending"] = long_pending

    # ── 평균처리 시간 ──
    accept_times = df["처리시간_접수(일)"].dropna()
    resolve_times = df["처리시간_해결(일)"].dropna()
    stats["avg_times"] = {
        "생성일_접수일": round(accept_times.mean(), 1) if len(accept_times) > 0 else None,
        "생성일_완료일": round(resolve_times.mean(), 1) if len(resolve_times) > 0 else None,
    }

    # 당월 평균처리 시간
    month_accept = df_month["처리시간_접수(일)"].dropna()
    month_resolve = df_month["처리시간_해결(일)"].dropna()
    stats["avg_times_monthly"] = {
        "생성일_접수일": round(month_accept.mean(), 1) if len(month_accept) > 0 else None,
        "생성일_완료일": round(month_resolve.mean(), 1) if len(month_resolve) > 0 else None,
    }

    # ── SR 처리 현황(상세) - 시스템명 × 문의유형 × 처리상태 ──
    detail_pivot = pd.pivot_table(
        df,
        index="시스템명",
        columns=["문의유형", "처리상태"],
        aggfunc="size",
        fill_value=0,
    )
    stats["detail_pivot"] = detail_pivot

    # ── DML 처리 현황 (3. 데이터 추출 및 수정) ──
    stats["data_request_report"] = generate_data_request_report(df, report_month)

    return stats


def generate_data_request_report(df: pd.DataFrame, report_month: str) -> list:
    """
    '3. 데이터 추출 및 수정' 문의유형의 당월 데이터를 시스템별로 집계하여 주요 사유 목록 생성

    Args:
        df: 정제된 DataFrame
        report_month: 리포트 대상 월 (예: "2026-02")

    Returns:
        list[dict]: 시스템별 처리현황 및 주요 사유 목록
          keys: 시스템명, 미접수, 접수, 완료, 합계, 주요_사유_목록, 주요_사유
    """
    def _month_of(x) -> str | None:
        if pd.isna(x) or x is None:
            return None
        ts = _parse_datetime(x)
        return ts.strftime("%Y-%m") if ts else None

    df_month = df[df["생성일"].apply(lambda x: _month_of(x) == report_month)].copy()
    df_data = df_month[df_month["문의유형"] == "3. 데이터 추출 및 수정"].copy()

    result = []
    for sys_name in sorted(df_data["시스템명"].dropna().unique()):
        df_sys = df_data[df_data["시스템명"] == sys_name]
        sc = df_sys["처리상태"].value_counts()

        summaries = []
        for _, r in df_sys.iterrows():
            key = str(r.get("키", "") or "").strip()
            summary = str(r.get("요약", "") or "").strip()
            if summary:
                summaries.append(f"• {key} {summary}" if key else f"• {summary}")

        result.append({
            "시스템명": sys_name,
            "미접수": int(sc.get("미접수", 0)),
            "접수": int(sc.get("접수", 0)),
            "완료": int(sc.get("완료", 0)),
            "합계": len(df_sys),
            "주요_사유_목록": summaries,
            "주요_사유": "\n".join(summaries),
        })

    logger.info(
        f"DML 처리 현황 집계: {len(result)}개 시스템, "
        f"{sum(r['합계'] for r in result)}건"
    )
    return result
