"""Build the 365-day offline Japanese calendar from cached date-page sources.

calendar.json は手作業で精選した版。このスクリプトを実行すると上書きされるので通常は使わない。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "work" / "date_articles_raw.json"
OUT = ROOT / "assets" / "data" / "calendar.json"

WORK_TIPS = {
    "nature": ["身近な資源の使い方を一つ見直す", "自然や周囲への影響を一つ確かめる"],
    "water": ["水や電気を無駄なく使う手順を見直す", "身近な水資源を大切にする工夫を一つ考える"],
    "travel": ["初めての人にも伝わる案内になっているか見直す", "移動や準備の段取りを一つ整える"],
    "history": ["過去の事例から、次に生かせる点を一つ拾う", "いつもの手順の背景を調べてみる"],
    "people": ["協力してくれた人に感謝を伝える", "相手の立場を確かめてから言葉を選ぶ"],
    "peace": ["異なる立場の意見を最後まで聞く", "相手を尊重する伝え方を一つ選ぶ"],
    "sports": ["準備運動や安全確認を丁寧に行う", "練習や作業の成果を記録して次に生かす"],
    "science": ["事実と推測を分け、根拠を一つ確かめる", "小さな疑問を一つ調べて共有する"],
    "space": ["視点を少し引いて、全体の関係を見直す", "大きな目標を今日できる一歩に分ける"],
    "culture": ["相手の背景やことばに意識を向ける", "学んだことを短く共有する"],
    "food": ["食材や道具を大切に扱う", "準備や片付けを一つ丁寧に整える"],
    "health": ["無理のない休憩や準備を一つ整える", "自分と周囲の健康を守る行動を一つ考える"],
    "technology": ["いつもの作業を一つ安全に効率化できないか考える", "道具やデータの扱い方を一つ見直す"],
    "work": ["今日の仕事で先に進める一歩を一つ決める", "普段の仕事を支える人や仕組みに目を向ける"],
    "seasonal": ["季節に合わせて身の回りを一つ整える", "変化に備え、予定や持ち物を一つ確認する"],
}

TITLE_OVERRIDES = {
    "02-09": "ドミノ・ピザの「For Good」デー（国際ピザデー）",
    "07-09": "ミソフォニア啓発の日",
    "07-16": "国土交通デー",
    "08-17": "Dream Zoneのラジオを楽しむ日",
}


def date_page_url(title: str) -> str:
    return "https://ja.wikipedia.org/wiki/" + quote(title, safe="")


def extract_section(raw: str) -> str:
    match = re.search(r"^==\s*記念日・年中行事\s*==\s*$", raw, re.M)
    if not match:
        return ""
    tail = raw[match.end() :]
    end = re.search(r"^==[^=].*?==\s*$", tail, re.M)
    return tail[: end.start()] if end else tail


def parse_items(raw: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in extract_section(raw).splitlines():
        if re.match(r"^\*(?!\*|:|#)\s*", line):
            if current:
                items.append(current)
            content = line.lstrip("* ").strip()
            # A few date pages put the explanation after two spaces on the same bullet.
            split = re.search(r"\s{2,}(?=\[\[|[A-Z]|[\u3040-\u30ff\u4e00-\u9fff])", content)
            inline_note = ""
            if split:
                inline_note = content[split.end() :]
                content = content[: split.start()]
            current = {"raw_title": content, "raw_note": inline_note, "raw_line": line}
        elif current and re.match(r"^\*+:\s*", line):
            current["raw_note"] += " " + re.sub(r"^\*+:\s*", "", line).strip()
    if current:
        items.append(current)
    return items


def _template_text(match: re.Match[str]) -> str:
    body = match.group(1)
    parts = body.split("|")
    name = parts[0].strip().lower()
    label = re.search(r"(?:^|\|)\s*label\s*=\s*([^|]+)", body)
    if label:
        return label.group(1).strip()
    if name in {"仮リンク", "ill"} and len(parts) > 1:
        return parts[1].strip()
    if name in {"lang", "lang-en", "lang-ja"} and len(parts) > 2:
        return parts[2].strip()
    if name in {"nowrap", "small", "ruby"} and len(parts) > 1:
        return parts[1].strip()
    return ""


def clean_wikitext(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref\b[^>]*>.*?</ref\s*>", "", text, flags=re.S)
    text = re.sub(r"<ref\b[^>]*/\s*>", "", text)
    for _ in range(12):
        updated = re.sub(r"\{\{([^{}]*)\}\}", _template_text, text)
        if updated == text:
            break
        text = updated
    text = re.sub(r"\[\[ファイル:[^\]]*\]\]", "", text, flags=re.I)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]+\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("'''", "").replace("''", "")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[（(]\s*[)）]", "", text)
    text = re.sub(r"^[（(](.+)[)）]$", r"\1", text)
    return text.strip(" \t\r\n。、")


def clean_title(text: str) -> str:
    title = clean_wikitext(text)
    # The day pages often append the English title of an already translated name.
    title = re.sub(r"\s*[（(][^()（）]*[A-Za-z][^()（）]*[)）]", "", title)
    title = re.sub(r"\s*\(International Days\)", "", title, flags=re.I)
    title = re.sub(r"[（(]\s*[)）]", "", title)
    return title.strip(" 、・/／")


def references(note: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for ref in re.finditer(r"<ref\b[^>]*>(.*?)</ref\s*>", note, flags=re.S):
        body = ref.group(1)
        url = re.search(r"\burl\s*=\s*([^|}\n]+)", body, re.I)
        if not url:
            url = re.search(r"\bhttps?://[^\s|}\]]+", body, re.I)
            if not url:
                continue
            target = url.group(0).rstrip(".,")
        else:
            target = url.group(1).strip().strip("<>")
        title = re.search(r"\btitle\s*=\s*([^|}\n]+)", body, re.I)
        publisher = re.search(r"\bpublisher\s*=\s*([^|}\n]+)", body, re.I)
        label = clean_wikitext((title or publisher).group(1)) if (title or publisher) else "関連する参考情報"
        if target.startswith("//"):
            target = "https:" + target
        if target.startswith("http") and all(row["url"] != target for row in found):
            found.append({"label": label or "関連する参考情報", "url": target})
    return found


def choose_summary(note: str, title: str) -> str:
    summary = clean_wikitext(note)
    if not summary:
        if title == "クリスマス・イヴ":
            return "クリスマスの前夜にあたる日です。地域や宗教、家庭によって過ごし方はさまざまです。"
        return f"「{title}」に関する日付です。記事に掲載された背景や関連資料を出典から確認できます。"
    sentences = re.split(r"(?<=[。！？])\s*", summary)
    if len(summary) > 220:
        summary = "".join(sentences[:2]).strip() if sentences[0] else summary[:220]
    if len(summary) > 260:
        summary = summary[:257].rsplit("、", 1)[0] + "…"
    return summary


def theme_for(title: str, summary: str) -> str:
    text = title + " " + summary
    if re.search(r"節分|七夕|正月|新年|大晦日|年末|年越し|除夜|クリスマス|春分|秋分|冬至|夏至|春季|夏季|秋季|冬季", text):
        if not re.search(r"平和|人権|戦争|追悼|難民", text):
            return "seasonal"
    rules = [
        ("peace", r"平和|人権|暴力|奴隷|戦争|追悼|ホロコースト|難民|共存|差別|殉教|核実験|原爆|被曝|被爆"),
        ("sports", r"スポーツ|競技|大会|駅伝|野球|サッカー|ゴルフ|競馬|マラソン|相撲|水泳|ラグビー|バスケット|卓球|テニス|スキー|スケート|オリンピック|ボクシング|けん玉|ダービー|競輪|競走|選手権|プロレス|運動会"),
        ("space", r"宇宙|月面|天文|衛星|惑星|星空|宇宙飛行|ロケット|NASA"),
        ("water", r"海洋|海の日|海岸|海難|水資源|水の日|河川|湿地|水質|水産|漁業|漁|クジラ|サンゴ|氷河|湖沼|水辺|水生"),
        ("food", r"食|料理|農業|穀物|野菜|果物|コーヒー|チョコ|食品|栄養|ピザ|寿司|ラーメン|シュウマイ|うどん|アイスクリーム|ジャム|バレンタイン|調味料|塩の日|みそ|発酵|弁当|醸造|飲料|酒造|お菓子|菓子"),
        ("health", r"健康|医療|病|睡眠|献血|血液|がん|障害|福祉|看護|感染|エイズ|保健"),
        ("technology", r"技術|工学|発明|発電|エネルギー|電気|通信|インターネット|コンピューター|自動車|鉄道|交通|地下鉄|路面電車|空気清浄機|家電|ミシン|情報誌|消防|ラジオ|テレビ|放送"),
        ("science", r"科学|研究|数学|物理|化学|生物|進化|地質|地球|気象|気候|観測|データ"),
        ("travel", r"観光|旅行|旅|登山|航空|鉄道|電車|航海|港|地図|探検|世界遺産|公園"),
        ("nature", r"自然|環境|森林|森|木|植物|花|動物|生物|野生|鳥|魚|犬|猫|フナ|カメ|すずめ|スズメ|ペット|昆虫|自然公園|生態|地球"),
        ("culture", r"文化|教育|学校|文字|言語|点字|読書|書籍|出版|図書|本の日|文学|詩|音楽|芸術|美術|写真|映画|演劇|博物館|翻訳|識字|識者|祭|祭礼|神社|寺|仏|御影|祈り|宗教|絵手紙|切手|スカウト|芸妓|タウン情報"),
        ("history", r"歴史|建国|独立|革命|憲法|条約|開通|開業|開設|創立|設立|発足|成立|公布|就任|結成|戦国|日本初|初めて|第1回|記念館|落成|皇帝|王国"),
        ("work", r"仕事|労働|働|産業|初荷|職業|運輸|交通安全|安全"),
        ("seasonal", r"春季|夏季|秋季|冬季|節分|七夕|正月|新年|大晦日|年末|年越し|除夜|クリスマス|季節|立春|立秋|冬至|夏至|春分|秋分"),
    ]
    for theme, pattern in rules:
        if re.search(pattern, text):
            return theme
    return "people"


def score(item: dict[str, str], title: str, summary: str, refs: list[dict[str, str]]) -> int:
    raw = item["raw_title"]
    body = item["raw_note"]
    if not title or re.fullmatch(r"[\W_]+", title):
        return -100
    points = 0
    points += 10 if summary else 0
    points += 5 if 25 <= len(summary) <= 240 else 0
    points += 5 if refs else 0
    points += 45 if "{{UN}}" in raw else 0
    points += 28 if re.search(r"世界|国際", title) else 0
    points += 20 if "{{World}}" in raw else 0
    points += 4 if re.search(r"制定|由来|記念|この日|設立|始ま", summary) else 0
    if re.search(r"元日|正月|初詣", title) and not re.search(r"制定|由来|この日|祝日", summary):
        points -= 8
    if re.search(r"\{\{JPN\}\}", raw):
        points += 2
    if re.search(r"株式会社|会社|商品|製品|発売|ブランド|チョコレート|ガチャ|プリキュア|企業", summary):
        points -= 16
    if re.search(r"旧暦|太陰暦|陰暦|年によって|年ごとに変|変動祝日|イースター|復活祭|春節|ラマダーン|2月末日|閏年の場合|第\s*[一二三四五1-5].*(?:曜|金曜)|(?:第|最初の).*(?:金曜日|土曜日|日曜日)|春分|秋分|節分", title + summary):
        points -= 80
    return points


def work_tip(theme: str, index: int) -> str:
    choices = WORK_TIPS[theme]
    return choices[index % len(choices)]


def to_entry(title: str, raw: str, index: int) -> dict[str, object]:
    items = parse_items(raw)
    ranked = []
    for item in items:
        name = clean_title(item["raw_title"])
        summary = choose_summary(item["raw_note"], name) if name else ""
        cites = references(item["raw_note"])
        ranked.append((score(item, name, summary, cites), item, name, summary, cites))
    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = ranked[0] if ranked else None
    if not selected or selected[0] < 0:
        name = "今日の暦メモ"
        summary = "この日付の記念日や行事は、出典記事に掲載された情報から紹介しています。"
        cites = []
    else:
        _, item, name, summary, cites = selected
    if not name:
        name = "今日の暦メモ"
    if not summary:
        summary = choose_summary("", name)
    month, day = map(int, title.removesuffix("日").split("月"))
    date = f"{month:02d}-{day:02d}"
    name = TITLE_OVERRIDES.get(date, name)
    theme = theme_for(name, summary)
    citations = cites[:1]
    if selected and "{{UN}}" in selected[1]["raw_title"]:
        citations.append({"label": "国連の国際デー一覧", "url": "https://www.un.org/en/observances/list-days-weeks"})
    citations.append({"label": f"{month}月{day}日の日付記事と脚注", "url": date_page_url(title)})
    return {
        "date": date,
        "title": name,
        "kind": "記念日・年中行事",
        "summary": summary,
        "work_tip": work_tip(theme, index),
        "visual": theme,
        "sources": citations,
    }


def main() -> None:
    pages = json.loads(RAW.read_text(encoding="utf-8"))
    entries: list[dict[str, object]] = []
    for index, title in enumerate(pages):
        entries.append(to_entry(title, pages[title], index))
    entries.sort(key=lambda row: row["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    leap_day = {
        "date": "02-29",
        "title": "うるう日（閏日）",
        "kind": "暦のしくみ",
        "summary": "季節と暦のずれを小さくするため、グレゴリオ暦では閏年に2月29日を置きます。1太陽年は約365.2422日です。",
        "work_tip": "長期の予定は、周期や変化も含めて確認する",
        "visual": "science",
        "sources": [
            {"label": "国立天文台 暦計算室「閏年と旧暦について」", "url": "https://eco.mtk.nao.ac.jp/koyomi/topics/html/topics1990.html"},
            {"label": "2月29日の日付記事", "url": date_page_url("2月29日")},
        ],
    }
    OUT.write_text(json.dumps({"format": 1, "license": "Calendar text adapted from Japanese Wikipedia under CC BY-SA 4.0; original artwork", "entries": entries, "leap_day": leap_day}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    visual_counts = Counter(row["visual"] for row in entries)
    empty_summaries = sum(not row["summary"] for row in entries)
    duplicate_titles = [key for key, count in Counter(row["title"] for row in entries).items() if count > 1]
    print(f"Wrote {len(entries)} entries; empty summaries={empty_summaries}; duplicate titles={len(duplicate_titles)}")
    print("Themes:", dict(visual_counts))
    for sample in ["01-01", "02-01", "06-05", "09-27", "12-24", "12-31"]:
        row = next((r for r in entries if r["date"] == sample), None)
        if row:
            print(f"{sample} | {row['title']} | {row['summary'][:95]} | {row['visual']}")


if __name__ == "__main__":
    main()
