#!/usr/bin/env python3
"""ChatGPT に貼るプロンプト集 docs/gpt-prompts.html を作る。

使い方: python3 scripts/build_prompts.py
仕様ファイル（テンプレート・今日のデータ・疑問ツリー・選手カード）をプロンプトに埋め込むので、
仕様を変えたら作り直す。
"""
import html
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/BaQaz/guide"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").strip()


def tree_section(nos):
    text = read("docs/question-tree.md")
    head = text.split("---")[0].strip()
    parts = re.split(r"^(?=## \d\. )", text, flags=re.M)
    picked = [p.split("\n---")[0].strip() for p in parts if re.match(r"## (\d)\.", p) and re.match(r"## (\d)\.", p).group(1) in nos]
    return head + "\n\n" + "\n\n".join(picked)


def attach(rel, body=None):
    return f"<<<ファイル {rel}>>>\n{body if body is not None else read(rel)}\n<<<ここまで>>>"


def write_rules(issue, branch, pr_title, pr_ref, what):
    """GPT がリポジトリに直接書き込むための手順。長い出力がチャットで圧縮されないよう、1件ごとにコミットさせる。"""
    return f"""# 書き込みのしかた（厳守）
あなたは GitHub のリポジトリ BaQaz/guide に書き込めます。チャットに本文を出すのではなく、リポジトリに直接コミットしてください。
1. main から新しいブランチ `{branch}` を作る（すでにあれば、そのブランチに続けて書く）
2. {what}
3. 全部書き終えたら、`{branch}` から main へのプルリクエストを作る。タイトルは「{pr_title}」、本文の1行目に `{pr_ref}`、続けて：書いたもの（記事IDまたは選手名）の一覧／needs_check: true にしたIDと理由／使った出典URLの一覧
4. チャットには、コミットしたファイルの一覧とPRのURLだけを短く返す（本文をチャットに貼らない）
- 途中で止まったときは「どこまでコミットしたか」を書いて止まり、「続き」と送られたら次のファイルから再開する。同じファイルを二重に作らない
- 書き込めなかったときは、エラーの内容をそのまま伝えて止まる（チャットに全文を貼る方式に切り替えない）"""


def article_write_rules(j):
    return write_rules(j["issue"], j["branch"], f"#{j['issue']} {j['title']}（{j['part']}）", f"Refs #{j['issue']}",
                       f"""記事は1つ書くごとに、1記事＝1ファイルで、すぐにコミットする（まとめて書いてから一度にコミットしない）
   - 書くのは「今回書く範囲」の {len(j['ids'])} 本だけ。ほかの ID のファイルは作らない（別のチャットが書いています）
   - パス：`content/<カテゴリ番号>/<ID>.md`（例：`content/1/1-07.md`、`content/1/1-07-a.md`）
   - 中身：テンプレートどおりの front matter（--- で囲む）と本文だけ。コードブロックや `=== FILE: … ===` の区切りは入れない
   - コミットメッセージ：`<ID> <疑問の文> (#{j['issue']})`""")


def players_write_rules():
    return write_rules(9, "content/9-fighters", "#9 日本ハムの選手カード", "Closes #9", """data/players/fighters.md を直接編集してコミットする。選手を1人（またはセクション1つ）書き足すごとにコミットする（全部書いてから一度にコミットしない）
   - 毎回、ブランチ上の最新の fighters.md を読んでから追記する。既存の先発・スタメン部分は消さない
   - コミットメッセージ：`日本ハム <選手名またはセクション名> を追加 (#9)`""")


COMMON_RULES = """# 守ること
- 添付の「記事テンプレート」の型・字数・書き方ルール（とくに「口調」）に必ず従う。読み手は野球をまったく観たことがない大人で、球場の待ち時間にスマホで1〜2分で読む
- 「今日の試合で見るなら」は必須。添付の「今日の試合データ」「選手カード」にある具体的な選手名・場面で書く
- 2026年の出来事はあなたの学習データより新しい場合がある。今日の試合・2026年シーズンの数字や出来事は、添付データにあるものか、ウェブ検索で NPB・球団公式・主要紙から確認できたものだけを使い、front matter の sources に URL を書く
- 確認できない内容は書かない。確認が必要な記述が残る記事は needs_check: true にし、該当箇所に <!-- TODO: 確認 --> を残す
- 🔍 がついた疑問は、球団公式などで確認できた内容だけを書く。推測で書かない
- チケットの氏名・番号・座席の列や番号は書かない"""

# Issue ごとの範囲。記事が多い Issue は MAX_PER_CHAT 本ずつ（L1 とその L2 はまとめて）に分け、1チャット＝1パートにする。
MAX_PER_CHAT = 10
ISSUES = [
    dict(issue=2, title="カテゴリ1「野球ってそもそも？」", prio="最優先", cats="1", players=False, slug="basics",
         l1s="1-01 1-03 1-04 1-05 1-06 1-07 1-08 1-09",
         notes="- 1-01-d（延長戦）と 1-05-b（コールド）は🔍。2026年のNPBの規定を公式で確認できたときだけ書く\n- 1-01-c「今日は何時に終わりそう？」は 18:00 開始を前提に、平均的な試合時間を出典つきで"),
    dict(issue=3, title="カテゴリ2「打つ・投げる・守る」", prio="最優先", cats="2", players=True, slug="play",
         l1s="2-02 2-03 2-07 2-09 2-10 2-12",
         notes="- 2-03-b（海風とホームラン）は山口航輝・井上広大・清宮・万波を例に使える\n- 2-09 は今日の継投予想（ロッテのブルペン、福島蓮は短いイニングの予想）と結びつける"),
    dict(issue=4, title="カテゴリ4「数字・記録・スコアボード」", prio="高", cats="4", players=True, slug="numbers",
         l1s="4-01 4-02 4-06",
         notes="- 4-02（スタメン表の見方）は、添付の予想スタメン表を例に使う\n- 4-06-a（今日かかっている記録）は、今日の試合データの「今日かかっている記録・話題」だけを根拠にする"),
    dict(issue=5, title="カテゴリ5「今日の試合」", prio="高", cats="5", players=True, slug="today",
         l1s="5-01 5-02 5-03 5-04 5-05 5-06 5-07",
         notes="- 順位・ゲーム差・予告先発・記録は、今日の試合データにある数字だけを使う\n- 5-01-c は🔍。CS の開催地の決まり方を NPB 公式で確認できたときだけ書く\n- 5-06 は選手カードから要約する（清宮・山口・ジャクソン）\n- 5-07 と 5-07-a〜d は短くてよい。「上の『スタメン』から選手カードが見られます」と案内する"),
    dict(issue=10, title="カテゴリ7「ZOZOマリンスタジアム」", prio="高", cats="7", players=False, slug="stadium",
         l1s="7-04 7-06 7-07 7-08 7-09 7-10 7-11 7-01 7-02 7-03 7-05 7-12",
         notes="- 🔍が多い。イベント時刻・メニュー・持ち込み・再入場・傘・座席からの見え方・トイレは、マリーンズ球団公式・ZOZOマリンスタジアム公式で確認できたものだけを書く\n- 7-07 は 2026/9/28 当日のイベント。7-07-d の企画名は「2026 秋の夜空にみんなで叫ぼう！特別招待」\n- 7-11 の前提は 1塁側・内野指定席B・Cゲート（コアラゲート）・フロア4 まで。それ以上の座席情報は書かない\n- 7-08-a は天気予報「くもり時々雨」と夜の海風を踏まえる"),
    dict(issue=6, title="カテゴリ6「応援」", prio="中", cats="6", players=False, slug="cheer",
         l1s="6-01 6-02 6-03 6-04",
         notes="- 観戦席は1塁側（ロッテ側）の内野指定席B。6-01-a は内野席での応援への参加のしかたを中心に\n- 6-01-b（応援歌）と 6-04（マスコット）は🔍。歌詞の全文は載せない"),
    dict(issue=7, title="カテゴリ3「選手の頭の中」", prio="中", cats="3", players=True, slug="mind",
         l1s="3-01 3-02 3-03 3-04 3-05 3-06 3-07 3-08",
         notes="- 「今日の試合で見るなら」では選手カードの具体例を使う（例：3-08 はサブロー・新庄の起用、3-06-a は藤原・万波）"),
    dict(issue=8, title="カテゴリ1・2の残りとカテゴリ8", prio="低", cats="128", players=False, slug="rest",
         l1s="1-02 2-01 2-04 2-05 2-06 2-08 2-11 2-13 2-14 2-15 2-16 2-17 2-18 8-01 8-02",
         notes="- 2-16-a と 8-02-a は🔍"),
]


def parse_tree():
    """question-tree.md から {L1のID: (題, [(L2のID, 題), …])} を作る。"""
    tree, cur = {}, None
    for line in read("docs/question-tree.md").splitlines():
        m = re.match(r"^- \*\*(\d-\d\d) (.+?)\*\*(.*)$", line)
        if m:
            cur = m.group(1)
            tree[cur] = ((m.group(2) + m.group(3)).strip(), [])
            continue
        m = re.match(r"^  - (\d-\d\d-[a-z]) (.+)$", line)
        if m and cur:
            tree[cur][1].append((m.group(1), m.group(2).strip()))
    return tree


def balanced(items, size, n):
    """items を順番のまま n 個に分け、いちばん大きいパートができるだけ小さくなるようにする。"""
    best = {}

    def go(i, k):
        if k == 1:
            return sum(size[x] for x in items[i:]), [items[i:]]
        if (i, k) not in best:
            opts = []
            for j in range(i + 1, len(items) - k + 2):
                m, rest = go(j, k - 1)
                opts.append((max(sum(size[x] for x in items[i:j]), m), [items[i:j]] + rest))
            best[i, k] = min(opts, key=lambda o: o[0])
        return best[i, k]

    return go(0, min(n, len(items)))[1]


# どの Issue にも書かれていない L1（あとから疑問ツリーに足したものなど）を入れる Issue（カテゴリ番号 → Issue）
DEFAULT_ISSUE = {"1": 8, "2": 8, "3": 7, "4": 4, "5": 5, "6": 6, "7": 10, "8": 8}


def written_ids():
    """content/ にすでにある記事の ID（build_site.py と同じ読み方）。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_site import load_articles
    return set(load_articles())


def split_jobs():
    """まだ書かれていない記事だけを、Issue ごとに MAX_PER_CHAT 本前後のパートに分ける。"""
    tree, done, jobs = parse_tree(), written_ids(), []
    listed = {l1 for iss in ISSUES for l1 in iss["l1s"].split()}
    extra = {}
    for l1 in tree:
        if l1 not in listed:
            extra.setdefault(DEFAULT_ISSUE[l1[0]], []).append(l1)
    for iss in ISSUES:
        order = iss["l1s"].split() + extra.get(iss["issue"], [])
        todo = {l1: [x for x in [l1] + [c for c, _ in tree[l1][1]] if x not in done] for l1 in order}
        todo = {l1: ids for l1, ids in todo.items() if ids}
        if not todo:
            continue
        size = {l1: len(ids) for l1, ids in todo.items()}
        chunks = balanced(list(size), size, math.ceil(sum(size.values()) / MAX_PER_CHAT))
        for k, l1s in enumerate(chunks, 1):
            ids = [x for l1 in l1s for x in todo[l1]]
            lines = []
            for l1 in l1s:
                line = f"- {l1} {tree[l1][0]}" + ("" if l1 in ids else "（書き済み。書かない）")
                lines.append(line + "".join(f"\n  - {c} {t}" for c, t in tree[l1][1] if c in ids))
            # Issue の注意点のうち、このパートの ID に触れる行（と ID を含まない行）だけ残す
            notes = [n for n in iss["notes"].split("\n") if not re.search(r"\d-\d\d", n) or any(l1 in n for l1 in l1s)]
            jobs.append(dict(iss, part=f"{k}/{len(chunks)}", branch=f"content/{iss['issue']}-{iss['slug']}-{ids[0]}", ids=ids,
                             scope=f"次の {len(ids)} 本\n" + "\n".join(lines),
                             notes="\n".join(notes) or "- 特になし"))
    return jobs


def article_prompt(j):
    files = [attach("docs/content-template.md", read("docs/content-template.md")),
             attach("data/today.md"),
             attach("docs/question-tree.md（該当カテゴリの抜粋）", tree_section(j["cats"]))]
    if j["players"]:
        files.append(attach("data/players/README.md"))
        if j["issue"] == 5:
            files += [attach("data/players/managers.md"), attach("data/players/lotte.md"), attach("data/players/fighters.md")]
    return f"""あなたは、野球をまったく知らない初心者向けの観戦ガイドの記事を書くライターです。
2026年9月28日（月）18:00 からの ZOZOマリンスタジアム「千葉ロッテ×北海道日本ハム」を観に行く人が、球場の待ち時間にスマホで読みます。

# 今回書く範囲（GitHub Issue #{j['issue']}：{j['title']}　パート {j['part']}）
{j['scope']}

# この範囲の注意点
{j['notes']}

{COMMON_RULES}

{article_write_rules(j)}

# 添付資料
""" + "\n\n".join(files)


def players_prompt():
    return f"""あなたは、プロ野球の観戦用選手名鑑の編集者です。2026年9月28日（月）18:00 の「千葉ロッテ×北海道日本ハム」（ZOZOマリン）向けの名鑑を仕上げます。

# 今回やること（GitHub Issue #9）
1. 添付の data/players/fighters.md の空欄3セクション「スタメン候補」「ブルペン」「代打・代走」を埋める
   - まず NPB 公式「日本ハム 出場選手登録」で 9/28 時点の1軍登録を確認し、そこから選ぶ
   - 目安：スタメン候補＝進藤勇也、郡司裕也、大塚、奈良間大己、西川遥輝／ブルペン＝柳川大晟（抑え）、島本浩也、大川慈英、カストロほか主要な救援／代打・代走＝スタメン外の野手
   - 書式は添付 README.md の「カードの書式」どおり。ロッテ側（lotte.md）を見本に、同じ7項目・同じ口調・同じ長さで
   - 成績は 9/26 時点、直近の結果は 9/27 まで。「直近数試合」は 9/24・26・27 の3試合
   - 見つからない項目は「公開情報が見つかりませんでした」と書く
2. fighters.md 内の <!-- TODO: 確認 --> を出典で確認し、正しければコメントを消し、違えば直す

# 守ること
- 2026年の出来事はあなたの学習データより新しい場合がある。数字・出来事はウェブ検索で NPB・球団公式・主要紙から確認できたものだけ
- 確認できない記述は書かず、<!-- TODO: 確認 --> を残す

{players_write_rules()}

# 添付資料
{attach("data/players/README.md")}

{attach("data/players/lotte.md")}

{attach("data/players/fighters.md")}

{attach("data/today.md")}"""


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GPT プロンプト集</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--sub:#66666c;--line:#e0e0dc;--accent:#1d2d6b;--ok:#1a7f37}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}h1{font-size:1.4rem;margin:.3em 0}h2{font-size:1.15rem;margin:1.6em 0 .5em;border-left:4px solid var(--accent);padding-left:.5em}
a{color:var(--accent)}ol,ul{padding-left:1.3em}li{margin:.25em 0}code{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:0 4px;font-size:.88em;word-break:break-all}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.row h3{margin:0;font-size:1rem;flex:1;min-width:12em}
.tag{font-size:.75rem;border:1px solid var(--line);border-radius:999px;padding:1px 8px;color:var(--sub)}
button{font:inherit;font-size:.9rem;border:0;border-radius:8px;padding:8px 14px;background:var(--accent);color:var(--bg);cursor:pointer}
button.done{background:var(--ok)}details{margin-top:8px}summary{cursor:pointer;color:var(--sub);font-size:.85rem}
textarea{width:100%;height:220px;margin-top:6px;font:12px/1.5 ui-monospace,monospace;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px}
.small{font-size:.85rem;color:var(--sub)}
</style></head><body><main>
<h1>観戦ガイドの作業手順</h1>
<p class="small">2026/9/28 ロッテ×日本ハム観戦ガイド（<a href="REPO">BaQaz/guide</a>）。このページは main が更新されるたびに自動で作り直され、<strong>まだ書かれていない記事のプロンプトだけ</strong>が並びます。できることは ChatGPT で、ChatGPT ではできないことだけ Claude で行います。</p>
<p class="small">最新版を開く：<a href="https://baqaz.github.io/guide/docs/gpt-prompts.html">GitHub Pages</a>（Pages を有効にした後）。Pages を使わない場合は、Claude のプロジェクトで「プロンプト集を更新して」と送ると、いつものリンクが最新版になります。</p>

<h2>全体の流れ</h2>
<ol>
<li><strong>記事を書く</strong>（ChatGPT）… 下の「記事のプロンプト」を1本ずつ新しいチャットに送る。いま STATUS</li>
<li><strong>PR をマージする</strong>（ChatGPT）… 「PR をまとめてマージ」を送る。マージされると1〜2分でサイトとこのページが自動で作り直される</li>
<li><strong>疑問を増やす</strong>（ChatGPT）… 「疑問を増やす」を送る → できた PR を 2. と同じようにマージ → このページに新しい疑問の記事プロンプトが出るので 1. に戻る</li>
<li><strong>ファクトチェック</strong>（Claude・任意）… 「Claude に頼む」の文をコピーして、Claude のプロジェクトに送る</li>
<li><strong>推敲</strong>（Claude）… 記事がそろったら、hq-chat で文章を推敲してもらう。hq-chat は Claude のスキルなので ChatGPT ではできない</li>
<li><strong>公開して球場で使う</strong> … 下の「公開」と「球場で使う」</li>
</ol>

<h2>ChatGPT の準備（毎回）</h2>
<ul>
<li><strong>1プロンプトにつき新しいチャット</strong>を1つ。モデルは考える系（Thinking）、<strong>ウェブ検索</strong>と <strong>GitHub への書き込み</strong>（BaQaz/guide）を使える状態にする</li>
<li>書き込みの確認を求められたら許可する。途中で止まったら「続き」と送る（コミット済みの次から再開します）</li>
<li>急ぐときは、送るときに「ブランチは作らず main に直接コミットしてください。PR も不要です」と一言添えると、書いたそばから反映されます（レビューなし）</li>
</ul>

<h2>1. 記事のプロンプト（優先順）</h2>
CARDS

<h2>2. PR をまとめてマージ（ChatGPT）</h2>
TOOL_MERGE

<h2>3. 疑問を増やす（ChatGPT）</h2>
<p class="small">疑問ツリー（docs/question-tree.md）に新しい疑問を足す PR を作ります。1チャットで1回。マージすると、上の「記事のプロンプト」に新しい疑問の分が出ます。</p>
TOOL_MORE

<h2>4〜5. Claude に頼む</h2>
<p class="small">Claude のプロジェクト（ロッテ対日本ハム観戦ガイド続行）のチャットにコピーして送ります。</p>
TOOL_CLAUDE

<h2>6. 公開（GitHub Pages）</h2>
<ol>
<li>Settings → General → いちばん下の Danger Zone →「Change repository visibility」→「Make public」（無料プランでは Pages に必要。リポジトリの中身は誰でも見られるようになる）</li>
<li>Settings → Pages →「Source」を「Deploy from a branch」、Branch を「main」「/ (root)」にして Save</li>
<li>1〜2分後、サイトは <a href="https://baqaz.github.io/guide/site/">baqaz.github.io/guide/site/</a>、このページは <a href="https://baqaz.github.io/guide/docs/gpt-prompts.html">baqaz.github.io/guide/docs/gpt-prompts.html</a> で開けます。マージのたびに自動で最新になるので、ダウンロードは不要です</li>
</ol>
<p class="small">スマホで GitHub の Settings が見当たらないときは、ブラウザのメニューで「デスクトップ用サイト」に切り替えます。</p>

<h2>7. 球場で使う</h2>
<ul>
<li><strong>トップ</strong>：速報ボード（スコア・B/S/O・塁）とスタメン。ランプと塁はタップで変えられます</li>
<li><strong>写真で更新</strong>：速報ボードの「写真からスコアとスタメンを更新」→ プロンプトをコピー → ChatGPT に<strong>写真と一緒に</strong>送る → 返ってきたコードブロックの中身を貼って「反映」。この更新はその端末のブラウザの中だけに保存されます</li>
<li><strong>もっと知りたいとき</strong>：記事の見出しごとの「GPTに聞く」でプロンプトがコピーされるので、ChatGPT に貼るだけ</li>
<li>電波が弱いことがあるので、試合前に一度開いてタブを残しておく</li>
</ul>
</main>
<script>
document.querySelectorAll('button[data-copy]').forEach(b=>b.onclick=async()=>{
  const ta=document.getElementById(b.dataset.copy);
  try{await navigator.clipboard.writeText(ta.value)}catch(e){ta.parentElement.open=true;ta.select();document.execCommand('copy')}
  b.textContent='コピーしました';b.classList.add('done');setTimeout(()=>{b.textContent='コピー';b.classList.remove('done')},2000);
});
</script>
</body></html>"""


def card(i, issue, title, prio, prompt):
    return f"""<div class="card"><div class="row"><h3>{i + 1}. #{issue} {html.escape(title)}</h3><span class="tag">{prio}</span>
<button data-copy="p{i}">コピー</button></div>
<div class="small">{len(prompt):,} 文字 ・ <a href="{REPO}/issues/{issue}">Issue #{issue}</a></div>
<details><summary>中身を見る</summary><textarea id="p{i}" readonly>{html.escape(prompt)}</textarea></details></div>"""


MERGE_PROMPT = f"""GitHub のリポジトリ BaQaz/guide の、open なプルリクエストを確認してマージしてください。あなたはこのリポジトリに書き込めます。

# 対象
- ブランチ名が `content/` で始まる open な PR すべて（番号の小さい順）

# マージしてよい条件（すべて満たすもの）
- 変更したファイルが `content/` の下の .md だけ（ブランチ `content/9-…` は `data/players/fighters.md` だけ、ブランチ `content/tree-…` は `docs/question-tree.md` だけ）
- 記事ファイルの先頭に front matter（--- で囲む）があり、`id` がファイル名と同じ
- 本文に ``` のコードブロックや `=== FILE:` の区切りが入っていない
- main と衝突（conflict）していない

# やること
1. 条件を満たす PR は、merge commit でマージする（squash や rebase ではなく）
2. 条件を満たさない PR はマージせず、何が足りないかを PR にコメントで書く。直せるものはそのブランチで直してからマージしてよい
3. 最後に、チャットに「マージした PR」「マージしなかった PR と理由」の一覧を短く返す"""

MORE_PROMPT = lambda: f"""あなたは、野球をまったく知らない初心者向けの観戦ガイドの編集者です。2026年9月28日（月）18:00 の「千葉ロッテ×北海道日本ハム」（ZOZOマリン）を観に行く人が、球場で「これ何？」と思ったときに押すボタン（疑問）を増やします。

# 今の疑問ツリー
添付の docs/question-tree.md です。L1＝ガイドのページに並ぶボタン（読み手がそのまま口にする疑問）、L2＝L1 の記事の最後に出る「さらに気になる？」のボタン（L1 を読んで次に湧く疑問）です。
サイトでは、カテゴリ1〜4と8が「野球初心者ガイド」、5と6が「ロッテ対日本ハムを楽しむガイド」、7が「マリーンズスタジアムガイド」に並びます。

# やること
1. main から新しいブランチ `content/tree-more` を作る（あれば続けて使う）
2. docs/question-tree.md に疑問を足してコミットする。カテゴリを1つ足し終えるごとにコミットする
   - 目標：全体で100個前後を追加。L2 が2個以下の L1 には L2 を足して3〜5個にする。各カテゴリに、まだない L1 を3〜6個足す
   - 球場で本当に浮かぶ疑問を優先する（例：ビジョンの表示、審判のジェスチャー、投手交代の間に何が起きているか、ヤジや応援の決まり、座席・売店・天気）
   - 書式は今と同じにする。L1 は `- **カテゴリ番号-連番 疑問**`、L2 はその下に2スペース下げて `  - L1のID-a 疑問`。今日の観戦で特に役立つ L1 は疑問の前に `★ `、公式情報の確認が必要なものは疑問の後に `🔍`
   - 既存の ID・疑問の文は変えない、消さない。ID は各カテゴリの続き番号にする（L2 は -a, -b… の続き）
   - ファイル末尾の「集計」があれば数を更新する
3. 全部終えたら `content/tree-more` から main へのプルリクエストを作る。タイトルは「疑問を追加」、本文に追加した疑問の数（カテゴリ別）
4. チャットには、追加した数と PR の URL だけを返す

# 添付資料
{attach("docs/question-tree.md")}"""

CLAUDE_TEXT = """【ファクトチェック】BaQaz/guide の open な記事 PR（または次の PR：＿＿）を、docs/handoff.md の「ファクトチェックの基準」で確認してください。数字・日付・記録を出典で確かめ、間違いは同じブランチで直してください。push とマージは確認なしで進めてかまいません。

【推敲】BaQaz/guide の content/ の記事を、hq-chat（natural-japanese）の進め方で推敲してください。docs/content-template.md の口調（15歳向け、淡々と筋道立ててやさしく、「あなた」「〜なのだ」「〜というわけだ」）と具体性（数字・選手名・理屈・出典）は保ち、事実は変えないでください。カテゴリごとに1つの PR にして、push・PR・マージは確認なしで進めてかまいません。

【プロンプト集の更新】プロンプト集とサイトのリンクを最新版に更新してください。"""


def tool(i, title, prompt, note=""):
    return f"""<div class="card"><div class="row"><h3>{html.escape(title)}</h3><button data-copy="t{i}">コピー</button></div>
{f'<div class="small">{note}</div>' if note else ''}<details><summary>中身を見る</summary><textarea id="t{i}" readonly>{html.escape(prompt)}</textarea></details></div>"""


def players_done():
    return len(re.findall(r"^## ", read("data/players/fighters.md"), re.M)) >= 15


def main():
    cards = []
    jobs = split_jobs()
    k = next((i + 1 for i in range(len(jobs) - 1, -1, -1) if jobs[i]["issue"] <= 5), 0)
    order = jobs[:k] + ([] if players_done() else [None]) + jobs[k:]  # None = 選手カード（#9）
    for i, j in enumerate(order):
        if j is None:
            cards.append(card(i, 9, "日本ハムの選手カード（候補・ブルペン・代打代走）", "高", players_prompt()))
        else:
            head = f"{j['title']}（{j['part']}）{' '.join(x for x in j['ids'] if x.count('-') == 1)}"
            cards.append(card(i, j["issue"], head, j["prio"], article_prompt(j)))
    n = sum(len(j["ids"]) for j in jobs)
    status = f"残り {n} 本・{len(cards)} チャット。" if cards else "書かれていない記事はありません。"
    out = (PAGE.replace("REPO", REPO).replace("STATUS", status)
           .replace("CARDS", "\n".join(cards) or '<p class="small">いまは書く記事がありません。3. で疑問を増やせます。</p>')
           .replace("TOOL_MERGE", tool(0, "PR をまとめてマージ", MERGE_PROMPT, "ChatGPT に送ると、記事の PR を確認してマージします。記事を書き終えるたびに何度送ってもかまいません"))
           .replace("TOOL_MORE", tool(1, "疑問を増やす", MORE_PROMPT()))
           .replace("TOOL_CLAUDE", tool(2, "Claude に頼む（必要な段落だけ送る）", CLAUDE_TEXT)))
    (ROOT / "docs/gpt-prompts.html").write_text(out, encoding="utf-8")
    print(f"docs/gpt-prompts.html: プロンプト {len(cards)} 件（残り {n} 本）")


if __name__ == "__main__":
    main()
