# 年替わり・2〜4年目・日付が動く日の設計（2026-10-04 決定）

本人決定（10/4）: 「サーバー側で年1回差し替え」方式。手順4の「Android の画像取得方式」もこれでまとめて解決する。

## 方針

1. **データ**
   - `assets/data/calendar.json` は 1 年目（基準データ）のまま。
   - 2〜4 年目は `assets/data/years/slot2.json` 〜 `slot4.json` に「日付 → 差し替えエントリ」の差分だけを書く。無い日付は 1 年目を使う。
   - 年 → slot: `slot = (year - 2027) % 4 + 1`（2027 年が 1 年目）。
   - 日付が動く日（二十四節気）はエントリに `"solar_term": "立春"` などを持たせる。`assets/data/solar_terms.json`（国立天文台「暦要項」の年別日付、2027〜2034）でその年の実際の日付に置き、もともとその日付にあったエントリと入れ替える。
   - 祝日の移動（成人の日など）は採用しない（G3）。仕事始め 01-04 は官公庁の御用始め（行政機関の休日に関する法律）として固定日扱い。
2. **生成（CI）**
   - `tools/build_year.py --year YYYY` で、その年の 366 件（平年は 365 件）を解決した JSON を作り、`compose_wallpapers.py` に渡して年別の画像を作る。
   - Pages に出すもの:
     - `wallpapers/MM-dd.jpg` … **今年**分（iPhone ショートカット・Web が読む。URL は変えない）
     - `wallpapers/YYYY/MM-dd.jpg` … 今年分と来年分（Android の先読み用）
   - 定期実行: 毎年 12/31 23:30 JST（`cron: '30 14 31 12 *'`）。12/31 分はその朝に設定済みなので、切り替えの影響を受けない。手動実行（workflow_dispatch）も残す。
3. **Android**
   - 日中（WorkManager の定期実行）に**翌日分**を `wallpapers/YYYY/MM-dd.jpg` から取得し、アプリ内に保存する。
   - 0 時の切り替えでは保存済みの画像を使う。無い・壊れている場合は同梱の `assets/wallpapers/MM-DD.webp`（1 年目）を使う。
   - `INTERNET` 権限を追加する。取得先は `tngmshr.github.io` のみ。

## 未決（別途）

- 挿絵のテーマ共用化、更新のお知らせ（手順4の残り）
- 2〜4 年目の中身（Codex の候補収集 → 採点 → slot 割り当て）
