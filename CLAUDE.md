# CLAUDE.md
# MyKomon 日報入力補助 Edge拡張機能 開発プロジェクト

## プロジェクト概要

税理士事務所で使用している業務管理システム「MyKomon（TKC）」の日報入力を補助する
Microsoft Edge拡張機能を開発する。

MyKomonにはAPIが存在しないため、拡張機能がブラウザ上でMyKomonのDOM要素を直接操作し、
カード型UIで選択した構造化データを日報の平文入力欄に自動挿入する。

---

## 解決したい課題

- MyKomonの日報は平文（自由記述）のみで、AI分析に必要な構造化データが蓄積されない
- 職員が「何をどう書けばよいか」迷うことで、入力品質にばらつきが生じている
- 税理士法上の業務処理簿として必要な項目（業務区分・担当者・処理の要旨）の記録が不十分

---

## 実現したいこと

MyKomonの日報入力画面でカード型UIをポップアップ表示し、
職員が選択した項目を構造化タグとして平文入力欄に自動挿入する。

### 挿入されるテキストのイメージ

```
（職員が自由記述で入力した内容）
○○株式会社の月次監査を実施。試算表は概ね完了したが棚卸表が未着のため確定できず。

---
【業務区分】監査
【ステータス】中断
【阻害要因】資料待ち
#監査 #中断 #資料待ち
```

---

## カードUIの入力項目（確定版）

### [1] 税理士法上の業務区分（選択式・単一選択）
- 申告
- 相談
- 監査
- 記帳代行
- その他

### [2] 業務ステータス（選択式・単一選択）
- 完了
- 継続
- 中断

### [3] 阻害要因（選択式・複数選択可）
- **表示条件：[2]で「継続」または「中断」を選択した場合のみ表示**
- 資料待ち
- 確認中
- 知識不足
- 客先都合
- その他

---

## 技術仕様

### 対象ブラウザ
- **Microsoft Edge（優先）**
- Google Chrome（後日対応・同一コードで動作可能）
- 規格：Manifest V3

### 対象システム
- MyKomon（TKC製 Webシステム）
- MyKomonの日報入力画面上で動作する

### 主な処理の流れ

```
1. MyKomonの日報入力画面を検知（URLパターンまたはDOM要素で判定）
2. ブラウザ右上の拡張機能アイコンをクリック、またはページ上のボタンをクリック
3. カード型UIのポップアップを表示
4. 職員が[1][2][3]の項目を選択
   - [2]で「完了」を選択した場合、[3]は非表示にする
5. 「平文に反映する」ボタンをクリック
6. MyKomonの日報入力欄（テキストエリア）の末尾に構造化タグを自動挿入
7. 職員はMyKomonの「登録」ボタンを押して保存
```

### ファイル構成（推奨）

```
/edge-extension
  ├── manifest.json        # 拡張機能の設定ファイル（Manifest V3）
  ├── popup.html           # カード型UIのHTML
  ├── popup.js             # カードUIのロジック・DOM操作
  ├── content.js           # MyKomonページへの挿入スクリプト
  ├── background.js        # バックグラウンド処理（必要に応じて）
  └── icons/               # 拡張機能アイコン
       ├── icon16.png
       ├── icon48.png
       └── icon128.png
```

### manifest.jsonの基本設定

```json
{
  "manifest_version": 3,
  "name": "MyKomon 日報入力補助",
  "version": "1.0.0",
  "description": "MyKomonの日報入力をカード型UIで補助し、構造化タグを自動挿入します",
  "permissions": [
    "activeTab",
    "scripting"
  ],
  "host_permissions": [
    "https://*.mykomon.jp/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "content_scripts": [
    {
      "matches": ["https://*.mykomon.jp/*"],
      "js": ["content.js"]
    }
  ]
}
```

---

## 生成されるタグの仕様

### タグのフォーマット（固定）

```
---
【業務区分】{選択値}
【ステータス】{選択値}
【阻害要因】{選択値1}・{選択値2}  ※複数選択時は「・」で連結
#業務区分_{選択値} #ステータス_{選択値} #阻害要因_{選択値}
```

### タグ命名規則（変更禁止）

過去データとの一貫性を保つため、以下のタグ名称は運用開始後に変更しないこと。

| 項目 | タグ例 |
|------|--------|
| 業務区分 | #業務区分_申告 / #業務区分_監査 / #業務区分_相談 / #業務区分_記帳代行 |
| ステータス | #ステータス_完了 / #ステータス_継続 / #ステータス_中断 |
| 阻害要因 | #阻害要因_資料待ち / #阻害要因_確認中 / #阻害要因_知識不足 / #阻害要因_客先都合 |

---

## AI分析への活用方針

MyKomonからCSVエクスポートした日報データに上記タグが含まれるため、
AIによる以下の分析が可能になる。

- 担当者別・業務区分別の業務詰まり件数の集計
- 阻害要因の傾向分析（資料待ちが多い顧客の特定など）
- 業務ステータスの推移による処理能力の可視化
- 税理士法上の業務処理簿としての記録の整合性確認

---

## 運用環境

- OS：Windows 10 / Windows 11
- ブラウザ：Microsoft Edge（Chromiumベース）
- サーバー：既存のWindowsサーバーに同居（RPA用途）
- Microsoft 365環境あり

---

## 将来の拡張予定

### フェーズ2以降で追加を検討する項目
- 難易度・自己評価（自分のスキルに対して難しすぎたか）
- 関与した税理士・補助者の記録
- 処理の要旨（定型文からの選択）

### Chrome対応
- 同一コード（Manifest V3）のままChromeウェブストアへ申請するだけで対応可能
- 追加開発は不要

### RPA連携（Power Automate Desktop）
- 将来的にスマホからの入力にも対応する場合
- Googleフォーム or Power Apps → スプレッドシート → RPA → MyKomon の構成で拡張可能

---

## 開発上の注意事項

1. **MyKomonのDOM構造はTKCのアップデートで変わる可能性がある**
   - テキストエリアの特定はIDよりも複数の属性を組み合わせて行う
   - 動作確認は月1回実施するルールを設ける

2. **タグの命名規則は絶対に変更しない**
   - 変更するとCSVエクスポート後のAI分析で過去データとの整合性が失われる

3. **MyKomonのログイン情報は拡張機能内に保存しない**
   - セキュリティポリシー上、認証情報の取り扱いは行わない

4. **拡張機能の配布方法**
   - Microsoft Edge アドオンストア経由、またはグループポリシーによる社内配布
   - 職員が個別にインストール・アンインストールできないよう管理者が制御することを推奨

---

## app.py の既知の問題点（2026-04-27 記録）

Streamlit アプリ（日報分析アプリ）の開発中に発覚したバグと対処法。将来の修正作業で同じ過ちを繰り返さないために記録する。

---

### 問題1：Streamlit Cloud のエントリポイントはルートの `app.py`

**症状**：`日報分析アプリ/app.py` を何時間編集しても Streamlit Cloud に反映されない。  
**原因**：Streamlit Cloud のログに `main module: 'app.py'` と表示されており、ルート直下の `app.py` が entry point。`日報分析アプリ/app.py` はローカル版専用。  
**対処**：クラウド版を修正するときは**必ずルートの `app.py` を直接編集する**。

**ファイルの使い分け**：
| ファイル | 用途 |
|---|---|
| `app.py`（ルート） | Streamlit Cloud（クラウド版）のエントリポイント |
| `日報分析アプリ/app.py` | ローカル版（.bat ファイルから起動）のエントリポイント |
| `配布用/所長配布用/日報分析アプリ/app.py` | ローカル版のコピー（所長配布フォルダ）。更新時は手動で同期が必要 |

---

### 問題2：`%#m` は Windows 専用 — Linux（Streamlit Cloud）でクラッシュする

**症状**：データ読み込み後に Streamlit Cloud でエラーが発生し、グラフが表示されない。  
**原因**：`strftime("%Y年%#m月")` の `%#m`（ゼロ埋めなし月）は Windows 専用書式。Linux では `%-m` を使う。  
**対処**：

```python
# 誤（Windows専用）
label = dates.min().strftime("%Y年%#m月")

# 正（OS判定で分岐）
_fmt = "%Y年%-m月" if os.name != "nt" else "%Y年%#m月"
label = dates.min().strftime(_fmt)
```

---

### 問題3：`st.stop()` をタブ生成前に呼ぶと全タブがブロックされる

**症状**：Tab6「人事経営相談」がデータ未読み込み時に表示されない（相談はデータ不要なのに使えない）。  
**原因**：`if df.empty: st.info(...); st.stop()` をタブ生成コードより前に書くと、`st.tabs([...])` 自体が実行されず全タブが消える。  
**対処**：`st.stop()` はタブ生成前に書かない。各タブ内部に `if df.empty: st.info(_NO_DATA)` を入れてガードする。

```python
# 誤
if df.empty:
    st.info("データがありません")
    st.stop()  # ここで止まると以降のタブが全部消える

tab1, tab2, tab3, ... = st.tabs([...])

# 正
tab1, tab2, tab3, ... = st.tabs([...])

with tab1:
    if df.empty:
        st.info(_NO_DATA)
    else:
        # グラフ描画
```

---

### 問題4：変数の初期化漏れによる `NameError`

**症状**：Tab5 の AI レポート生成ボタン描画時に `NameError: name 'summary_text' is not defined`。  
**原因**：`summary_text` を `if not df.empty:` ブロック内でのみ代入し、`df.empty` のときに未定義のまま後続コードが参照した。  
**対処**：条件分岐の前に必ず初期値を設定する。

```python
# 誤
if not df.empty:
    summary_text = generate_report(...)
# df.empty のとき summary_text は未定義

st.button("送る", disabled=not summary_text)  # NameError

# 正
summary_text = ""  # 先に初期化
if not df.empty and get_api_key():
    summary_text = generate_report(...)

st.button("送る", disabled=not summary_text)
```

---

### 問題5：`st.text_area` の `value=` は既存の session_state を上書きしない

**症状**：「この結果を相談入力欄にセット」ボタンを押しても入力欄が変わらない。  
**原因**：`st.text_area(key="k", value=x)` は `st.session_state["k"]` が既に存在すると `value=` を完全に無視する。  
**対処**：プリフィルしたいテキストを直接 `st.session_state` のウィジェットキーに書き込んでから `st.rerun()` する。

```python
# 誤
st.session_state["consult_prefill"] = text
st.rerun()
# ↓ text_area 側で value=prefill としても key が存在すると無視される

# 正
st.session_state["consult_question_input"] = text  # ウィジェットキーを直接書き換え
st.rerun()
```

---

### 配布用フォルダの手動同期が必要

`日報分析アプリ/app.py` を更新したら、以下への手動コピーも忘れずに行う：

```
配布用/所長配布用/日報分析アプリ/app.py
配布用/所長配布用/日報分析アプリ/analyzer.py
配布用/所長配布用/日報分析アプリ/knowledge.py
配布用/所長配布用/日報分析アプリ/使用マニュアル.md
配布用/所長配布用/日報分析アプリ/instruction_director.md
配布用/所長配布用/instruction_director.md
```

---

## app.py の理想的なフォルダ構成（2026-04-27 設計レビュー）

### 現状の問題：同じファイルが3箇所に存在し手動同期が必要

```
現状（問題あり）
/
├── app.py                ← Streamlit Cloud 専用（クラウドのみ）
├── analyzer.py           ← クラウド用
├── knowledge.py          ← クラウド用
├── manual.md             ← クラウド用
├── 日報分析アプリ/
│   ├── app.py            ← ローカル専用（内容はクラウド版と別管理）
│   ├── analyzer.py       ← ローカル用（同じ内容の重複）
│   ├── knowledge.py      ← ローカル用（同じ内容の重複）
│   └── 使用マニュアル.md
└── 配布用/所長配布用/日報分析アプリ/
    ├── app.py            ← 手動コピー（更新漏れが起きやすい）
    ├── analyzer.py       ← 手動コピー
    ├── knowledge.py      ← 手動コピー
    └── 使用マニュアル.md ← 手動コピー
```

`app.py` の実体が**クラウド版・ローカル版・配布用**の3か所に分散しており、
更新するたびに3か所を手動で同期しなければならない。同期漏れがバグの温床になる。

---

### 理想構成A：Streamlit Cloud の entry point を `日報分析アプリ/app.py` に変更する

最小変更で二重管理を解消できる案。Streamlit Cloud の設定画面で **Main file path** を
`日報分析アプリ/app.py` に変更するだけでよい（コード変更は不要）。

```
理想構成A（推奨）
/
├── 日報分析アプリ/           ← ここだけメンテすれば Cloud もローカルも動く
│   ├── app.py                ← Cloud + ローカル共通 entry point
│   ├── analyzer.py
│   ├── knowledge.py
│   ├── 使用マニュアル.md
│   └── instruction_director.md
├── 配布用/所長配布用/
│   ├── instruction_director.md   ← 手動コピー（引き続き必要）
│   └── 日報分析アプリ/           ← 手動コピー（引き続き必要）
└── edge-extension/
    └── ...
```

**メリット**：ルートの `app.py` / `analyzer.py` / `knowledge.py` が不要になり、
「クラウド用」と「ローカル用」の二重管理が消える。  
**デメリット**：Streamlit Cloud の設定変更が必要（一度だけの作業）。

**変更手順**：
1. Streamlit Cloud のダッシュボードでアプリの Settings を開く
2. **Main file path** を `app.py` → `日報分析アプリ/app.py` に変更して Save
3. ルートの `app.py` / `analyzer.py` / `knowledge.py` / `manual.md` を削除

---

### 理想構成B：全ファイルをルートに統合する

ローカル版の `.bat` ファイルもルートの `app.py` を指すように変更し、
`日報分析アプリ/` フォルダ自体をなくす案。

```
理想構成B（シンプル）
/
├── app.py                ← Cloud + ローカル共通（.bat もここを指す）
├── analyzer.py
├── knowledge.py
├── manual.md
├── instruction_director.md
├── 配布用/所長配布用/
│   └── （バッチと起動ショートカットのみ。py ファイルは共有）
└── edge-extension/
    └── ...
```

**メリット**：`.py` ファイルの重複が完全になくなる。ローカルもクラウドも1つのファイルを参照。  
**デメリット**：ローカル版の `.bat` ファイルのパス修正が必要。`配布用/` の py ファイルを
削除してルートへのパス参照に切り替える作業が発生する。

---

### 現状のまま運用する場合の最低限のルール

構成変更をしない場合は、以下を開発ルールとして徹底する：

| ルール | 理由 |
|---|---|
| クラウド版修正 → ルートの `app.py` を編集 | `日報分析アプリ/app.py` はクラウドに反映されない |
| ローカル版修正 → `日報分析アプリ/app.py` を編集 | ルート `app.py` はローカル版の `.bat` から参照されない |
| 両方に同じ修正が必要なら両方に適用 | 内容が乖離すると動作の差異が生じる |
| `analyzer.py` / `knowledge.py` を修正したら両方のフォルダに適用 | 共有ロジックが分岐するとデバッグ困難になる |
| 配布用への同期は修正のたびに実施 | 所長のローカル版が古いまま動作し続けるリスクを防ぐ |
