"""
人事経営相談AIシステム
計画と現実のずれを入力すると、根本原因と改善策を提案する
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st

from knowledge import build_system_prompt

# ── 資料ファイルパス ───────────────────────────────────────────
_BASE = Path(__file__).parent.parent.parent  # cluadecode_shared 直下
DOC_MANUAL = _BASE / "世界の人事制度" / "人事制度改革提言_詳細解説書.docx"
DOC_PPTX   = _BASE / "世界の人事制度" / "人事制度改革提言_役員向けプレゼン.pptx"
DOC_MANUAL_MD = Path(__file__).parent / "人事経営相談アプリ_使用マニュアル.md"


def _open_file(path: Path):
    """既定のアプリでファイルを開く（Windows）"""
    os.startfile(str(path))


def _print_file(path: Path):
    """既定のアプリで印刷ダイアログを起動（Windows）"""
    subprocess.Popen(
        ["powershell", "-Command",
         f'Start-Process -FilePath "{path}" -Verb Print'],
        shell=True,
    )


def _md_to_html(path: Path, auto_print: bool = False) -> str:
    """マークダウンファイルをHTMLに変換する（外部ライブラリ不要）"""
    import re
    import html as _h

    def inline(text: str) -> str:
        text = _h.escape(text)
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
        return text

    lines = path.read_text(encoding="utf-8").split("\n")
    body: list = []
    in_code = in_ul = in_table = False

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_ul:    body.append("</ul>");    in_ul = False
            if in_table: body.append("</table>"); in_table = False
            body.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            body.append(_h.escape(line))
            continue
        if in_table and not line.startswith("|"):
            body.append("</table>"); in_table = False
        if in_ul and not line.startswith("- "):
            body.append("</ul>"); in_ul = False
        if line.startswith("### "):
            body.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("> "):
            body.append(f"<blockquote>{inline(line[2:])}</blockquote>")
        elif line.startswith("- "):
            if not in_ul: body.append("<ul>"); in_ul = True
            body.append(f"<li>{inline(line[2:])}</li>")
        elif line.startswith("|"):
            if not in_table:
                body.append("<table>"); in_table = True
            if re.fullmatch(r"[|\s\-:]+", line):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            body.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        elif re.fullmatch(r"-{3,}", line):
            body.append("<hr>")
        elif not line.strip():
            body.append("")
        else:
            body.append(f"<p>{inline(line)}</p>")

    if in_ul:    body.append("</ul>")
    if in_table: body.append("</table>")

    css = (
        "body{font-family:'Meiryo','Yu Gothic',sans-serif;max-width:900px;margin:0 auto;padding:24px;font-size:10.5pt;line-height:1.7;color:#222}"
        "h1{font-size:1.5em;border-bottom:2px solid #1B3A5C;padding-bottom:.3em;color:#1B3A5C}"
        "h2{font-size:1.25em;border-bottom:1px solid #4472C4;padding-bottom:.2em;color:#1B3A5C;margin-top:1.5em}"
        "h3{font-size:1.05em;color:#4472C4;margin-top:1.2em}"
        "table{border-collapse:collapse;width:100%;margin:.8em 0}"
        "td,th{border:1px solid #aaa;padding:6px 10px}"
        "tr:nth-child(even){background:#f5f7fa}"
        "code{background:#f0f0f0;padding:2px 4px;border-radius:3px;font-family:monospace}"
        "pre{background:#f0f0f0;padding:12px;border-radius:4px;overflow-x:auto}"
        "pre code{background:none;padding:0}"
        "blockquote{border-left:4px solid #4472C4;margin:0;padding:.5em 1em;background:#f0f5ff}"
        "hr{border:none;border-top:1px solid #ccc;margin:1.5em 0}"
        "@media print{body{padding:0}}"
    )
    print_js = "<script>window.onload=function(){window.print();}</script>" if auto_print else ""
    return (
        "<!DOCTYPE html>\n<html lang=\"ja\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<title>人事経営相談アプリ 使用マニュアル</title>\n"
        f"<style>{css}</style>\n"
        "</head>\n<body>\n"
        + "\n".join(body)
        + f"\n{print_js}\n</body>\n</html>"
    )


def _open_manual_md():
    import tempfile
    import webbrowser
    tmp = Path(tempfile.gettempdir()) / "consult_manual.html"
    tmp.write_text(_md_to_html(DOC_MANUAL_MD, auto_print=False), encoding="utf-8")
    webbrowser.open(tmp.as_uri())


def _print_manual_md():
    import tempfile
    import webbrowser
    tmp = Path(tempfile.gettempdir()) / "consult_manual_print.html"
    tmp.write_text(_md_to_html(DOC_MANUAL_MD, auto_print=True), encoding="utf-8")
    webbrowser.open(tmp.as_uri())


def _format_gap_prefill(gap: dict) -> str:
    """日報分析データを相談入力欄テキストに変換する（所長の補足欄付き）"""
    lines = [
        f"【日報分析データ {gap.get('period', '不明')}】（{gap.get('generated_at', '')} 取得）",
        (
            f"全日報件数：{gap.get('total_records', 0):,}件　"
            f"タグ付き：{gap.get('tagged_records', 0):,}件"
            f"（{gap.get('tag_rate_pct', 0):.1f}%）　"
            f"詰まり：{gap.get('stuck_count', 0)}件"
        ),
    ]
    low_staff = gap.get("low_tag_rate_staff", [])
    if low_staff:
        lines.append("\n■ タグ付き率が低い担当者（上位5名）")
        for name, rate in low_staff:
            lines.append(f"・{name}：{rate:.1f}%")
    top_blockers = gap.get("top_blockers", [])
    if top_blockers:
        lines.append("\n■ 主な阻害要因")
        for i, (reason, count) in enumerate(top_blockers, 1):
            lines.append(f"{i}位：{reason}（{count}件）")
    red_clients = gap.get("red_clients", [])
    if red_clients:
        lines.append("\n■ 緊急対応が必要な顧問先")
        for c in red_clients:
            lines.append(f"・{c}")
    monthly = gap.get("monthly_stuck_rates", {})
    if monthly:
        lines.append("\n■ 月次詰まり率（直近）")
        for month, rate in list(monthly.items())[-3:]:
            lines.append(f"・{month}：{rate:.1f}%")
    lines += [
        "\n---",
        "【所長の補足・感じているずれ（任意）】",
        "（ここに追記してください）",
    ]
    return "\n".join(lines)


# ── 定数 ───────────────────────────────────────────────────���──
HISTORY_PATH = Path(__file__).parent / "consult_history.json"
LATEST_GAP_PATH = Path(__file__).parent / "latest_gap.json"
MAX_HISTORY_DISPLAY = 20

GAP_CATEGORIES = [
    "（自動判断）",
    "ボトムアップ・自主経営",
    "業務の見える化・日報",
    "評価制度・人事考課",
    "給与・報酬体系",
    "職階・役割分担",
    "有資格者の処遇",
    "職員の教育・育成",
    "採用・離職",
    "顧客対応・サービス品質",
    "G8・海外事例の研究",
    "経営者の人事一般相談",
    "その他",
]

# ── 履歴の読み書き ─────────────────────────────────────────────
def load_history() -> list:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_history(history: list):
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Claude API 呼び出し ────────────────────────────────────────
def call_claude(conversation: list) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=build_system_prompt(),
        messages=conversation,
    )
    return response.content[0].text


# ── ページ設定 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="人事経営相談AI",
    page_icon="💼",
    layout="wide",
)

st.markdown("""
<style>
.consult-header {
    background: linear-gradient(135deg, #1B3A5C, #4472C4);
    color: white;
    padding: 1.2rem 1.5rem;
    border-radius: 8px;
    margin-bottom: 1.2rem;
}
.consult-header h1 { color: white; margin: 0; font-size: 1.5rem; }
.consult-header p  { color: #D6E4F7; margin: 0.3rem 0 0; font-size: 0.9rem; }
.phase-badge {
    display: inline-block;
    background: #27AE60;
    color: white;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}
.history-item {
    border-left: 3px solid #4472C4;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem;
    background: #F8FAFC;
    border-radius: 0 4px 4px 0;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ── ヘッダー ───────────────────────────────────────────────────
st.markdown("""
<div class="consult-header">
  <h1>💼 人事経営相談AI ── 計画と現実のずれを解決する</h1>
  <p>人事制度改革の実施中に生じる「うまくいかない」を入力すると、根本原因と改善策を提案します。<br>
  日報データに基づく自社分析だけでなく、<strong>G8諸国・世界標準の人事事例</strong>を参照した幅広い人事経営相談にも対応します。</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<span class="phase-badge">現在：Phase 1 ── 業務可視化の定着期</span>',
            unsafe_allow_html=True)

# ── サイドバー ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 設定")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        api_key = st.text_input(
            "Anthropic API キー",
            type="password",
            help="未設定の場合のみ入力してください",
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
    else:
        st.success("API キー設定済み")

    st.divider()
    st.markdown("### 📑 人事制度改革資料")

    # 詳細解説書
    st.markdown("**詳細解説書**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 開く", key="open_manual", use_container_width=True,
                     disabled=not DOC_MANUAL.exists()):
            _open_file(DOC_MANUAL)
            st.toast("Word で開きました")
    with c2:
        if st.button("🖨️ 印刷", key="print_manual", use_container_width=True,
                     disabled=not DOC_MANUAL.exists()):
            _print_file(DOC_MANUAL)
            st.toast("印刷ダイアログを起動しました")
    if not DOC_MANUAL.exists():
        st.caption(f"⚠ ファイルが見つかりません:\n{DOC_MANUAL}")

    # 役員向けプレゼン
    st.markdown("**役員向けプレゼン**")
    c3, c4 = st.columns(2)
    with c3:
        if st.button("📊 開く", key="open_pptx", use_container_width=True,
                     disabled=not DOC_PPTX.exists()):
            _open_file(DOC_PPTX)
            st.toast("PowerPoint で開きました")
    with c4:
        if st.button("🖨️ 印刷", key="print_pptx", use_container_width=True,
                     disabled=not DOC_PPTX.exists()):
            _print_file(DOC_PPTX)
            st.toast("印刷ダイアログを起動しました")
    if not DOC_PPTX.exists():
        st.caption(f"⚠ ファイルが見つかりません:\n{DOC_PPTX}")

    st.divider()
    st.markdown("### 📖 使用マニュアル")
    c_md1, c_md2 = st.columns(2)
    with c_md1:
        if st.button("📄 表示", key="view_manual_md", use_container_width=True,
                     disabled=not DOC_MANUAL_MD.exists()):
            _open_manual_md()
            st.toast("マニュアルをブラウザで開きました")
    with c_md2:
        if st.button("🖨️ 印刷", key="print_manual_md", use_container_width=True,
                     disabled=not DOC_MANUAL_MD.exists()):
            _print_manual_md()
            st.toast("印刷ダイアログを起動しました")
    if not DOC_MANUAL_MD.exists():
        st.caption(f"⚠ ファイルが見つかりません:\n{DOC_MANUAL_MD}")

    st.divider()
    st.markdown("### 📊 日報分析データを使う")
    if LATEST_GAP_PATH.exists():
        try:
            _gap_data = json.loads(LATEST_GAP_PATH.read_text(encoding="utf-8"))
            st.caption(
                f"📅 {_gap_data.get('period', '期間不明')}　"
                f"{_gap_data.get('generated_at', '')}"
            )
            _cg1, _cg2 = st.columns(2)
            with _cg1:
                st.metric("全件数", f"{_gap_data.get('total_records', 0):,}")
            with _cg2:
                st.metric("タグ付き率", f"{_gap_data.get('tag_rate_pct', 0):.1f}%")
            if st.button("📥 この結果を相談に使う", use_container_width=True,
                         type="primary", key="use_gap_data"):
                prefill_text = _format_gap_prefill(_gap_data)
                st.session_state["prefill"] = prefill_text
                st.session_state["question_input"] = prefill_text
                st.rerun()
        except Exception:
            st.caption("データの読み込みに失敗しました")
    else:
        st.caption(
            "日報分析アプリの「AI分析レポート」タブで"
            "「📨 人事経営相談に送る」を押すとここにデータが表示されます"
        )

    st.divider()
    st.markdown("### 📂 相談カテゴリ")
    selected_cat = st.selectbox("テーマ（任意）", GAP_CATEGORIES)

    st.divider()
    st.markdown("### 📋 現在の計画概要")
    st.markdown("""
**Phase 1（進行中）**
- 音声日報・Edge拡張を全員展開
- タグ付き率80%以上が目標
- 評価・給与への連動はまだ行わない

**Phase 2（2026年10月〜）**
- 職階設計（Tier1〜4）確定
- OKR導入（給与連動なし）
- 評価基準の試行

**Phase 3（2027年4月〜）**
- ジョブ型基本給への移行
- 集合ボーナス導入
""")

    st.divider()
    if st.button("🗑️ 今回の会話をリセット", use_container_width=True):
        st.session_state.conversation = []
        st.session_state.pop("last_question", None)
        st.rerun()

# ── セッション初期化 ───────────────────────────────────────────
if "conversation" not in st.session_state:
    st.session_state.conversation = []

# ── メインエリア ───────────────────────────────────────────────
col_main, col_history = st.columns([2, 1])

with col_main:
    st.markdown("### 💬 相談する")

    # 相談例のクイック入力
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
            "給与テーブルを職員に公開することのメリット・デメリットは",
            "心理的安全性を高めるために所長として何をすべきか",
            "スキルベース採用とはどういう考え方か。当事務所に応用できるか",
        ]
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            with cols[i % 2]:
                if st.button(ex, key=f"ex_{i}", use_container_width=True):
                    st.session_state["prefill"] = ex

    # 入力欄
    prefill = st.session_state.pop("prefill", "")
    question = st.text_area(
        "計画と現実のずれ・困っていること",
        value=prefill,
        height=120,
        placeholder="例：ボトムアップ会議を始めたが誰も発言しない。何が原因で、どう対処すればよいか。",
        key="question_input",
    )

    # カテゴリをプロンプトに付加
    cat_note = ""
    if selected_cat != "（自動判断）":
        cat_note = f"\n\n【相談カテゴリ】{selected_cat}"

    send_btn = st.button("📨 相談する", type="primary", use_container_width=True,
                         disabled=not question.strip())

    # ── 送信処理 ────────────────────────────────��─────────────
    if send_btn and question.strip():
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("サイドバーに Anthropic API キーを入力してください。")
        else:
            user_message = question.strip() + cat_note
            st.session_state.conversation.append(
                {"role": "user", "content": user_message}
            )

            with st.spinner("分析中... (10〜30秒)"):
                try:
                    answer = call_claude(st.session_state.conversation)
                    st.session_state.conversation.append(
                        {"role": "assistant", "content": answer}
                    )

                    # 履歴に保存
                    history = load_history()
                    history.append({
                        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "category": selected_cat,
                        "question": question.strip(),
                        "answer": answer,
                    })
                    save_history(history)

                except Exception as e:
                    st.error(f"エラー: {e}")
                    st.session_state.conversation.pop()

    # ── 会話表示 ──────────────────────────────────────────────
    conversation = st.session_state.get("conversation", [])
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

        # フォローアップ
        st.divider()
        followup = st.text_input(
            "フォローアップ質問（続けて相談）",
            placeholder="例：具体的にどのような言葉で職員に説明すればよいですか？",
            key="followup",
        )
        if st.button("続けて相談", disabled=not followup.strip()):
            if not os.environ.get("ANTHROPIC_API_KEY"):
                st.error("APIキーを入力してください。")
            else:
                st.session_state.conversation.append(
                    {"role": "user", "content": followup.strip()}
                )
                with st.spinner("回答中..."):
                    try:
                        answer = call_claude(st.session_state.conversation)
                        st.session_state.conversation.append(
                            {"role": "assistant", "content": answer}
                        )
                        history = load_history()
                        history.append({
                            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "category": selected_cat,
                            "question": f"[フォローアップ] {followup.strip()}",
                            "answer": answer,
                        })
                        save_history(history)
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
                        st.session_state.conversation.pop()

# ── 相談履歴パネル ─────────────────────────────────────────────
with col_history:
    st.markdown("### 🗂️ 過去の相談履歴")
    history = load_history()

    if not history:
        st.info("まだ相談履歴がありません。")
    else:
        # 新しい順に表示
        for item in reversed(history[-MAX_HISTORY_DISPLAY:]):
            with st.expander(
                f"🕐 {item['datetime']}｜{item['question'][:25]}…"
                if len(item["question"]) > 25
                else f"🕐 {item['datetime']}｜{item['question']}"
            ):
                if item.get("category") and item["category"] != "（自動判断）":
                    st.markdown(f"**カテゴリ：** {item['category']}")
                st.markdown(f"**相談：** {item['question']}")
                st.divider()
                st.markdown(item["answer"])

        st.divider()
        if st.button("📥 履歴をJSONで保存", use_container_width=True):
            st.download_button(
                label="ダウンロード",
                data=json.dumps(history, ensure_ascii=False, indent=2),
                file_name=f"consult_history_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

        if st.button("🗑️ 履歴を全削除", use_container_width=True):
            save_history([])
            st.success("履歴を削除しました。")
            st.rerun()
