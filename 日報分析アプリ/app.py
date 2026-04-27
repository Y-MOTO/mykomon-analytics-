"""
MyKomon 日報分析 & 人事経営相談 ── Streamlit（タブ統合版）
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import anthropic
import markdown as md_lib
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from dateutil.relativedelta import relativedelta

import ai_report
import analyzer
from knowledge import build_system_prompt
from parser import load_csvs

# ── パス定数 ────────────────────────────────────────────────────────────────
MANUAL_PATH      = Path(__file__).parent / "使用マニュアル.md"
INSTRUCTION_PATH = Path(__file__).parent / "instruction_director.md"
EXPORT_SCRIPT    = Path(__file__).parent.parent / "csv_export" / "mykomon_export_http.py"

GAP_CATEGORIES = [
    "（自動判断）", "ボトムアップ・自主経営", "業務の見える化・日報",
    "評価制度・人事考課", "給与・報酬体系", "職階・役割分担",
    "有資格者の処遇", "職員の教育・育成", "採用・離職",
    "顧客対応・サービス品質", "G8・海外事例の研究", "経営者の人事一般相談", "その他",
]

# ── ページ設定 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MyKomon 日報分析",
    page_icon="📊",
    layout="wide",
)

# ── API キー ────────────────────────────────────────────────────────────────
def get_api_key() -> str:
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")

_key = get_api_key()
if _key:
    os.environ["ANTHROPIC_API_KEY"] = _key

# ── ダイアログ ──────────────────────────────────────────────────────────────
@st.dialog("📖 使用マニュアル", width="large")
def show_manual():
    if MANUAL_PATH.exists():
        st.markdown(MANUAL_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("マニュアルファイルが見つかりません。")

@st.dialog("📋 所長向けインストラクション", width="large")
def show_instruction():
    if INSTRUCTION_PATH.exists():
        st.markdown(INSTRUCTION_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("インストラクションファイルが見つかりません。")

# ── ユーティリティ ──────────────────────────────────────────────────────────
def get_months_in_range(sy, sm, ey, em):
    months, cur = [], datetime(sy, sm, 1)
    end = datetime(ey, em, 1)
    while cur <= end:
        months.append((cur.year, cur.month))
        cur += relativedelta(months=1)
    return months


def call_claude_consult(conversation: list) -> str:
    client = anthropic.Anthropic(api_key=get_api_key())
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=build_system_prompt(),
        messages=conversation,
    )
    return response.content[0].text


def format_gap_prefill(gap: dict) -> str:
    lines = [
        f"【日報分析データ {gap.get('period', '不明')}】（{gap.get('generated_at', '')} 取得）",
        (f"全日報件数：{gap.get('total_records', 0):,}件　"
         f"タグ付き：{gap.get('tagged_records', 0):,}件"
         f"（{gap.get('tag_rate_pct', 0):.1f}%）　"
         f"詰まり：{gap.get('stuck_count', 0)}件"),
    ]
    if gap.get("low_tag_rate_staff"):
        lines.append("\n■ タグ付き率が低い担当者（上位5名）")
        for name, rate in gap["low_tag_rate_staff"]:
            lines.append(f"・{name}：{rate:.1f}%")
    if gap.get("top_blockers"):
        lines.append("\n■ 主な阻害要因")
        for i, (reason, count) in enumerate(gap["top_blockers"], 1):
            lines.append(f"{i}位：{reason}（{count}件）")
    if gap.get("red_clients"):
        lines.append("\n■ 緊急対応が必要な顧問先")
        for c in gap["red_clients"]:
            lines.append(f"・{c}")
    if gap.get("monthly_stuck_rates"):
        lines.append("\n■ 月次詰まり率（直近）")
        for month, rate in list(gap["monthly_stuck_rates"].items())[-3:]:
            lines.append(f"・{month}：{rate:.1f}%")
    lines += ["\n---", "【所長の補足・感じているずれ（任意）】", "（ここに追記してください）"]
    return "\n".join(lines)

# ── セッション初期化 ────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "gap_data" not in st.session_state:
    st.session_state.gap_data = None
if "consult_conversation" not in st.session_state:
    st.session_state.consult_conversation = []
if "consult_history" not in st.session_state:
    st.session_state.consult_history = []

# ── サイドバー ──────────────────────────────────────────────────────────────
st.markdown("""<style>
section[data-testid="stSidebar"] .stButton button {
    font-size: 12px !important; padding: 4px 6px !important;
}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**⚙️ 設定**")

    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("📖 マニュアル", use_container_width=True):
            show_manual()
    with _c2:
        if st.button("📋 運用説明", use_container_width=True):
            show_instruction()

    st.divider()
    st.markdown("**🔐 MyKomon認証**")
    mykomon_user = st.text_input("MyKomon ID", key="mk_user",
                                  label_visibility="collapsed", placeholder="MyKomon ID")
    mykomon_pass = st.text_input("パスワード", type="password", key="mk_pass",
                                  label_visibility="collapsed", placeholder="MyKomon パスワード")

    st.markdown("**📥 データ取得**")
    _now = datetime.now()
    _years = list(range(_now.year - 3, _now.year + 1))
    _c1, _c2 = st.columns(2)
    with _c1:
        start_year  = st.selectbox("開始年", _years, index=len(_years) - 1, key="sy")
        start_month = st.selectbox("開始月", range(1, 13),
                                   index=max(0, _now.month - 4), key="sm",
                                   format_func=lambda m: f"{m}月")
    with _c2:
        end_year    = st.selectbox("終了年", _years, index=len(_years) - 1, key="ey")
        end_month   = st.selectbox("終了月", range(1, 13),
                                   index=max(0, _now.month - 2), key="em",
                                   format_func=lambda m: f"{m}月")
    export_btn = st.button("📥 CSVをエクスポート実行", use_container_width=True, type="primary")

    st.markdown("**📂 CSVアップロード**（手動）")
    uploaded_files = st.file_uploader(
        "CSVをアップロード", type="csv", accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if st.button("📥 CSVを読み込む", use_container_width=True, disabled=not uploaded_files):
        with st.spinner("読み込み中..."):
            try:
                tmp_dir = tempfile.mkdtemp()
                for uf in uploaded_files:
                    (Path(tmp_dir) / uf.name).write_bytes(uf.read())
                df_loaded = load_csvs(tmp_dir)
                st.session_state.df = df_loaded
                st.session_state.summary_text = analyzer.build_summary_text(df_loaded)
                st.session_state.ai_report = None
                st.session_state.analysis_conversation = []
                st.success(f"{len(df_loaded):,} 件読み込みました")
                st.rerun()
            except Exception as e:
                st.error(f"読み込みエラー: {e}")

    if not get_api_key():
        st.divider()
        api_input = st.text_input("Anthropic API キー", type="password",
                                   help="未設定の場合のみ入力してください")
        if api_input:
            os.environ["ANTHROPIC_API_KEY"] = api_input
            st.rerun()
    else:
        st.success("API キー設定済み")

# ── CSVエクスポート実行 ─────────────────────────────────────────────────────
if export_btn:
    months = get_months_in_range(start_year, start_month, end_year, end_month)
    if not months:
        st.error("終了月が開始月より前になっています。")
    elif not mykomon_user or not mykomon_pass:
        st.error("MyKomon IDとパスワードを入力してください。")
    elif not EXPORT_SCRIPT.exists():
        st.error(f"エクスポートスクリプトが見つかりません: {EXPORT_SCRIPT}")
    else:
        st.info(f"MyKomonにログインして {len(months)} ヶ月分をエクスポートします…")
        progress = st.progress(0)
        status   = st.empty()
        errors   = []
        tmp_dir  = tempfile.mkdtemp()
        for i, (yr, mo) in enumerate(months):
            status.text(f"取得中: {yr}年{mo}月　({i+1} / {len(months)})")
            cmd = [sys.executable, str(EXPORT_SCRIPT),
                   "--year", str(yr), "--month", str(mo),
                   "--save-dir", tmp_dir,
                   "--username", mykomon_user,
                   "--password", mykomon_pass]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
            if result.returncode != 0:
                errors.append(f"{yr}年{mo}月: {result.stderr[-300:]}")
            progress.progress((i + 1) / len(months))
        status.empty()
        if errors:
            st.error("エクスポートに失敗しました:\n" + "\n".join(errors))
        else:
            with st.spinner("データを読み込み中..."):
                df_loaded = load_csvs(tmp_dir)
                st.session_state.df = df_loaded
                st.session_state.summary_text = analyzer.build_summary_text(df_loaded)
                st.session_state.ai_report = None
                st.session_state.analysis_conversation = []
            st.success(f"{len(months)} ヶ月分完了。{len(df_loaded):,} 件読み込みました。")
            st.rerun()

# ── メインUI ────────────────────────────────────────────────────────────────
st.title("📊 MyKomon 日報分析ダッシュボード")

df = st.session_state.get("df", pd.DataFrame())

tagged = df[df["has_tag"] == True].copy() if ("has_tag" in df.columns and not df.empty) else pd.DataFrame()

from parser import date_column as _date_col
period_str = "不明"
tag_rate_pct = 0.0
if not df.empty:
    d_col = _date_col(df)
    if d_col:
        dates = pd.to_datetime(df[d_col], errors="coerce").dropna()
        if not dates.empty:
            min_d = dates.min().strftime("%Y年%-m月") if os.name != "nt" else dates.min().strftime("%Y年%#m月")
            max_d = dates.max().strftime("%Y年%-m月") if os.name != "nt" else dates.max().strftime("%Y年%#m月")
            period_str = min_d if min_d == max_d else f"{min_d} 〜 {max_d}"
            tag_rate_pct = round(len(tagged) / len(df) * 100, 1) if len(df) > 0 else 0.0
            st.info(f"📅 読み込み期間：**{period_str}**　｜　全 {len(df):,} 件　｜　タグ付き {len(tagged):,} 件（{tag_rate_pct}%）")
    if tagged.empty:
        st.caption("タグ付き日報はまだありません。全件ベースの活動量分析を表示しています。")

_NO_DATA = "データ未読込です。サイドバーからCSVをエクスポートまたはアップロードしてください。"

# ── タブ ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👤 担当者別分析",
    "🏢 顧問先別分析",
    "🔄 業務×工程 ボトルネック",
    "📅 月次トレンド",
    "🤖 AI分析レポート",
    "💼 人事経営相談",
])

# ─ TAB 1 ────────────────────────────────────────────────────────────────────
with tab1:
    if df.empty:
        st.info(_NO_DATA)
    st.subheader("担当者別 活動量（全件）")
    sa = analyzer.staff_activity_summary(df)
    if sa.empty:
        st.info("データなし")
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            fig = px.bar(sa.head(20), x="担当者", y="日報件数",
                         color_discrete_sequence=["#4c8bf5"], title="担当者別 日報件数（全件）")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.dataframe(sa, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("担当者別 拡張機能使用率（タグ付き率）")
    tr = analyzer.staff_tag_rate(df)
    if tr.empty:
        st.info("担当者列が見つかりません")
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            fig = px.bar(tr, x="担当者", y="タグ付き率(%)", color="タグ付き率(%)",
                         color_continuous_scale=["#e05252", "#f5c518", "#27ae60"],
                         range_color=[0, 100], title="担当者別 タグ付き率（%）　←低いほど未使用")
            fig.update_xaxes(tickangle=45)
            fig.update_yaxes(range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.dataframe(tr, use_container_width=True, hide_index=True)

    if not tagged.empty:
        st.divider()
        st.subheader("担当者別 詰まり分析（タグ付き）")
        sb = analyzer.staff_blocking_summary(df)
        if not sb.empty:
            col_a, col_b = st.columns([3, 2])
            with col_a:
                fig = px.bar(sb.head(15), x="担当者", y="詰まり件数",
                             color_discrete_sequence=["#e05252"], title="担当者別 詰まり件数")
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.dataframe(sb, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("担当者別 阻害要因内訳")
        rb = analyzer.staff_blocking_reasons(df)
        if not rb.empty:
            staff_list = rb["担当者"].unique().tolist()
            selected = st.selectbox("担当者を選択", ["（全員）"] + staff_list)
            filtered = rb if selected == "（全員）" else rb[rb["担当者"] == selected]
            fig2 = px.bar(filtered.head(20), x="件数", y="阻害要因",
                          color="担当者" if selected == "（全員）" else None,
                          orientation="h", title="阻害要因 内訳")
            fig2.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, use_container_width=True)

# ─ TAB 2 ────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("顧問先別 対応件数（全件）")
    ca = analyzer.client_activity_summary(df)
    if ca.empty:
        st.info("顧問先列が見つかりません（CSVのカラム名を確認）")
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            fig = px.bar(ca.head(20), x="顧問先", y="対応件数",
                         color_discrete_sequence=["#4c8bf5"], title="顧問先別 対応件数（全件）")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.dataframe(ca.head(20), use_container_width=True, hide_index=True)

    if not tagged.empty:
        st.divider()
        st.subheader("顧問先別 詰まり分析（タグ付き）")
        cb = analyzer.client_blocking_summary(df)
        if not cb.empty:
            col_a, col_b = st.columns([3, 2])
            with col_a:
                fig = px.bar(cb.head(20), x="顧問先", y="詰まり件数", color="Red件数",
                             color_continuous_scale=["#f5c518", "#e05252"],
                             title="顧問先別 詰まり件数（色: Red件数）")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.dataframe(cb.head(20), use_container_width=True, hide_index=True)

# ─ TAB 3 ────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("業務区分 × 工程 ボトルネック（タグ付きのみ）")
    if tagged.empty:
        st.info("タグ付き日報が蓄積されると表示されます。")
    else:
        pb = analyzer.process_bottleneck(df)
        if pb.empty:
            st.info("工程タグが付いた詰まり日報がありません")
        else:
            pivot = pb.pivot_table(index="工程", columns="業務区分", values="件数", fill_value=0)
            fig = px.imshow(pivot, color_continuous_scale="Reds",
                            title="業務区分 × 工程 ヒートマップ（詰まり件数）", aspect="auto")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(pb, use_container_width=True, hide_index=True)

# ─ TAB 4 ────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("月次 日報件数推移（全件）")
    mat = analyzer.monthly_all_trend(df)
    if mat.empty:
        st.info("日付列が見つかりません")
    else:
        fig = px.bar(mat, x="月", y="日報件数", color_discrete_sequence=["#4c8bf5"],
                     title="月別 日報件数（全件）")
        st.plotly_chart(fig, use_container_width=True)
        if "工数合計（分）" in mat.columns:
            mat["工数合計（時間）"] = (mat["工数合計（分）"] / 60).round(1)
            fig2 = px.bar(mat, x="月", y="工数合計（時間）",
                          color_discrete_sequence=["#36a2eb"], title="月別 工数合計（時間）")
            st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(mat, use_container_width=True, hide_index=True)

    if not tagged.empty:
        st.divider()
        st.subheader("月次ステータス推移（タグ付き）")
        mt = analyzer.monthly_trend(df)
        if not mt.empty:
            fig = px.line(mt, x="月", y=["完了", "継続", "中断"],
                          markers=True, title="月別 ステータス推移")
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.bar(mt, x="月", y="詰まり率", title="月別 詰まり率（%）",
                          color_discrete_sequence=["#e05252"])
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(mt, use_container_width=True, hide_index=True)

# ─ TAB 5: AI分析 ────────────────────────────────────────────────────────────
with tab5:
    st.subheader("🤖 AI分析レポート（Claude Sonnet 4.6）")

    if not get_api_key():
        st.warning("サイドバーに Anthropic API キーを入力してください。")

    summary_text = ""
    if df.empty:
        st.info(_NO_DATA)
    elif get_api_key():
        summary_text = st.session_state.get("summary_text", "")
        if not summary_text:
            summary_text = analyzer.build_summary_text(df)
            st.session_state.summary_text = summary_text

    if summary_text:
        with st.expander("集計データ（AIへの入力）", expanded=False):
            st.text(summary_text)

    if st.button("📝 AIレポートを生成", use_container_width=True, disabled=not summary_text):
        with st.spinner("Claude が分析中... (30〜60秒)"):
            try:
                report = ai_report.generate_report(summary_text)
                st.session_state.ai_report = report
                st.session_state.analysis_conversation = []
            except Exception as e:
                st.error(f"エラー: {e}")

    if st.session_state.get("ai_report"):
        st.markdown("### レポート")
        full_report_md = ai_report.ANALYSIS_PREMISES_MD + st.session_state.ai_report
        st.markdown(full_report_md)

        st.divider()
        st.markdown("#### 📨 人事経営相談に送る")
        st.caption("集計データをTab6「人事経営相談」の相談入力欄に自動セットします")
        if st.button("📨 人事経営相談に送る", use_container_width=True, key="send_to_consult"):
            gap = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "period": period_str,
                "tag_rate_pct": float(tag_rate_pct),
                "total_records": int(len(df)),
                "tagged_records": int(len(tagged)),
            }
            _sb = analyzer.staff_blocking_summary(df)
            gap["stuck_count"] = int(_sb["詰まり件数"].sum()) if not _sb.empty else 0
            _rb = analyzer.staff_blocking_reasons(df)
            if not _rb.empty:
                _top = _rb.groupby("阻害要因")["件数"].sum().sort_values(ascending=False).head(5)
                gap["top_blockers"] = [[k, int(v)] for k, v in _top.items()]
            else:
                gap["top_blockers"] = []
            _tr = analyzer.staff_tag_rate(df)
            if not _tr.empty:
                _low = _tr.nsmallest(5, "タグ付き率(%)")
                gap["low_tag_rate_staff"] = [[r["担当者"], float(r["タグ付き率(%)"])]
                                              for _, r in _low.iterrows()]
            else:
                gap["low_tag_rate_staff"] = []
            _cb = analyzer.client_blocking_summary(df)
            if not _cb.empty and "Red件数" in _cb.columns:
                gap["red_clients"] = _cb[_cb["Red件数"] > 0].head(5)["顧問先"].tolist()
            else:
                gap["red_clients"] = []
            _mt = analyzer.monthly_trend(df)
            if not _mt.empty and "詰まり率" in _mt.columns:
                gap["monthly_stuck_rates"] = {str(r["月"]): float(r["詰まり率"])
                                               for _, r in _mt.tail(6).iterrows()}
            else:
                gap["monthly_stuck_rates"] = {}
            st.session_state.gap_data = gap
            st.session_state.consult_prefill = format_gap_prefill(gap)
            st.success("✅ 送りました。「💼 人事経営相談」タブを開いてください。")

        st.divider()
        st.markdown("### フォローアップ質問")
        question = st.text_input("質問を入力してください", key="followup_input")
        if st.button("送信", key="followup_btn") and question:
            with st.spinner("回答中..."):
                try:
                    answer, conv = ai_report.ask_followup(
                        summary_text,
                        st.session_state.get("analysis_conversation", []),
                        question,
                    )
                    st.session_state.analysis_conversation = conv
                except Exception as e:
                    st.error(f"エラー: {e}")

        conv = st.session_state.get("analysis_conversation", [])
        if len(conv) > 2:
            st.markdown("#### 会話履歴")
            for msg in conv[1:]:
                role = "🧑 所長" if msg["role"] == "user" else "🤖 Claude"
                with st.chat_message(msg["role"]):
                    st.markdown(f"**{role}**\n\n{msg['content']}")

# ─ TAB 6: 人事経営相談 ───────────────────────────────────────────────────────
with tab6:
    st.markdown("""
<style>
.consult-header{background:linear-gradient(135deg,#1B3A5C,#4472C4);color:white;
  padding:1.2rem 1.5rem;border-radius:8px;margin-bottom:1.2rem;}
.consult-header h1{color:white;margin:0;font-size:1.4rem;}
.consult-header p{color:#D6E4F7;margin:.3rem 0 0;font-size:.85rem;}
.phase-badge{display:inline-block;background:#27AE60;color:white;padding:2px 10px;
  border-radius:12px;font-size:.8rem;font-weight:bold;margin-bottom:.5rem;}
</style>
<div class="consult-header">
  <h1>💼 人事経営相談AI ── 計画と現実のずれを解決する</h1>
  <p>「うまくいかない」を入力すると、根本原因と改善策を提案します。G8諸国・世界標準の人事事例も参照します。</p>
</div>
""", unsafe_allow_html=True)
    st.markdown('<span class="phase-badge">現在：Phase 1 ── 業務可視化の定着期</span>',
                unsafe_allow_html=True)

    if not get_api_key():
        st.error("サイドバーに Anthropic API キーを入力してください。")

    col_main, col_hist = st.columns([2, 1])

    with col_main:
        # 日報データが届いていれば表示
        gap_data = st.session_state.get("gap_data")
        if gap_data:
            with st.container(border=True):
                st.markdown("**📊 日報分析データ（Tab5から送信済み）**")
                _cg1, _cg2, _cg3 = st.columns(3)
                with _cg1:
                    st.metric("全件数", f"{gap_data.get('total_records', 0):,}")
                with _cg2:
                    st.metric("タグ付き率", f"{gap_data.get('tag_rate_pct', 0):.1f}%")
                with _cg3:
                    st.metric("詰まり件数", gap_data.get("stuck_count", 0))
                if st.button("📥 この結果を相談入力欄にセット", use_container_width=True,
                             type="primary", key="use_gap_data"):
                    st.session_state.consult_prefill = format_gap_prefill(gap_data)
                    st.rerun()

        # カテゴリ選択
        selected_cat = st.selectbox("相談カテゴリ（任意）", GAP_CATEGORIES)

        # 相談例
        with st.expander("💡 相談例（クリックで入力欄にコピー）"):
            examples = [
                "ボトムアップ会議を始めたが誰も発言しない",
                "日報のタグ付き率が20%で上がらない",
                "評価制度を変えたら古参職員が不満を持っている",
                "有資格者が自分だけが評価されていないと言っている",
                "後輩への指導が減って業務品質が下がっている",
                "OKRを設定したが形骸化している",
                "音声入力を使わない職員がいる",
                "集合ボーナスの目標設定をどうすればよいか",
                "ドイツの会計事務所はどのように職員を評価しているか",
                "英国の専門職事務所に学べる離職防止策はあるか",
                "Z世代の職員が増えてきたがどう動機づければよいか",
                "心理的安全性を高めるために所長として何をすべきか",
            ]
            cols = st.columns(2)
            for i, ex in enumerate(examples):
                with cols[i % 2]:
                    if st.button(ex, key=f"cex_{i}", use_container_width=True):
                        st.session_state.consult_prefill = ex
                        st.rerun()

        # 入力欄
        prefill = st.session_state.pop("consult_prefill", "")
        question = st.text_area(
            "計画と現実のずれ・困っていること",
            value=prefill,
            height=120,
            placeholder="例：ボトムアップ会議を始めたが誰も発言しない。何が原因で、どう対処すればよいか。",
            key="consult_question_input",
        )

        cat_note = f"\n\n【相談カテゴリ】{selected_cat}" if selected_cat != "（自動判断）" else ""
        send_btn = st.button("📨 相談する", type="primary", use_container_width=True,
                             disabled=not question.strip(), key="consult_send")

        if send_btn and question.strip():
            user_message = question.strip() + cat_note
            st.session_state.consult_conversation.append({"role": "user", "content": user_message})
            with st.spinner("分析中... (10〜30秒)"):
                try:
                    answer = call_claude_consult(st.session_state.consult_conversation)
                    st.session_state.consult_conversation.append({"role": "assistant", "content": answer})
                    st.session_state.consult_history.append({
                        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "category": selected_cat,
                        "question": question.strip(),
                        "answer": answer,
                    })
                except Exception as e:
                    st.error(f"エラー: {e}")
                    st.session_state.consult_conversation.pop()

        conversation = st.session_state.get("consult_conversation", [])
        if conversation:
            st.divider()
            st.markdown("### 📝 回答")
            for msg in reversed(conversation):
                if msg["role"] == "assistant":
                    st.markdown(msg["content"])
                elif msg["role"] == "user":
                    st.markdown(f"> **相談：** {msg['content']}")
                if msg != conversation[0]:
                    st.divider()

            st.divider()
            followup = st.text_input(
                "フォローアップ質問",
                placeholder="例：具体的にどのような言葉で職員に説明すればよいですか？",
                key="consult_followup",
            )
            if st.button("続けて相談", disabled=not followup.strip(), key="consult_followup_btn"):
                st.session_state.consult_conversation.append({"role": "user", "content": followup.strip()})
                with st.spinner("回答中..."):
                    try:
                        answer = call_claude_consult(st.session_state.consult_conversation)
                        st.session_state.consult_conversation.append({"role": "assistant", "content": answer})
                        st.session_state.consult_history.append({
                            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "category": selected_cat,
                            "question": f"[フォローアップ] {followup.strip()}",
                            "answer": answer,
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
                        st.session_state.consult_conversation.pop()

        if st.button("🗑️ 会話をリセット", key="consult_reset"):
            st.session_state.consult_conversation = []
            st.rerun()

    with col_hist:
        st.markdown("### 🗂️ 過去の相談履歴")
        history = st.session_state.get("consult_history", [])
        if not history:
            st.info("まだ相談履歴がありません。")
        else:
            for item in reversed(history[-20:]):
                label = (f"🕐 {item['datetime']}｜{item['question'][:20]}…"
                         if len(item["question"]) > 20
                         else f"🕐 {item['datetime']}｜{item['question']}")
                with st.expander(label):
                    if item.get("category") and item["category"] != "（自動判断）":
                        st.markdown(f"**カテゴリ：** {item['category']}")
                    st.markdown(f"**相談：** {item['question']}")
                    st.divider()
                    st.markdown(item["answer"])

            st.divider()
            st.download_button(
                label="📥 履歴をJSONで保存",
                data=json.dumps(history, ensure_ascii=False, indent=2),
                file_name=f"consult_history_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
            if st.button("🗑️ 履歴を全削除", use_container_width=True, key="consult_clear_hist"):
                st.session_state.consult_history = []
                st.rerun()
