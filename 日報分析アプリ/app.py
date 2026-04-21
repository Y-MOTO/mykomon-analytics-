"""
MyKomon 日報分析アプリ  ─  Streamlit
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from dateutil.relativedelta import relativedelta

import markdown as md_lib

import analyzer
import ai_report
from parser import load_csvs

MANUAL_PATH = Path(__file__).parent / "使用マニュアル.md"


@st.dialog("📖 使用マニュアル", width="large")
def show_manual():
    if MANUAL_PATH.exists():
        st.markdown(MANUAL_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("マニュアルファイルが見つかりません。")

EXPORT_SCRIPT = Path(__file__).parent.parent / "csv-export" / "mykomon_export_http.py"


def get_months_in_range(sy, sm, ey, em):
    months, cur = [], datetime(sy, sm, 1)
    end = datetime(ey, em, 1)
    while cur <= end:
        months.append((cur.year, cur.month))
        cur += relativedelta(months=1)
    return months

# ── ページ設定 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MyKomon 日報分析",
    page_icon="📊",
    layout="wide",
)

# ── 設定読み込み ────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "csv-export" / "config.json"

@st.cache_data(ttl=300)
def load_data(save_dir: str) -> pd.DataFrame:
    return load_csvs(save_dir)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ── サイドバー ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 設定")
    cfg = load_config()

    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("📖 マニュアル", use_container_width=True):
            show_manual()
    with _c2:
        if st.button("🖨️ 印刷", use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0)

    st.divider()

    # --- データ取得セクション ---
    st.markdown("### 📥 データ取得")
    now = datetime.now()
    years = list(range(now.year - 3, now.year + 1))

    col1, col2 = st.columns(2)
    with col1:
        start_year  = st.selectbox("開始年", years, index=len(years) - 1, key="sy")
        start_month = st.selectbox("開始月", range(1, 13),
                                   index=max(0, now.month - 4), key="sm",
                                   format_func=lambda m: f"{m}月")
    with col2:
        end_year    = st.selectbox("終了年", years, index=len(years) - 1, key="ey")
        end_month   = st.selectbox("終了月", range(1, 13),
                                   index=max(0, now.month - 2), key="em",
                                   format_func=lambda m: f"{m}月")

    export_btn = st.button("📥 CSVをエクスポート実行", use_container_width=True,
                           type="primary")

    st.divider()

    # --- 分析設定 ---
    st.markdown("### 📂 分析対象")
    default_dir = cfg.get("save_dir", "")
    save_dir = st.text_input("CSVフォルダ", value=default_dir,
                              help="csv-export の config.json と同じパス")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        api_key = st.text_input("Anthropic API キー", type="password",
                                 help="未設定の場合のみ入力してください")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

    load_btn = st.button("🔄 既存CSVを再読み込み", use_container_width=True)

# ── CSVエクスポート実行 ─────────────────────────────────────────────────────
if export_btn:
    months = get_months_in_range(start_year, start_month, end_year, end_month)
    if not months:
        st.error("終了月が開始月より前になっています。")
    elif not EXPORT_SCRIPT.exists():
        st.error(f"エクスポートスクリプトが見つかりません: {EXPORT_SCRIPT}")
    else:
        st.info(f"MyKomonにログインして {len(months)} ヶ月分をエクスポートします…")
        progress = st.progress(0)
        status   = st.empty()
        errors   = []

        for i, (yr, mo) in enumerate(months):
            status.text(f"取得中: {yr}年{mo}月　({i+1} / {len(months)})")
            result = subprocess.run(
                [sys.executable, str(EXPORT_SCRIPT),
                 "--year", str(yr), "--month", str(mo)],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if result.returncode != 0:
                errors.append(f"{yr}年{mo}月: {result.stderr[-200:]}")
            progress.progress((i + 1) / len(months))

        status.empty()
        if errors:
            st.error("一部エラーが発生しました:\n" + "\n".join(errors))
        else:
            st.success(f"{len(months)} ヶ月分のエクスポートが完了しました。データを読み込みます…")

        # エクスポート後に自動でデータを再読み込み
        if save_dir:
            df_new = load_data(save_dir)
            st.session_state.df = df_new
            st.session_state.summary_text = analyzer.build_summary_text(df_new)
            st.session_state.conversation = []
            st.rerun()

# ── データ読み込み ──────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

if load_btn and save_dir:
    with st.spinner("CSVを読み込み中..."):
        df = load_data(save_dir)
        st.session_state.df = df
        st.session_state.summary_text = analyzer.build_summary_text(df)
        st.session_state.conversation = []
        st.success(f"{len(df):,} 件読み込みました（タグ付き: {df['has_tag'].sum() if 'has_tag' in df.columns else 0} 件）")

df = st.session_state.get("df", pd.DataFrame())

# ── メインUI ────────────────────────────────────────────────────────────────
st.title("📊 MyKomon 日報分析ダッシュボード")

if df.empty:
    st.info("サイドバーでCSVフォルダを指定し「データ読み込み」を押してください。")
    st.stop()

tagged = df[df["has_tag"] == True].copy() if "has_tag" in df.columns else pd.DataFrame()

# ── 読み込みデータの期間表示 ─────────────────────────────────────────────────
from parser import date_column as _date_col
d_col = _date_col(df)
if d_col:
    dates = pd.to_datetime(df[d_col], errors="coerce").dropna()
    if not dates.empty:
        min_d = dates.min().strftime("%Y年%#m月")
        max_d = dates.max().strftime("%Y年%#m月")
        period_str = min_d if min_d == max_d else f"{min_d} 〜 {max_d}"
        st.info(f"📅 読み込み期間：**{period_str}**　｜　全 {len(df):,} 件　｜　タグ付き {len(tagged):,} 件")

if tagged.empty:
    st.caption("タグ付き日報はまだありません。全件ベースの活動量分析を表示しています。")

# ── タブ ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👤 担当者別分析",
    "🏢 顧問先別分析",
    "🔄 業務×工程 ボトルネック",
    "📅 月次トレンド",
    "🤖 AI分析レポート",
])

# ─ TAB 1: 担当者別 ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("担当者別 活動量（全件）")
    sa = analyzer.staff_activity_summary(df)
    if sa.empty:
        st.info("データなし")
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            fig = px.bar(
                sa.head(20),
                x="担当者", y="日報件数",
                color_discrete_sequence=["#4c8bf5"],
                title="担当者別 日報件数（全件）",
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.dataframe(sa, use_container_width=True, hide_index=True)

    if not tagged.empty:
        st.divider()
        st.subheader("担当者別 詰まり分析（タグ付き）")
        sb = analyzer.staff_blocking_summary(df)
        if not sb.empty:
            col_a, col_b = st.columns([3, 2])
            with col_a:
                fig = px.bar(
                    sb.head(15),
                    x="担当者", y="詰まり件数",
                    color_discrete_sequence=["#e05252"],
                    title="担当者別 詰まり件数",
                )
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
            fig2 = px.bar(
                filtered.head(20),
                x="件数", y="阻害要因",
                color="担当者" if selected == "（全員）" else None,
                orientation="h",
                title="阻害要因 内訳",
            )
            fig2.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, use_container_width=True)

# ─ TAB 2: 顧問先別 ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("顧問先別 対応件数（全件）")
    ca = analyzer.client_activity_summary(df)
    if ca.empty:
        st.info("顧問先列が見つかりません（CSVのカラム名を確認）")
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            fig = px.bar(
                ca.head(20),
                x="顧問先", y="対応件数",
                color_discrete_sequence=["#4c8bf5"],
                title="顧問先別 対応件数（全件）",
            )
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
                fig = px.bar(
                    cb.head(20),
                    x="顧問先", y="詰まり件数",
                    color="Red件数",
                    color_continuous_scale=["#f5c518", "#e05252"],
                    title="顧問先別 詰まり件数（色: Red件数）",
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.dataframe(cb.head(20), use_container_width=True, hide_index=True)

# ─ TAB 3: ボトルネック ───────────────────────────────────────────────────────
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
            fig = px.imshow(
                pivot,
                color_continuous_scale="Reds",
                title="業務区分 × 工程 ヒートマップ（詰まり件数）",
                aspect="auto",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(pb, use_container_width=True, hide_index=True)

# ─ TAB 4: 月次トレンド ───────────────────────────────────────────────────────
with tab4:
    st.subheader("月次 日報件数推移（全件）")
    mat = analyzer.monthly_all_trend(df)
    if mat.empty:
        st.info("日付列が見つかりません")
    else:
        fig = px.bar(
            mat, x="月", y="日報件数",
            color_discrete_sequence=["#4c8bf5"],
            title="月別 日報件数（全件）",
        )
        st.plotly_chart(fig, use_container_width=True)
        if "工数合計（分）" in mat.columns:
            mat["工数合計（時間）"] = (mat["工数合計（分）"] / 60).round(1)
            fig2 = px.bar(
                mat, x="月", y="工数合計（時間）",
                color_discrete_sequence=["#36a2eb"],
                title="月別 工数合計（時間）",
            )
            st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(mat, use_container_width=True, hide_index=True)

    if not tagged.empty:
        st.divider()
        st.subheader("月次ステータス推移（タグ付き）")
        mt = analyzer.monthly_trend(df)
        if not mt.empty:
            fig = px.line(
                mt, x="月", y=["完了", "継続", "中断"],
                markers=True, title="月別 ステータス推移",
            )
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.bar(
                mt, x="月", y="詰まり率",
                title="月別 詰まり率（%）",
                color_discrete_sequence=["#e05252"],
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(mt, use_container_width=True, hide_index=True)

# ─ TAB 5: AI分析 ────────────────────────────────────────────────────────────
with tab5:
    st.subheader("🤖 AI分析レポート（Claude Sonnet 4.6）")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("サイドバーに Anthropic API キーを入力してください。")
        st.stop()

    summary_text = st.session_state.get("summary_text", "")
    if not summary_text:
        summary_text = analyzer.build_summary_text(df)
        st.session_state.summary_text = summary_text

    with st.expander("集計データ（AIへの入力）", expanded=False):
        st.text(summary_text)

    if st.button("📝 AIレポートを生成", use_container_width=True):
        with st.spinner("Claude が分析中... (30〜60秒)"):
            try:
                report = ai_report.generate_report(summary_text)
                st.session_state.ai_report = report
                st.session_state.conversation = []
            except Exception as e:
                st.error(f"エラー: {e}")

    if "ai_report" in st.session_state:
        st.markdown("### レポート")
        full_report_md = ai_report.ANALYSIS_PREMISES_MD + st.session_state.ai_report
        st.markdown(full_report_md)

        report_body_html = md_lib.markdown(
            full_report_md, extensions=["tables", "nl2br"]
        )
        print_page_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI分析レポート</title>
<style>
  body {{ font-family: 'Yu Gothic', 'Meiryo', 'Hiragino Sans', sans-serif;
         max-width: 800px; margin: 2em auto; line-height: 1.8; font-size: 11pt; color: #222; }}
  h1, h2, h3 {{ border-bottom: 1px solid #ccc; padding-bottom: 0.3em; margin-top: 1.5em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
  th {{ background: #f5f5f5; }}
  @media print {{ @page {{ margin: 2cm; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
<h1>AI分析レポート</h1>
{report_body_html}
</body>
</html>"""
        components.html(
            f"""
            <button onclick="doPrint()" style="
                padding:8px 20px; font-size:14px; cursor:pointer;
                background:#ff4b4b; color:white; border:none; border-radius:6px;
                font-family:sans-serif; margin-top:4px;">
              🖨️ このレポートを印刷
            </button>
            <script>
            function doPrint() {{
                var w = window.open('', '_blank');
                w.document.write({json.dumps(print_page_html)});
                w.document.close();
                w.focus();
                w.print();
            }}
            </script>
            """,
            height=60,
        )

        st.divider()
        st.markdown("### フォローアップ質問")
        question = st.text_input("質問を入力してください", key="followup_input")
        if st.button("送信", key="followup_btn") and question:
            with st.spinner("回答中..."):
                try:
                    answer, conv = ai_report.ask_followup(
                        summary_text,
                        st.session_state.get("conversation", []),
                        question,
                    )
                    st.session_state.conversation = conv
                except Exception as e:
                    st.error(f"エラー: {e}")

        conv = st.session_state.get("conversation", [])
        if len(conv) > 2:
            st.markdown("#### 会話履歴")
            for msg in conv[1:]:
                role = "🧑 所長" if msg["role"] == "user" else "🤖 Claude"
                with st.chat_message(msg["role"]):
                    st.markdown(f"**{role}**\n\n{msg['content']}")
