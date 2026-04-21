"""
pandas による集計ロジック
"""
import pandas as pd
from parser import staff_column, client_column, date_column, text_column


def _tagged(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["has_tag"] == True].copy()


# ---- [1] 担当者別詰まり分析 ----------------------------------------

def staff_blocking_summary(df: pd.DataFrame) -> pd.DataFrame:
    """担当者 × ステータス（継続/中断）の件数と阻害要因ランキング。"""
    t = _tagged(df)
    s_col = staff_column(t)
    if s_col is None or t.empty:
        return pd.DataFrame()

    blocked = t[t["ステータス"].isin(["継続", "中断"])].copy()
    if blocked.empty:
        return pd.DataFrame()

    summary = (
        blocked.groupby(s_col)
        .agg(
            詰まり件数=("ステータス", "count"),
            継続=(  "ステータス", lambda x: (x == "継続").sum()),
            中断=(  "ステータス", lambda x: (x == "中断").sum()),
        )
        .reset_index()
        .rename(columns={s_col: "担当者"})
        .sort_values("詰まり件数", ascending=False)
    )
    return summary


def staff_blocking_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """担当者別 阻害要因 内訳（explode）。"""
    t = _tagged(df)
    s_col = staff_column(t)
    if s_col is None or t.empty:
        return pd.DataFrame()

    blocked = t[t["ステータス"].isin(["継続", "中断"])].copy()
    blocked = blocked.explode("阻害要因_list")
    blocked = blocked[blocked["阻害要因_list"].notna() & (blocked["阻害要因_list"] != "")]

    if blocked.empty:
        return pd.DataFrame()

    result = (
        blocked.groupby([s_col, "阻害要因_list"])
        .size()
        .reset_index(name="件数")
        .rename(columns={s_col: "担当者", "阻害要因_list": "阻害要因"})
        .sort_values(["担当者", "件数"], ascending=[True, False])
    )
    return result


# ---- [2] 顧問先別問題特定 ------------------------------------------

def client_blocking_summary(df: pd.DataFrame) -> pd.DataFrame:
    t = _tagged(df)
    c_col = client_column(t)
    if c_col is None or t.empty:
        return pd.DataFrame()

    blocked = t[t["ステータス"].isin(["継続", "中断"])].copy()
    if blocked.empty:
        return pd.DataFrame()

    summary = (
        blocked.groupby(c_col)
        .agg(
            詰まり件数=("ステータス", "count"),
            Red件数=("緊急度", lambda x: (x == "Red").sum()),
            Yellow件数=("緊急度", lambda x: (x == "Yellow").sum()),
        )
        .reset_index()
        .rename(columns={c_col: "顧問先"})
        .sort_values("詰まり件数", ascending=False)
    )
    return summary


# ---- [3] 業務区分 × 工程 ボトルネック ----------------------------

def process_bottleneck(df: pd.DataFrame) -> pd.DataFrame:
    t = _tagged(df)
    if t.empty:
        return pd.DataFrame()

    blocked = t[t["ステータス"].isin(["継続", "中断"])].copy()
    blocked = blocked.dropna(subset=["業務区分", "工程"])
    if blocked.empty:
        return pd.DataFrame()

    pivot = (
        blocked.groupby(["業務区分", "工程"])
        .size()
        .reset_index(name="件数")
        .sort_values("件数", ascending=False)
    )
    return pivot


# ---- [4] 月次トレンド ---------------------------------------------

def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    t = _tagged(df)
    d_col = date_column(t)
    if d_col is None or t.empty:
        return pd.DataFrame()

    t = t.copy()
    t[d_col] = pd.to_datetime(t[d_col], errors="coerce")
    t = t.dropna(subset=[d_col])
    t["月"] = t[d_col].dt.to_period("M").astype(str)

    trend = (
        t.groupby("月")
        .agg(
            総件数=("has_tag", "count"),
            完了=(  "ステータス", lambda x: (x == "完了").sum()),
            継続=(  "ステータス", lambda x: (x == "継続").sum()),
            中断=(  "ステータス", lambda x: (x == "中断").sum()),
        )
        .reset_index()
        .sort_values("月")
    )
    trend["詰まり率"] = ((trend["継続"] + trend["中断"]) / trend["総件数"] * 100).round(1)
    return trend


# ---- 全件ベース集計（タグ不要） ------------------------------------

def staff_activity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """全件ベース: 担当者別 日報件数・工数合計"""
    s_col = staff_column(df)
    if s_col is None or df.empty:
        return pd.DataFrame()
    grp = df.groupby(s_col)
    result = grp.size().reset_index(name="日報件数")
    result = result.rename(columns={s_col: "担当者"})
    if "工数（分）" in df.columns:
        wsums = grp["工数（分）"].sum().reset_index()
        wsums.columns = ["担当者", "工数合計（分）"]
        result = result.merge(wsums, on="担当者")
    return result.sort_values("日報件数", ascending=False)


def client_activity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """全件ベース: 顧問先別 対応件数・工数合計"""
    c_col = client_column(df)
    if c_col is None or df.empty:
        return pd.DataFrame()
    valid = df[~df[c_col].astype(str).str.contains(r"\[-1\]|未選択", na=True)]
    if valid.empty:
        return pd.DataFrame()
    grp = valid.groupby(c_col)
    result = grp.size().reset_index(name="対応件数")
    result = result.rename(columns={c_col: "顧問先"})
    if "工数（分）" in valid.columns:
        wsums = grp["工数（分）"].sum().reset_index()
        wsums.columns = ["顧問先", "工数合計（分）"]
        result = result.merge(wsums, on="顧問先")
    return result.sort_values("対応件数", ascending=False)


def monthly_all_trend(df: pd.DataFrame) -> pd.DataFrame:
    """全件ベース: 月次 日報件数・工数合計"""
    d_col = date_column(df)
    if d_col is None or df.empty:
        return pd.DataFrame()
    tmp = df.copy()
    tmp[d_col] = pd.to_datetime(tmp[d_col], errors="coerce")
    tmp = tmp.dropna(subset=[d_col])
    tmp["月"] = tmp[d_col].dt.to_period("M").astype(str)
    grp = tmp.groupby("月")
    result = grp.size().reset_index(name="日報件数")
    if "工数（分）" in tmp.columns:
        wsums = grp["工数（分）"].sum().reset_index()
        wsums.columns = ["月", "工数合計（分）"]
        result = result.merge(wsums, on="月")
    return result.sort_values("月")


# ---- 全体サマリー（AI向け） ----------------------------------------

def build_summary_text(df: pd.DataFrame) -> str:
    """AI分析に渡す集計サマリーテキスト（全件ベース + タグ付き詳細）。"""
    lines = []

    # --- 全件統計 ---
    d_col = date_column(df)
    lines.append(f"全日報件数: {len(df)}")
    if d_col and not df.empty:
        dates = pd.to_datetime(df[d_col], errors="coerce").dropna()
        if not dates.empty:
            lines.append(f"期間: {dates.min().date()} 〜 {dates.max().date()}")

    sa = staff_activity_summary(df)
    if not sa.empty:
        lines.append("\n【担当者別 日報件数（全件・上位10名）】")
        lines.append(sa.head(10).to_string(index=False))

    ca = client_activity_summary(df)
    if not ca.empty:
        lines.append("\n【顧問先別 対応件数（全件・上位10）】")
        lines.append(ca.head(10).to_string(index=False))

    mat = monthly_all_trend(df)
    if not mat.empty:
        lines.append("\n【月次 日報件数推移（全件）】")
        lines.append(mat.to_string(index=False))

    # --- メモテキストサンプル ---
    t_col = text_column(df)
    if t_col:
        memo_df = df[df[t_col].notna() & (df[t_col].astype(str).str.strip() != "")]
        if not memo_df.empty:
            sample = memo_df[t_col].sample(min(len(memo_df), 40), random_state=42)
            lines.append(f"\n【日報テキストサンプル（{len(sample)}件抜粋）】")
            for text in sample:
                lines.append(f"- {str(text)[:150]}")

    # --- タグ付き詳細分析（あれば） ---
    t = _tagged(df)
    if not t.empty:
        lines.append(f"\n【タグ付き日報 詳細分析（{len(t)}件）】")
        sb = staff_blocking_summary(df)
        if not sb.empty:
            lines.append("担当者別詰まり件数（上位5名）:")
            lines.append(sb.head(5).to_string(index=False))
        rb = staff_blocking_reasons(df)
        if not rb.empty:
            top = rb.groupby("阻害要因")["件数"].sum().sort_values(ascending=False).head(5)
            lines.append("阻害要因ランキング（上位5）:")
            lines.append(top.to_string())
        pb = process_bottleneck(df)
        if not pb.empty:
            lines.append("業務×工程ボトルネック（上位5）:")
            lines.append(pb.head(5).to_string(index=False))
        mt = monthly_trend(df)
        if not mt.empty:
            lines.append("月次ステータストレンド:")
            lines.append(mt.to_string(index=False))

    return "\n".join(lines)
