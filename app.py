"""SR 리포팅 자동화 - Streamlit 대시보드"""

import io
import os
import sys
import tempfile
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    INQUIRY_TYPE_ORDER,
    PROCESS_STATUS_ORDER,
    PROJECT_TEAM_NAME_MAP,
    PROJECT_SHEET_PREFIX_MAP,
)
from data_processor import generate_summary_stats, process
from jira_client import JiraClient, load_from_excel
from report_generator import generate_report

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="SR 리포팅 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 스타일 ───────────────────────────────────────────────
st.markdown(
    """
    <style>
    .metric-card {
        background: #f0f4f8;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        border-left: 4px solid #1F3864;
    }
    .metric-card h3 { margin: 0; font-size: 13px; color: #666; font-weight: 500; }
    .metric-card h1 { margin: 4px 0 0; font-size: 32px; font-weight: 700; color: #1F3864; }
    .metric-card p  { margin: 2px 0 0; font-size: 12px; color: #999; }
    .section-title  { font-size: 16px; font-weight: 700; color: #1F3864;
                      border-left: 4px solid #1F3864; padding-left: 10px; margin: 20px 0 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 색상 팔레트 ──────────────────────────────────────────────
STATUS_COLORS = {"미접수": "#FF6B6B", "접수": "#FFA500", "완료": "#4CAF50"}
INQUIRY_COLORS = [
    "#1F3864", "#2E6DA4", "#4A9EDB", "#7BB8E8", "#AED6F1",
]


# ────────────────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load_excel(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """업로드된 Excel 파일을 DataFrame으로 로드"""
    suffix = os.path.splitext(filename)[-1] or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
        tmp_f.write(file_bytes)
        tmp_path = tmp_f.name
    try:
        return load_from_excel(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@st.cache_data(show_spinner=False)
def _load_jira(project: str, from_date: str, username: str, password: str) -> pd.DataFrame:
    """Jira에서 데이터 수집"""
    client = JiraClient(username=username, password=password)
    return client.fetch_issues(project, from_date)


def _make_excel_bytes(
    df: pd.DataFrame,
    stats: dict,
    team_name: str,
    report_month: str,
    selected_projects: list = None,
) -> bytes:
    """Excel 리포트를 메모리에서 생성하여 bytes 반환"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_f:
        tmp_path = tmp_f.name
    try:
        generate_report(
            df, stats, team_name, report_month,
            output_path=tmp_path,
            selected_projects=selected_projects,
        )
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _metric_card(label: str, value, sub: str = "") -> str:
    return f"""
    <div class="metric-card">
        <h3>{label}</h3>
        <h1>{value}</h1>
        <p>{sub}</p>
    </div>
    """


# ────────────────────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 SR 리포팅")
    st.divider()

    st.subheader("⚙️ 기본 설정")

    # 리포트 월 선택
    now = datetime.now()
    report_month = st.text_input(
        "리포트 대상 월 (YYYY-MM)",
        value=now.strftime("%Y-%m"),
        placeholder="예: 2026-02",
    )

    st.divider()
    st.subheader("📂 데이터 소스")
    source = st.radio(
        "데이터 가져오기",
        ["Excel 파일 업로드", "Jira 직접 연동"],
        index=0,
    )

    df_raw = None
    data_loaded = False

    if source == "Excel 파일 업로드":
        uploaded = st.file_uploader(
            "Excel RAW 데이터 (.xlsx)",
            type=["xlsx"],
            help="Jira에서 내보낸 RAW 데이터 Excel 파일",
        )
        if uploaded:
            with st.spinner("데이터 로드 중..."):
                try:
                    df_raw = _load_excel(uploaded.read(), uploaded.name)
                    data_loaded = True
                    st.success(f"✅ {len(df_raw):,}건 로드 완료")
                except Exception as e:
                    st.error(f"❌ 파일 로드 실패: {e}")

    else:  # Jira 직접 연동
        jira_url = st.text_input("Jira URL", value="https://jira.sinc.co.kr")
        jira_project = st.text_input("프로젝트 코드", value="AMDP1")
        jira_from = st.text_input("데이터 시작일", value="2025-01-01")
        jira_user = st.text_input("사용자 ID")
        jira_pw = st.text_input("비밀번호", type="password")

        if st.button("🔄 Jira 데이터 수집", use_container_width=True):
            if not jira_user or not jira_pw:
                st.error("사용자 ID와 비밀번호를 입력하세요.")
            else:
                with st.spinner("Jira에서 데이터 수집 중..."):
                    try:
                        df_raw = _load_jira(jira_project, jira_from, jira_user, jira_pw)
                        data_loaded = True
                        st.success(f"✅ {len(df_raw):,}건 수집 완료")
                    except Exception as e:
                        st.error(f"❌ Jira 연동 실패: {e}")

    if data_loaded and df_raw is not None:
        # ── 프로젝트(팀) 다중 선택 ────────────────────────────
        st.divider()
        st.subheader("🏢 팀 선택")

        available_projects = sorted(df_raw["프로젝트"].dropna().unique().tolist())
        selected_projects = st.multiselect(
            "프로젝트(팀) 선택",
            options=available_projects,
            default=available_projects,
            help="선택한 팀의 데이터만 리포트에 반영됩니다. Excel은 팀별 시트로 분리됩니다.",
        )

        # 팀 이름 자동 추출
        if selected_projects:
            team_names = [
                PROJECT_TEAM_NAME_MAP.get(p, p.replace(" 업무 관리", "").strip())
                for p in selected_projects
            ]
            if len(team_names) == len(available_projects):
                team_name = "전체"
            else:
                team_name = " / ".join(team_names)
        else:
            team_name = "전체"
            selected_projects = available_projects  # 미선택 시 전체 사용

        st.caption(f"📌 팀 이름: **{team_name}**")

        st.divider()
        if not selected_projects:
            st.warning("⚠️ 최소 1개 팀을 선택하세요.")
        elif st.button("📊 리포트 생성", type="primary", use_container_width=True):
            st.session_state["run"] = True
            st.session_state["df_raw"] = df_raw
            st.session_state["team_name"] = team_name
            st.session_state["report_month"] = report_month
            st.session_state["selected_projects"] = selected_projects


# ────────────────────────────────────────────────────────────
# 메인 콘텐츠
# ────────────────────────────────────────────────────────────
if "run" not in st.session_state:
    # 초기 화면
    st.title("📊 SR 리포팅 자동화 대시보드")
    st.markdown("""
    **사용 방법:**
    1. 왼쪽 사이드바에서 팀 이름과 리포트 대상 월을 설정합니다.
    2. 데이터 소스를 선택합니다.
       - **Excel 파일 업로드**: Jira에서 내보낸 RAW 데이터를 업로드합니다.
       - **Jira 직접 연동**: Jira 계정 정보를 입력하여 자동으로 데이터를 가져옵니다.
    3. **리포트 생성** 버튼을 클릭합니다.
    """)
    st.info("👈 사이드바에서 데이터를 불러온 후 '리포트 생성' 버튼을 클릭하세요.")
    st.stop()

# ── 데이터 처리 ──────────────────────────────────────────────
_selected_projects = st.session_state.get("selected_projects", [])

with st.spinner("데이터 정제 및 통계 계산 중..."):
    df_all = process(st.session_state["df_raw"].copy())

    # 프로젝트 필터 적용
    if _selected_projects:
        df = df_all[df_all["프로젝트"].isin(_selected_projects)].copy()
    else:
        df = df_all.copy()

    stats = generate_summary_stats(df, st.session_state["report_month"])
    _team = st.session_state["team_name"]
    _month = st.session_state["report_month"]

# ── 프로젝트 필터 배너 ───────────────────────────────────────
if _selected_projects:
    all_projects = sorted(df_all["프로젝트"].dropna().unique().tolist())
    if set(_selected_projects) == set(all_projects):
        filter_label = "전체 팀"
    else:
        short_names = [
            PROJECT_TEAM_NAME_MAP.get(p, p.replace(" 업무 관리", ""))
            for p in _selected_projects
        ]
        filter_label = " | ".join(short_names)
    st.info(f"🔍 **필터 적용 중**: {filter_label} &nbsp;·&nbsp; {len(df):,}건", icon=None)

# ── 헤더 ─────────────────────────────────────────────────────
col_title, col_dl = st.columns([7, 3])
with col_title:
    st.title(f"📊 {_team} SR 현황 — {_month}")
    total = stats["total"]
    st.caption(
        f"전체 {total['합계']:,}건 · 미접수 {total['미접수']} · "
        f"접수 {total['접수']} · 완료 {total['완료']}"
    )
with col_dl:
    st.write("")
    st.write("")
    with st.spinner("Excel 리포트 준비 중..."):
        excel_bytes = _make_excel_bytes(df, stats, _team, _month, _selected_projects)
    st.download_button(
        label="⬇️ Excel 리포트 다운로드",
        data=excel_bytes,
        file_name=f"SR_Report_{_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )

st.divider()

# ── 탭 구성 ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 요약 대시보드", "📋 처리 현황(상세)", "⚠️ 장기 미처리", "🗂️ 원본 데이터", "📝 DML 처리 현황"]
)


# ════════════════════════════════════════════════════════════
# 탭 1: 요약 대시보드
# ════════════════════════════════════════════════════════════
with tab1:
    total = stats["total"]
    monthly = stats["monthly"]
    rates = stats["rates"]
    avg = stats.get("avg_times_monthly", {})
    long_pending = stats.get("long_pending", pd.DataFrame())

    # ── KPI 카드 ──
    st.markdown('<div class="section-title">■ 전체 현황</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    kpis = [
        (c1, "전체 SR", f"{total['합계']:,}건", "2025년 이후 누적"),
        (c2, "미접수", f"{total['미접수']:,}건", "처리 대기"),
        (c3, "접수 중", f"{total['접수']:,}건", "처리 진행"),
        (c4, "완료", f"{total['완료']:,}건", "처리 완료"),
        (c5, "접수율", f"{rates['접수율']}%", "(접수+완료) / 전체"),
        (c6, "처리율", f"{rates['처리율']}%", "완료 / 전체"),
    ]
    for col, label, value, sub in kpis:
        with col:
            st.markdown(_metric_card(label, value, sub), unsafe_allow_html=True)

    st.write("")

    # ── 당월 KPI ──
    st.markdown(f'<div class="section-title">■ 당월 현황 ({_month})</div>', unsafe_allow_html=True)
    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    month_total = monthly["합계"]
    month_accepted = monthly["접수"] + monthly["완료"]
    m_rate = round(month_accepted / month_total * 100, 1) if month_total > 0 else 0
    m_done_rate = round(monthly["완료"] / month_total * 100, 1) if month_total > 0 else 0
    avg_accept = avg.get("생성일_접수일")
    avg_resolve = avg.get("생성일_완료일")

    month_kpis = [
        (mc1, "당월 SR", f"{month_total:,}건", "이번 달 생성"),
        (mc2, "미접수", f"{monthly['미접수']:,}건", ""),
        (mc3, "접수 중", f"{monthly['접수']:,}건", ""),
        (mc4, "완료", f"{monthly['완료']:,}건", ""),
        (mc5, "평균 접수시간", f"{avg_accept if avg_accept else '-'}일", "생성일→접수일"),
        (mc6, "평균 처리시간", f"{avg_resolve if avg_resolve else '-'}일", "생성일→완료일"),
    ]
    for col, label, value, sub in month_kpis:
        with col:
            st.markdown(_metric_card(label, value, sub), unsafe_allow_html=True)

    st.write("")
    st.divider()

    # ── 차트 영역 ──
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown('<div class="section-title">■ 처리상태 분포</div>', unsafe_allow_html=True)
        status_df = pd.DataFrame([
            {"처리상태": s, "건수": int(df["처리상태"].value_counts().get(s, 0))}
            for s in PROCESS_STATUS_ORDER
        ])
        fig_status = px.pie(
            status_df,
            values="건수",
            names="처리상태",
            color="처리상태",
            color_discrete_map=STATUS_COLORS,
            hole=0.45,
        )
        fig_status.update_traces(textposition="outside", textinfo="percent+label+value")
        fig_status.update_layout(
            height=320,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with chart_col2:
        st.markdown('<div class="section-title">■ 문의유형별 건수</div>', unsafe_allow_html=True)
        inquiry_df = pd.DataFrame([
            {
                "문의유형": itype.split(". ", 1)[-1],  # "1. 기능문의" → "기능문의"
                "건수": int((df["문의유형"] == itype).sum()),
            }
            for itype in INQUIRY_TYPE_ORDER
        ])
        fig_inquiry = px.bar(
            inquiry_df,
            x="건수",
            y="문의유형",
            orientation="h",
            color="문의유형",
            color_discrete_sequence=INQUIRY_COLORS,
            text="건수",
        )
        fig_inquiry.update_traces(textposition="outside")
        fig_inquiry.update_layout(
            height=320,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_inquiry, use_container_width=True)

    # ── 문의유형 × 처리상태 stacked bar ──
    st.markdown('<div class="section-title">■ 문의유형별 처리상태</div>', unsafe_allow_html=True)
    stacked_data = []
    for itype in INQUIRY_TYPE_ORDER:
        df_t = df[df["문의유형"] == itype]
        for s in PROCESS_STATUS_ORDER:
            stacked_data.append({
                "문의유형": itype.split(". ", 1)[-1],
                "처리상태": s,
                "건수": int((df_t["처리상태"] == s).sum()),
            })
    stacked_df = pd.DataFrame(stacked_data)
    fig_stacked = px.bar(
        stacked_df,
        x="문의유형",
        y="건수",
        color="처리상태",
        color_discrete_map=STATUS_COLORS,
        barmode="stack",
        text_auto=True,
    )
    fig_stacked.update_layout(
        height=340,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis_title="",
        yaxis_title="건수",
    )
    st.plotly_chart(fig_stacked, use_container_width=True)

    # ── 접수율 처리율 테이블 ──
    st.markdown('<div class="section-title">■ 접수율 및 처리율</div>', unsafe_allow_html=True)
    rate_rows = []
    inquiry_rates = stats.get("inquiry_rates", {})
    for itype in INQUIRY_TYPE_ORDER:
        r = inquiry_rates.get(itype, {})
        rate_rows.append({
            "문의유형": itype,
            "건수": r.get("건수", 0),
            "접수율(%)": r.get("접수율", 0),
            "처리율(%)": r.get("처리율", 0),
        })
    rate_df = pd.DataFrame(rate_rows)
    st.dataframe(
        rate_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "접수율(%)": st.column_config.ProgressColumn(
                "접수율(%)", min_value=0, max_value=100, format="%.1f%%"
            ),
            "처리율(%)": st.column_config.ProgressColumn(
                "처리율(%)", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )


# ════════════════════════════════════════════════════════════
# 탭 2: SR 처리 현황(상세)
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">■ SR 처리 현황(상세) — 시스템별</div>', unsafe_allow_html=True)
    st.caption("단위: 건")

    # 시스템명 × 문의유형 × 처리상태 피벗
    systems = sorted(df["시스템명"].dropna().unique())
    rows = []
    for sys_name in systems:
        df_s = df[df["시스템명"] == sys_name]
        row = {"시스템명": sys_name}
        sc = df_s["처리상태"].value_counts()
        row["미접수"] = int(sc.get("미접수", 0))
        row["접수"] = int(sc.get("접수", 0))
        row["완료"] = int(sc.get("완료", 0))
        row["합계"] = len(df_s)
        for itype in INQUIRY_TYPE_ORDER:
            short = itype.split(". ", 1)[-1]
            df_t = df_s[df_s["문의유형"] == itype]
            tc = df_t["처리상태"].value_counts()
            row[f"{short}_미접수"] = int(tc.get("미접수", 0))
            row[f"{short}_접수"] = int(tc.get("접수", 0))
            row[f"{short}_완료"] = int(tc.get("완료", 0))
            row[f"{short}_합계"] = len(df_t)
        rows.append(row)

    # 총합계 행
    total_row = {"시스템명": "★ 총합계"}
    sc_all = df["처리상태"].value_counts()
    total_row["미접수"] = int(sc_all.get("미접수", 0))
    total_row["접수"] = int(sc_all.get("접수", 0))
    total_row["완료"] = int(sc_all.get("완료", 0))
    total_row["합계"] = len(df)
    for itype in INQUIRY_TYPE_ORDER:
        short = itype.split(". ", 1)[-1]
        df_t = df[df["문의유형"] == itype]
        tc = df_t["처리상태"].value_counts()
        total_row[f"{short}_미접수"] = int(tc.get("미접수", 0))
        total_row[f"{short}_접수"] = int(tc.get("접수", 0))
        total_row[f"{short}_완료"] = int(tc.get("완료", 0))
        total_row[f"{short}_합계"] = len(df_t)
    rows.append(total_row)

    detail_df = pd.DataFrame(rows)
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    # 시스템별 stacked bar
    st.markdown('<div class="section-title">■ 시스템별 처리상태</div>', unsafe_allow_html=True)
    sys_chart_data = []
    for sys_name in systems:
        df_s = df[df["시스템명"] == sys_name]
        sc = df_s["처리상태"].value_counts()
        for s in PROCESS_STATUS_ORDER:
            sys_chart_data.append({
                "시스템명": sys_name.replace("[백]", "").replace("[사] ", ""),
                "처리상태": s,
                "건수": int(sc.get(s, 0)),
            })
    fig_sys = px.bar(
        pd.DataFrame(sys_chart_data),
        x="시스템명",
        y="건수",
        color="처리상태",
        color_discrete_map=STATUS_COLORS,
        barmode="stack",
        text_auto=True,
    )
    fig_sys.update_layout(
        height=400,
        margin=dict(t=20, b=80, l=20, r=20),
        xaxis_tickangle=-35,
    )
    st.plotly_chart(fig_sys, use_container_width=True)


# ════════════════════════════════════════════════════════════
# 탭 3: 장기 미처리 SR
# ════════════════════════════════════════════════════════════
with tab3:
    long_pending = stats.get("long_pending", pd.DataFrame())
    st.markdown(
        f'<div class="section-title">■ 장기 미처리 SR (90일 이상) — {len(long_pending)}건</div>',
        unsafe_allow_html=True,
    )

    if len(long_pending) == 0:
        st.success("✅ 90일 이상 장기 미처리 SR이 없습니다.")
    else:
        st.warning(f"⚠️ {len(long_pending)}건의 장기 미처리 SR이 존재합니다.")

        # 시스템별 장기 미처리 현황 차트
        lp_sys = long_pending["시스템명"].value_counts().reset_index()
        lp_sys.columns = ["시스템명", "건수"]
        fig_lp = px.bar(
            lp_sys,
            x="시스템명",
            y="건수",
            color_discrete_sequence=["#FF6B6B"],
            text="건수",
        )
        fig_lp.update_layout(height=300, margin=dict(t=20, b=60, l=20, r=20))
        st.plotly_chart(fig_lp, use_container_width=True)

        # 목록 테이블
        display_cols = [
            c for c in ["키", "요약", "시스템명", "서비스", "처리상태", "문의유형", "생성일", "담당자"]
            if c in long_pending.columns
        ]
        st.dataframe(long_pending[display_cols], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
# 탭 4: 원본 데이터
# ════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">■ 정제된 RAW 데이터</div>', unsafe_allow_html=True)
    st.caption(f"총 {len(df):,}건")

    # 필터
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_system = st.multiselect(
            "시스템명 필터",
            options=sorted(df["시스템명"].dropna().unique()),
            default=[],
        )
    with fc2:
        f_status = st.multiselect(
            "처리상태 필터",
            options=PROCESS_STATUS_ORDER,
            default=[],
        )
    with fc3:
        f_inquiry = st.multiselect(
            "문의유형 필터",
            options=INQUIRY_TYPE_ORDER,
            default=[],
        )

    df_filtered = df.copy()
    if f_system:
        df_filtered = df_filtered[df_filtered["시스템명"].isin(f_system)]
    if f_status:
        df_filtered = df_filtered[df_filtered["처리상태"].isin(f_status)]
    if f_inquiry:
        df_filtered = df_filtered[df_filtered["문의유형"].isin(f_inquiry)]

    display_cols = [
        c for c in [
            "키", "요약", "시스템명", "서비스", "처리상태", "문의유형",
            "생성일", "접수일", "해결일", "담당자",
            "처리시간_접수(일)", "처리시간_해결(일)",
            "업무유형(FTE)", "업무구분(FTE)",
        ]
        if c in df_filtered.columns
    ]
    st.dataframe(
        df_filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        height=500,
    )
    st.caption(f"필터 결과: {len(df_filtered):,}건")


# ════════════════════════════════════════════════════════════
# 탭 5: DML 처리 현황 (3. 데이터 추출 및 수정)
# ════════════════════════════════════════════════════════════
with tab5:
    dml_data = stats.get("data_request_report", [])

    st.markdown(
        f'<div class="section-title">■ DML 처리 현황 (3. 데이터 추출 및 수정) — {_month}</div>',
        unsafe_allow_html=True,
    )
    st.caption("단위: 건 · 당월 생성 SR 기준")

    if not dml_data:
        st.info(f"해당 월({_month})에 '3. 데이터 추출 및 수정' 데이터가 없습니다.")
    else:
        # ── 처리 현황 요약 테이블 ──
        summary_rows = [
            {
                "시스템명": r["시스템명"],
                "미접수": r["미접수"],
                "접수": r["접수"],
                "완료": r["완료"],
                "합계": r["합계"],
            }
            for r in dml_data
        ]
        total_row = {
            "시스템명": "★ 총합계",
            "미접수": sum(r["미접수"] for r in dml_data),
            "접수": sum(r["접수"] for r in dml_data),
            "완료": sum(r["완료"] for r in dml_data),
            "합계": sum(r["합계"] for r in dml_data),
        }
        summary_rows.append(total_row)
        dml_summary_df = pd.DataFrame(summary_rows)
        st.dataframe(dml_summary_df, use_container_width=True, hide_index=True)

        st.write("")

        # ── 시스템별 주요 사유 ──
        st.markdown(
            '<div class="section-title">■ 시스템별 주요 사유</div>',
            unsafe_allow_html=True,
        )
        for r in dml_data:
            label = f"**{r['시스템명']}** — 미접수 {r['미접수']} / 접수 {r['접수']} / 완료 {r['완료']} (합계 {r['합계']}건)"
            with st.expander(label, expanded=False):
                if r["주요_사유_목록"]:
                    for item in r["주요_사유_목록"]:
                        st.markdown(item)
                else:
                    st.caption("요약 정보 없음")
