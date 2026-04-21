"""
Claude API を使った日報分析レポート生成
プロンプトキャッシュ + adaptive thinking を使用
"""
import anthropic

SYSTEM_PROMPT = """あなたは税理士事務所の所長を補佐する業務分析AIです。
MyKomonから抽出した日報データの集計結果を受け取り、
経営者視点で重要な洞察と具体的なアクションを提示します。

分析の観点：
- 業務の詰まり（継続・中断）の原因と対策
- 担当者ごとの負荷・スキルギャップ
- 顧問先ごとのリスク（資料未回収・繰り返す阻害要因）
- 組織全体の処理能力と月次変化

出力形式：
1. 経営者への要約（3〜5行）
2. 要注意事項（箇条書き・優先順位付き）
3. 推奨アクション（担当者名・顧問先名を含む具体的な指示）

日本語で回答してください。"""

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def generate_report(summary_text: str, extra_question: str = "") -> str:
    """
    集計サマリーを受け取りAIレポートを返す。
    prompt caching でシステムプロンプトをキャッシュ。
    """
    client = _get_client()

    user_content = f"以下は日報データの集計結果です。分析してください。\n\n{summary_text}"
    if extra_question.strip():
        user_content += f"\n\n追加質問: {extra_question.strip()}"

    full_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            full_text += text

    return full_text


def ask_followup(summary_text: str, conversation: list[dict], question: str) -> tuple[str, list[dict]]:
    """
    フォローアップ質問に答える（会話履歴付き）。
    conversation は [{"role": "user"|"assistant", "content": str}, ...] のリスト。
    """
    client = _get_client()

    if not conversation:
        first_user = f"以下は日報データの集計結果です。\n\n{summary_text}"
        conversation = [{"role": "user", "content": first_user}]

    conversation.append({"role": "user", "content": question})

    full_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=conversation,
    ) as stream:
        for text in stream.text_stream:
            full_text += text

    conversation.append({"role": "assistant", "content": full_text})
    return full_text, conversation
