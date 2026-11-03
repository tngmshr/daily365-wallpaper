# 年替わり・2〜4年目・日付が動く日の設計（2026-10-04 決定）

本人決定（10/4）: 「サーバー側で年1回差し替え」方式。手順4の「Android の画像取得方式」もこれでまとめて解決する。

## 方針

1. **データ**
   - `assets/data/calendar.json` は 1 年目（基準データ）のまま。
   - 2〜4 年目は `assets/data/years/slot2.json` 〜 `slot4.json` に「日付 → 差し替えエントリ」の差分だけを書く。無い日付は 1 年目を使う。
   - 年 → slot: `slot = (year - 2027) % 4 + 1`（2027 年が 1 年目）。2026 年以前は 1 年目のまま（`build_year.slot_for`、2026-11-03 決定）。
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
   - 0 時の切り替えでは保存済みの画像を使う。無い・壊れている場合は、1 年目と同じ内容の日なら同梱の `assets/wallpapers/MM-DD.webp`、違う日なら文章のカードを使う（下記「Android のロック画面」）。
   - `INTERNET` 権限を追加する。取得先は `tngmshr.github.io` のみ。

## 節気の照合（2026-10-17）

- `docs/solar_terms_check.csv` に、年・節気ごとの暦要項の時刻（公表済みの年だけ）と、ERFA（astropy）による視黄経の独立計算（JST、分単位）を置く。
- `python tools/check_solar_terms.py` で次を確かめる（標準ライブラリだけで動く）。
  - 2027〜2034 年の 4 節気がそろい、日付が節気ごとのありうる範囲に入っている。
  - 暦要項が公表済みの年は、その日付と一致し、`_sources` が暦要項の URL になっている（計算値のままならエラー）。
  - 未公表の年は、独立計算の日付と一致する。0 時まで 30 分未満なら警告。
  - 公表済みの年は、独立計算と暦要項の差が 2 分以内（計算方法の確認）。
  - `calendar.json` の節気エントリが 4 件そろい、`build_year` が各年の日付に置く。
- 暦要項（毎年 2 月ごろに翌年分が公表）が出たら、CSV の `published_jst` と `published_source`、`solar_terms.json` の日付と `_sources` を書き換える。計算をやり直すときは `--recompute`（astropy が必要）。
- テスト: `python -m unittest discover -s tools -p 'test_*.py'`

## 未決（別途）

- ~~挿絵のテーマ共用化、更新のお知らせ（手順4の残り）~~ 実装済み（お知らせは README「更新のお知らせ」）
- 2〜4 年目の中身（Codex の候補収集 → 採点 → slot 割り当て）
- アプリ画面の表示（2026-11-03 実装）: アプリ（Android・Web）も `lib/year_calendar.dart` で同じ規則により年を解決する（`assets/data/years/` と `solar_terms.json` を同梱）。1 年目と同じ内容の日は同梱の `assets/wallpapers/MM-DD.webp`、差し替え・節気の移動がある日は Pages の `wallpapers/YYYY/MM-DD.jpg` を表示し、読めないときは文章のカード（日付・種類・見出し・説明）で見せる。Web 版は表示した年別画像を直近 7 枚まで Service Worker に残す。`test/year_calendar_test.dart` が 2026〜2034 年について `build_year.py` の出力と突き合わせる。
  - 以前の式では 2026 年が 4 年目（`slot4.json`）になり、Pages は 2026 年分を差し替えて配っていた。2026 年以前は 1 年目のままにした（`slot_for`）。
- Android のロック画面（2026-11-03 実装）: `YearRotation.kt` が同じ規則でその日の項目を解決する。1 年目と内容が違う日（差し替え・節気の移動）に年別画像を取得できていなければ、同梱の 1 年目の壁紙（別の題材）は入れず、`WallpaperCard.kt` で日付・見出し・説明・仕事メモを描いた画像を入れる。この場合は「設定済み」として扱わず、予備の定期実行・アプリ復帰のたびに年別画像の取得をやり直し、取得できたら差し替える（1 年目と同じ日は従来どおり 1 日 1 回）。Kotlin の結果も 2025〜2034 年について `build_year.py` の出力と突き合わせて確認した（Android SDK のない環境で、JVM 上で実施）。
