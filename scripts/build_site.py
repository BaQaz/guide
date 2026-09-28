#!/usr/bin/env python3
"""リポジトリの Markdown から、1ファイルで完結するサイト site/index.html を作る。

使い方: python3 scripts/build_site.py
読むもの:
  docs/question-tree.md        ボタンの一覧
  content/**/*.md              記事（1問1ファイル）
  content/**/*.md の「まとめ書き」  `=== FILE: content/1/1-01.md ===` 区切りで複数記事を1ファイルに書いたもの
  data/players/*.md            選手・監督カード
標準ライブラリだけで動く。Markdown の表示はブラウザ側の小さな変換で行う。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE_MARK = re.compile(r"^=== FILE: (\S+) ===\s*$", re.M)


def parse_tree():
    cats, cur, last_l1 = [], None, None
    for line in (ROOT / "docs/question-tree.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (\d)\. (.+)$", line)
        if m:
            cur = {"no": m.group(1), "title": m.group(2), "items": []}
            cats.append(cur)
            continue
        m = re.match(r"^- \*\*(\d-\d\d) (.+?)\*\*(.*)$", line)
        if m and cur:
            title = m.group(2) + m.group(3)
            last_l1 = {"id": m.group(1), "title": title.replace("★", "").strip(),
                       "star": "★" in title, "check": "🔍" in title, "children": []}
            cur["items"].append(last_l1)
            continue
        m = re.match(r"^  - (\d-\d\d-[a-z]) (.+)$", line)
        if m and last_l1:
            last_l1["children"].append({"id": m.group(1), "title": m.group(2).strip(), "check": "🔍" in m.group(2)})
    return cats


def parse_front(text):
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return meta, body
    body, key = m.group(2), None
    for line in m.group(1).splitlines():
        line = re.sub(r"\s+#.*$", "", line)
        lm = re.match(r"^\s+-\s+(.+)$", line)
        if lm and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(lm.group(1).strip())
            continue
        km = re.match(r"^(\w+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            if val.startswith("["):
                meta[key] = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
            elif val:
                meta[key] = {"true": True, "false": False}.get(val, val.strip("\"'"))
    return meta, body


def load_articles():
    arts = {}
    for p in sorted((ROOT / "content").rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        parts = FILE_MARK.split(text)
        chunks = [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)] if len(parts) > 1 else [(str(p), text)]
        for name, chunk in chunks:
            chunk = chunk.strip()
            chunk = re.sub(r"^```\w*\n|\n```$", "", chunk)  # コードブロックで包まれていても読む
            meta, body = parse_front(chunk + "\n")
            aid = meta.get("id") or Path(name).stem
            arts[aid] = {"meta": meta, "body": body.strip()}
    return arts


def load_players():
    base = ROOT / "data/players"
    groups = []
    for fname, team in [("managers.md", "監督"), ("lotte.md", "ロッテ"), ("fighters.md", "日本ハム")]:
        p = base / fname
        if not p.exists():
            continue
        section = ""
        for block in re.split(r"^(?=#{1,2} )", p.read_text(encoding="utf-8"), flags=re.M):
            head = block.splitlines()[0] if block.strip() else ""
            if head.startswith("# ") and not head.startswith("## "):
                section = head[2:].strip()
                continue
            if head.startswith("## "):
                title = head[3:].strip()
                name = re.split(r"[（(]", title)[0].strip()
                groups.append({"team": team, "section": section or team, "name": name,
                               "title": title, "body": "\n".join(block.splitlines()[1:]).strip()})
    # data/players/detail/<チーム>-<名前>.md があれば、その選手のカードを詳しい版に差し替える（なければ追加）
    norm = lambda x: re.sub(r"[（(].*$", "", x).replace(" ", "").replace("　", "").replace("髙", "高").replace("﨑", "崎")
    for p in sorted((base / "detail").glob("*.md")) if (base / "detail").exists() else []:
        text = p.read_text(encoding="utf-8").strip()
        m = re.match(r"^## (.+?)\n(.*)$", text, re.S)
        if not m:
            continue
        title, body = m.group(1).strip(), m.group(2).strip()
        hit = next((g for g in groups if norm(g["name"]) == norm(title)), None)
        if hit:
            hit.update(title=title, body=body, detail=True)
        else:
            team = p.stem.split("-")[0]
            groups.append({"team": team, "section": "追加の選手", "name": norm(title), "title": title, "body": body, "detail": True})
    lineup = []
    readme = base / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*(\d|投)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|$", line)
            if m:
                lineup.append(list(m.groups()))
    # 背番号（見出しの「#86」）と、Wikipedia の選手ページの写真（data/players/photos.json）
    photos = json.loads((base / "photos.json").read_text(encoding="utf-8")) if (base / "photos.json").exists() else {}
    for g in groups:
        m = re.search(r"#(\d+)", g["title"])
        g["number"] = m.group(1) if m else ""
        ph = photos.get(g["name"]) or photos.get(re.sub(r"[（(].*$", "", g["name"]).strip())
        if ph:
            g["photo"] = ph
    return groups, lineup


def main():
    data = {"tree": parse_tree(), "articles": load_articles()}
    data["players"], data["lineup"] = load_players()
    readme = ROOT / "data/players/README.md"
    data["lineup_announced"] = readme.exists() and "## 発表スタメン" in readme.read_text(encoding="utf-8")
    today = (ROOT / "data/today.md").read_text(encoding="utf-8")
    data["today"] = today
    tpl = (ROOT / "scripts/site_template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site/index.html").write_text(out, encoding="utf-8")
    n_q = sum(1 + len(i["children"]) for c in data["tree"] for i in c["items"])
    print(f"site/index.html: 疑問 {n_q} / 記事 {len(data['articles'])} / 選手 {len(data['players'])}")


if __name__ == "__main__":
    main()
