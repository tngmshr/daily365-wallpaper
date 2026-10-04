"""docs/scoring.csv と除外リストから、ブラウザで見る採点一覧 docs/scoring.html を作る。"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

calendar = json.loads((ROOT / "assets/data/calendar.json").read_text(encoding="utf-8"))
entries = {e["date"]: e for e in calendar["entries"]}
entries["02-29"] = dict(calendar["leap_day"], date="02-29")

rows = []
for r in csv.DictReader((DOCS / "scoring.csv").open(encoding="utf-8-sig")):
    e = entries.get(r["date"], {})
    rows.append({**r, "summary": e.get("summary", ""), "excluded": ""})
for r in csv.DictReader((DOCS / "exclusions.csv").open(encoding="utf-8-sig")):
    if r["判定"] == "除外":
        rows.append({"date": r["date"], "title": r["title"], "verdict": "除外", "excluded": r["理由"],
                     "summary": e["summary"] if (e := entries.get(r["date"], {})).get("title") == r["title"] else ""})
rows.sort(key=lambda r: r["date"])

TEMPLATE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>記念日採点一覧</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--text:#1f2328;--muted:#656d76;--line:#d8dee4;
--keep:#1a7f37;--keep-bg:#dafbe1;--check:#9a6700;--check-bg:#fff8c5;--ex:#cf222e;--ex-bg:#ffebe9;
--work:#0969da;--uniq:#8250df;--season:#bf3989}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1117;--card:#161b22;--text:#e6edf3;--muted:#8d96a0;--line:#30363d;
--keep:#3fb950;--keep-bg:#12261e;--check:#d29922;--check-bg:#2b2111;--ex:#f85149;--ex-bg:#2d1214}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 "Yu Gothic UI","Hiragino Sans",sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:2}
h1{font-size:18px;margin:0 0 8px}.stats{display:flex;flex-wrap:wrap;gap:6px 14px;color:var(--muted);font-size:13px;margin-bottom:8px}
.stats b{color:var(--text)}.filters{display:flex;flex-wrap:wrap;gap:8px}
select,input{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--text)}
input{flex:1;min-width:160px}main{padding:12px 16px 40px;max-width:1100px;margin:0 auto}
h2{font-size:15px;margin:20px 0 8px;color:var(--muted)}
.row{display:grid;grid-template-columns:52px 1fr auto;gap:4px 12px;background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:6px}
.row.v-残す{border-left-color:var(--keep)}.row.v-要検討{border-left-color:var(--check)}.row.v-除外{border-left-color:var(--ex);opacity:.7}
.date{font-weight:700;font-variant-numeric:tabular-nums}.title{font-weight:700}
.total{font-size:20px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums}
.meta,.sum,.issue{grid-column:2/4;font-size:13px}.meta{color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 10px}
.sum{color:var(--muted)}.issue{color:var(--ex)}
.tag{display:inline-block;padding:0 8px;border-radius:10px;font-size:12px;font-weight:700;margin-left:6px}
.t-残す{background:var(--keep-bg);color:var(--keep)}.t-要検討{background:var(--check-bg);color:var(--check)}.t-除外{background:var(--ex-bg);color:var(--ex)}
.c-仕事{color:var(--work)}.c-ユニーク{color:var(--uniq)}.c-季節{color:var(--season)}
a{color:var(--work)}.fail{color:var(--ex);font-weight:700}
@media (max-width:600px){.row{grid-template-columns:44px 1fr auto}}
</style></head><body>
<header><h1>記念日採点一覧（1年目・現行データ）</h1><div class="stats" id="stats"></div>
<div class="filters">
<select id="fv"><option value="">判定: すべて</option><option>残す</option><option>要検討</option><option>除外</option></select>
<select id="fc"><option value="">区分: すべて</option><option>仕事</option><option>ユニーク</option><option>季節</option></select>
<select id="fs"><option value="">出典: すべて</option><option value="confirmed">確認済み</option><option value="date_only">日付のみ</option><option value="not_found">見つからない</option><option value="conflict">食い違い</option></select>
<select id="fo"><option value="date">日付順</option><option value="score">点数の低い順</option></select>
<input id="fq" placeholder="名前・説明で検索"></div></header>
<main id="list"></main>
<script>
const ROWS=__DATA__;
const ST={confirmed:"確認済み",date_only:"日付のみ",not_found:"見つからない",conflict:"食い違い"};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $=id=>document.getElementById(id);
function stats(){const c=(k,v)=>ROWS.filter(r=>r[k]===v).length,keep=ROWS.filter(r=>r.verdict==="残す");
const k=v=>keep.filter(r=>r.category===v).length;
$("stats").innerHTML=`<span>全 <b>${ROWS.length}</b></span><span>残す <b>${c("verdict","残す")}</b></span><span>要検討 <b>${c("verdict","要検討")}</b></span><span>除外 <b>${c("verdict","除外")}</b></span><span>残すの内訳: 仕事 <b>${k("仕事")}</b> / ユニーク <b>${k("ユニーク")}</b> / 季節 <b>${k("季節")}</b>（目安 255/73/37）</span>`}
function render(){const v=$("fv").value,c=$("fc").value,s=$("fs").value,q=$("fq").value.trim(),o=$("fo").value;
let rs=ROWS.filter(r=>(!v||r.verdict===v)&&(!c||r.category===c)&&(!s||r.status===s)&&(!q||(r.title+r.summary).includes(q)));
if(o==="score")rs=[...rs].sort((a,b)=>(+a.total||-99)-(+b.total||-99));
let html="",m="";
for(const r of rs){const mm=r.date.slice(0,2);if(o==="date"&&mm!==m){m=mm;html+=`<h2>${+mm}月</h2>`}
const [a,b]=r.date.split("-");let meta="";
if(r.excluded){meta=`<span>${esc(r.excluded)}</span>`}else{
const gates=["G1","G2","G3","G4"].filter(g=>r[g]==="0");
meta=`<span class="c-${esc(r.category)}">${esc(r.category)}</span><span>仕事${esc(r.A)} 出典${esc(r.B)} 話題${esc(r.C)} 季節${esc(r.D)} 東京${esc(r.F)} PR${esc(r.E)}</span><span>出典: ${ST[r.status]||esc(r.status)}${r.primary_url?` <a href="${esc(r.primary_url)}" target="_blank" rel="noopener">開く</a>`:""}</span><span>制定: ${esc(r.founder||r.founder_type)}</span>${gates.length?`<span class="fail">足切り: ${gates.join(",")}</span>`:""}${r.note?`<span>${esc(r.note)}</span>`:""}`}
html+=`<div class="row v-${esc(r.verdict)}"><div class="date">${+a}/${+b}</div><div class="title">${esc(r.title)}<span class="tag t-${esc(r.verdict)}">${esc(r.verdict)}</span></div><div class="total">${r.excluded?"":esc(r.total)}</div><div class="meta">${meta}</div><div class="sum">${esc(r.summary)}</div>${r.summary_issue?`<div class="issue">要修正: ${esc(r.summary_issue)}</div>`:""}</div>`}
$("list").innerHTML=html||"<p>該当なし</p>"}
["fv","fc","fs","fo"].forEach(id=>$(id).addEventListener("change",render));$("fq").addEventListener("input",render);
stats();render();
</script></body></html>"""

out = TEMPLATE.replace("__DATA__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
(DOCS / "scoring.html").write_text(out, encoding="utf-8")
print(f"{len(rows)} rows -> docs/scoring.html")
