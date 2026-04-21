"""
MyKomon CSV から構造化タグを抽出するパーサー
"""
import re
import pandas as pd
from pathlib import Path


TAG_PATTERNS = {
    "業務区分":  r"【業務区分】([^\n\r【]+)",
    "ステータス": r"【ステータス】([^\n\r【]+)",
    "工程":      r"【工程】([^\n\r【]+)",
    "緊急度":    r"【緊急度】([^\n\r【]+)",
    "工数":      r"【工数】([^\n\r【]+)",
    "阻害要因":  r"【阻害要因】([^\n\r【]+)",
}

BLOCKING_SPLIT = re.compile(r"[・、,，]")


def _extract_tags(text: str) -> dict:
    if not isinstance(text, str):
        return {}
    result = {}
    for key, pattern in TAG_PATTERNS.items():
        m = re.search(pattern, text)
        if m:
            result[key] = m.group(1).strip()
    return result


def load_csvs(save_dir: str) -> pd.DataFrame:
    """save_dir 内の全CSVを結合して返す。タグ列を追加済み。"""
    p = Path(save_dir)
    files = sorted(p.glob("*.csv"))
    if not files:
        return pd.DataFrame()

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="cp932", on_bad_lines="skip")
            frames.append(df)
        except Exception:
            try:
                df = pd.read_csv(f, encoding="utf-8-sig", on_bad_lines="skip")
                frames.append(df)
            except Exception:
                pass

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = _add_tag_columns(combined)
    return combined


def _find_text_column(df: pd.DataFrame) -> str | None:
    """日報本文が入っているカラムを推定する。"""
    candidates = ["workText", "業務内容", "日報", "内容", "メモ", "テキスト", "備考"]
    for c in candidates:
        if c in df.columns:
            return c
    # フォールバック: 文字列カラムで最長のもの
    str_cols = df.select_dtypes(include="object").columns
    if len(str_cols) == 0:
        return None
    return max(str_cols, key=lambda c: df[c].dropna().str.len().mean() if df[c].dropna().shape[0] > 0 else 0)


def _add_tag_columns(df: pd.DataFrame) -> pd.DataFrame:
    text_col = _find_text_column(df)
    if text_col is None:
        return df

    extracted = df[text_col].apply(_extract_tags).apply(pd.Series)
    for col in TAG_PATTERNS:
        if col not in extracted.columns:
            extracted[col] = None

    df = pd.concat([df, extracted], axis=1)

    # 阻害要因を複数行に展開（explode用リスト列）
    df["阻害要因_list"] = df["阻害要因"].apply(
        lambda v: [x.strip() for x in BLOCKING_SPLIT.split(v) if x.strip()] if isinstance(v, str) else []
    )
    df["has_tag"] = df["業務区分"].notna()
    return df


def text_column(df: pd.DataFrame) -> str | None:
    return _find_text_column(df)


def staff_column(df: pd.DataFrame) -> str | None:
    """担当者列を推定する。"""
    candidates = ["担当者", "職員氏名", "職員名", "社員名", "氏名", "userName", "staff"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def client_column(df: pd.DataFrame) -> str | None:
    """顧問先列を推定する。"""
    candidates = ["顧問先", "顧客名", "得意先", "client", "customerName"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def date_column(df: pd.DataFrame) -> str | None:
    candidates = ["日付", "date", "workDate", "作業日", "入力日", "開始日時"]
    for c in candidates:
        if c in df.columns:
            return c
    return None
