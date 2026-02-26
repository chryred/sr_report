"""
SR 리포팅 자동화 도구

사용법:
    # Jira에서 데이터 수집 후 리포트 생성
    python main.py --project AMDP1 --from-date 2025-01-01 --month 2026-02

    # 기존 Excel 파일로 리포트 생성 (Jira 연동 없이)
    python main.py --excel /path/to/raw_data.xlsx --month 2026-02

    # Jira 커스텀 필드 ID 확인
    python main.py --list-fields
"""

import argparse
import logging
import sys
from datetime import datetime

from config import OUTPUT_DIR


def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="SR 리포팅 자동화 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # Jira 연동
  python main.py --project AMDP1 --from-date 2025-01-01 --month 2026-02

  # Excel 파일 사용
  python main.py --excel ./RAW데이터.xlsx --month 2026-02

  # 커스텀 필드 ID 확인
  python main.py --list-fields
        """,
    )

    # 데이터 소스 (Jira 또는 Excel)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--project",
        help="Jira 프로젝트 코드 (예: AMDP1)",
    )
    source.add_argument(
        "--excel",
        help="기존 Excel RAW 데이터 파일 경로",
    )
    source.add_argument(
        "--list-fields",
        action="store_true",
        help="Jira 커스텀 필드 ID 목록 조회",
    )

    parser.add_argument(
        "--from-date",
        default="2025-01-01",
        help="Jira 데이터 시작일 (기본값: 2025-01-01)",
    )
    parser.add_argument(
        "--month",
        default=None,
        help="리포트 대상 월 (예: 2026-02). 미지정 시 현재 월",
    )
    parser.add_argument(
        "--team-name",
        default="백화점CX팀",
        help="팀 이름 (기본값: 백화점CX팀)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 파일 경로 (미지정 시 output/ 디렉토리에 자동 생성)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # 리포트 월 기본값
    report_month = args.month or datetime.now().strftime("%Y-%m")

    # ── Jira 커스텀 필드 조회 모드 ──
    if args.list_fields:
        from jira_client import JiraClient

        logger.info("Jira 커스텀 필드 목록 조회 중...")
        client = JiraClient()
        fields = client.fetch_custom_field_ids()
        print(f"\n{'='*60}")
        print(f"{'필드 ID':<30} {'필드명'}")
        print(f"{'='*60}")
        for fid, fname in sorted(fields.items()):
            print(f"{fid:<30} {fname}")
        print(f"{'='*60}")
        print(f"총 {len(fields)}개 커스텀 필드")
        return

    # ── 데이터 수집 ──
    if args.project:
        from jira_client import JiraClient

        logger.info(f"Jira에서 데이터 수집 중... (프로젝트: {args.project}, 시작일: {args.from_date})")
        client = JiraClient()
        df = client.fetch_issues(args.project, args.from_date)
    else:
        from jira_client import load_from_excel

        logger.info(f"Excel 파일에서 데이터 로드 중... ({args.excel})")
        df = load_from_excel(args.excel)

    if len(df) == 0:
        logger.error("수집된 데이터가 없습니다.")
        sys.exit(1)

    logger.info(f"총 {len(df)}건 데이터 수집 완료")

    # ── 데이터 정제 ──
    from data_processor import process, generate_summary_stats

    logger.info("데이터 정제 중...")
    df = process(df)

    # ── 통계 생성 ──
    logger.info("통계 데이터 생성 중...")
    stats = generate_summary_stats(df, report_month)

    # 요약 출력
    total = stats["total"]
    rates = stats["rates"]
    print(f"\n{'='*50}")
    print(f"  SR 건수 집계 ({report_month})")
    print(f"{'='*50}")
    print(f"  전체: 미접수 {total['미접수']} / 접수 {total['접수']} / 완료 {total['완료']} / 합계 {total['합계']}")
    print(f"  접수율: {rates['접수율']}% / 처리율: {rates['처리율']}%")
    print(f"  장기 미처리: {len(stats.get('long_pending', []))}건")

    avg = stats.get("avg_times_monthly", {})
    print(f"  평균처리시간(당월): 접수 {avg.get('생성일_접수일', '-')}일 / 해결 {avg.get('생성일_완료일', '-')}일")
    print(f"{'='*50}\n")

    # ── 리포트 생성 ──
    from report_generator import generate_report

    logger.info("Excel 리포트 생성 중...")
    output_path = generate_report(
        df=df,
        stats=stats,
        project_name=args.team_name,
        report_month=report_month,
        output_path=args.output,
    )

    print(f"리포트 생성 완료: {output_path}")


if __name__ == "__main__":
    main()
