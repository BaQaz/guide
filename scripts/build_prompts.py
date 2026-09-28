#!/usr/bin/env python3
"""ChatGPT に貼るプロンプト集 docs/gpt-prompts.html を作る。

使い方: python3 scripts/build_prompts.py
仕様ファイル（テンプレート・今日のデータ・疑問ツリー・選手カード）をプロンプトに埋め込むので、
仕様を変えたら作り直す。
"""
import html
import re
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


BRANCH_NAMES = {2: "basics", 3: "play", 4: "numbers", 5: "today", 6: "cheer", 7: "mind", 8: "rest", 9: "fighters", 10: "stadium"}


def write_rules(issue, what):
    """GPT がリポジトリに直接書き込むための手順。長い出力がチャットで圧縮されないよう、1件ごとにコミットさせる。"""
    branch = f"content/{issue}-{BRANCH_NAMES[issue]}"
    return f"""# 書き込みのしかた（厳守）
あなたは GitHub のリポジトリ BaQaz/guide に書き込めます。チャットに本文を出すのではなく、リポジトリに直接コミットしてください。
1. main から新しいブランチ `{branch}` を作る（すでにあれば、そのブランチに続けて書く）
2. {what}
3. 全部書き終えたら、`{branch}` から main へのプルリクエストを作る。タイトルは Issue #{issue} と同じ、本文の1行目に `Closes #{issue}`、続けて：書いたもの（記事IDまたは選手名）の一覧／needs_check: true にしたIDと理由／使った出典URLの一覧
4. チャットには、コミットしたファイルの一覧とPRのURLだけを短く返す（本文をチャットに貼らない）
- 途中で止まったときは「どこまでコミットしたか」を書いて止まり、「続き」と送られたら次のファイルから再開する。同じファイルを二重に作らない
- 書き込めなかったときは、エラーの内容をそのまま伝えて止まる（チャットに全文を貼る方式に切り替えない）"""


def article_write_rules(issue):
    return write_rules(issue, """記事は1つ書くごとに、1記事＝1ファイルで、すぐにコミットする（まとめて書いてから一度にコミットしない）
   - パス：`content/<カテゴリ番号>/<ID>.md`（例：`content/1/1-07.md`、`content/1/1-07-a.md`）
   - 中身：テンプレートどおりの front matter（--- で囲む）と本文だけ。コードブロックや `=== FILE: … ===` の区切りは入れない
   - コミットメッセージ：`<ID> <疑問の文> (#Issue番号)`""")


def players_write_rules():
    return write_rules(9, """data/players/fighters.md を直接編集してコミットする。選手を1人（またはセクション1つ）書き足すごとにコミットする（全部書いてから一度にコミットしない）
   - 毎回、ブランチ上の最新の fighters.md を読んでから追記する。既存の先発・スタメン部分は消さない
   - コミットメッセージ：`日本ハム <選手名またはセクション名> を追加 (#9)`""")


COMMON_RULES = """# 守ること
- 添付の「記事テンプレート」の型・字数・書き方ルールに必ず従う。読み手は野球をほぼ知らない大人で、球場の待ち時間にスマホで1〜2分で読む
- 「今日の試合で見るなら」は必須。添付の「今日の試合データ」「選手カード」にある具体的な選手名・場面で書く
- 2026年の出来事はあなたの学習データより新しい場合がある。今日の試合・2026年シーズンの数字や出来事は、添付データにあるものか、ウェブ検索で NPB・球団公式・主要紙から確認できたものだけを使い、front matter の sources に URL を書く
- 確認できない内容は書かない。確認が必要な記述が残る記事は needs_check: true にし、該当箇所に <!-- TODO: 確認 --> を残す
- 🔍 がついた疑問は、球団公式などで確認できた内容だけを書く。推測で書かない
- チケットの氏名・番号・座席の列や番号は書かない"""

JOBS = [
    dict(issue=2, title="カテゴリ1「野球ってそもそも？」の★", prio="最優先", cats="1", players=False,
         scope="カテゴリ1のうち ★ がついた L1（1-01, 1-03, 1-04, 1-05, 1-06, 1-07, 1-08, 1-09）と、その下の L2 をすべて",
         notes="- 1-01-d（延長戦）と 1-05-b（コールド）は🔍。2026年のNPBの規定を公式で確認できたときだけ書く\n- 1-01-c「今日は何時に終わりそう？」は 18:00 開始を前提に、平均的な試合時間を出典つきで"),
    dict(issue=3, title="カテゴリ2「打つ・投げる・守る」の★", prio="最優先", cats="2", players=True,
         scope="カテゴリ2のうち ★ がついた L1（2-02, 2-03, 2-07, 2-09, 2-10, 2-12）と、その下の L2 をすべて",
         notes="- 2-03-b（海風とホームラン）は山口航輝・井上広大・清宮・万波を例に使える\n- 2-09 は今日の継投予想（ロッテのブルペン、福島蓮は短いイニングの予想）と結びつける"),
    dict(issue=4, title="カテゴリ4「数字・記録・スコアボード」の★", prio="高", cats="4", players=True,
         scope="カテゴリ4のうち ★ がついた L1（4-01, 4-02, 4-06）と、その下の L2 をすべて",
         notes="- 4-02（スタメン表の見方）は、添付の予想スタメン表を例に使う\n- 4-06-a（今日かかっている記録）は、今日の試合データの「今日かかっている記録・話題」だけを根拠にする"),
    dict(issue=5, title="カテゴリ5「今日の試合」5-01〜5-07", prio="高", cats="5", players=True,
         scope="カテゴリ5の 5-01〜5-07 の L1 と L2 すべて（5-08 は不要）",
         notes="- 順位・ゲーム差・予告先発・記録は、今日の試合データにある数字だけを使う\n- 5-01-c は🔍。CS の開催地の決まり方を NPB 公式で確認できたときだけ書く\n- 5-06 は選手カードから要約する（清宮・山口・ジャクソン）\n- 5-07 と 5-07-a〜d は短くてよい。「上の『スタメン』から選手カードが見られます」と案内する"),
    dict(issue=10, title="カテゴリ7「ZOZOマリンスタジアム」", prio="高", cats="7", players=False,
         scope="カテゴリ7（7-01〜7-12）の L1 と L2 すべて。★（7-04, 7-06, 7-07, 7-08, 7-09, 7-10, 7-11）を先に",
         notes="- 🔍が多い。イベント時刻・メニュー・持ち込み・再入場・傘・座席からの見え方・トイレは、マリーンズ球団公式・ZOZOマリンスタジアム公式で確認できたものだけを書く\n- 7-07 は 2026/9/28 当日のイベント。7-07-d の企画名は「2026 秋の夜空にみんなで叫ぼう！特別招待」\n- 7-11 の前提は 1塁側・内野指定席B・Cゲート（コアラゲート）・フロア4 まで。それ以上の座席情報は書かない\n- 7-08-a は天気予報「くもり時々雨」と夜の海風を踏まえる"),
    dict(issue=6, title="カテゴリ6「応援」", prio="中", cats="6", players=False,
         scope="カテゴリ6（6-01〜6-04）の L1 と L2 すべて",
         notes="- 観戦席は1塁側（ロッテ側）の内野指定席B。6-01-a は内野席での応援への参加のしかたを中心に\n- 6-01-b（応援歌）と 6-04（マスコット）は🔍。歌詞の全文は載せない"),
    dict(issue=7, title="カテゴリ3「選手の頭の中」", prio="中", cats="3", players=True,
         scope="カテゴリ3（3-01〜3-08）の L1 と L2 すべて",
         notes="- 「今日の試合で見るなら」では選手カードの具体例を使う（例：3-08 はサブロー・新庄の起用、3-06-a は藤原・万波）"),
    dict(issue=8, title="カテゴリ2の残り・カテゴリ8", prio="低", cats="28", players=False,
         scope="カテゴリ2のうち ★ がない L1（2-01, 2-04, 2-05, 2-06, 2-08, 2-11, 2-13〜2-18）とその L2、カテゴリ8（8-01, 8-02）とその L2",
         notes="- 2-16-a と 8-02-a は🔍"),
]


def article_prompt(j):
    files = [attach("docs/content-template.md", read("docs/content-template.md")),
             attach("data/today.md"),
             attach("docs/question-tree.md（該当カテゴリの抜粋）", tree_section(j["cats"]))]
    if j["players"]:
        files.append(attach("data/players/README.md"))
        if j["issue"] == 5:
            files += [attach("data/players/managers.md"), attach("data/players/lotte.md"), attach("data/players/fighters.md")]
    return f"""あなたは、野球をほとんど知らない大人向けの観戦ガイドの記事を書くライターです。
2026年9月28日（月）18:00 からの ZOZOマリンスタジアム「千葉ロッテ×北海道日本ハム」を観に行く人が、球場の待ち時間にスマホで読みます。

# 今回書く範囲（GitHub Issue #{j['issue']}：{j['title']}）
{j['scope']}

# この範囲の注意点
{j['notes']}

{COMMON_RULES}

{article_write_rules(j['issue'])}

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
@media (prefers-color-scheme: dark){:root{--bg:#111214;--card:#1c1d21;--ink:#ececef;--sub:#a0a0a8;--line:#2e2f35;--accent:#9fb2ff;--ok:#56d364}}
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
<h1>ChatGPT に記事を書いてもらう手順</h1>
<p class="small">2026/9/28 ロッテ×日本ハム観戦ガイド（<a href="REPO">BaQaz/guide</a>）。各プロンプトには仕様・今日のデータ・選手カードが埋め込み済みなので、そのまま貼るだけで動きます。</p>

<h2>1. ChatGPT に送る</h2>
<ol>
<li>ChatGPT で<strong>新しいチャット</strong>を開く（1 Issue につき 1チャット）。モデルは考える系（Thinking）を選び、<strong>ウェブ検索</strong>と <strong>GitHub への書き込み</strong>（BaQaz/guide）を使える状態にする</li>
<li>下の「コピー」を押して、そのまま貼って送る</li>
<li>ChatGPT が Issue ごとのブランチ（例：<code>content/2-basics</code>）を作り、<strong>記事を1つ書くたびにコミット</strong>します。1件ずつ書き込むので、長い出力がチャットで省略・圧縮される心配がありません。本文をコピーして貼る作業はいりません</li>
<li>途中で止まったら「続き」と送る（コミット済みの次から再開します）。書き込みの確認を求められたら許可する</li>
</ol>

<h2>2. PR を確認してマージする（スマホのブラウザでも可）</h2>
<ol>
<li>書き終わると ChatGPT が PR を作り、URL を返します（<a href="REPO/pulls">PR の一覧</a>からも開けます）</li>
<li>PR の中身をざっと見て（出典URLがあるか、needs_check の箇所）、「Merge pull request」。Claude にファクトチェックを頼む場合は、マージ前に PR の URL を渡す</li>
</ol>
<p class="small">急ぐときは、プロンプトを送るときに「ブランチは作らず main に直接コミットしてください。PR も不要です」と一言添えれば、書いたそばからサイトに反映されます（レビューなし）。</p>
<p class="small">ChatGPT が書き込めなかったときだけ、手で入れます：<a href="REPO/new/main">Add file → Create new file</a> で <code>content/gpt/issue-番号.md</code> を作り、出力を貼る（<code>=== FILE: … ===</code> 区切りのまとめ書きも読めます）。</p>

<h2>3. プロンプト（優先順）</h2>
CARDS

<h2>4. サイト（HTML）にして共有する</h2>
<p>main にマージされるたびに、GitHub Actions「サイトを組み立てる」が <code>site/index.html</code> を自動で作り直してコミットします（1〜2分）。このファイル1つで全ページが動き、ネットにつながらなくても読めます。</p>
<ol>
<li><strong>ファイルを取る</strong>：<a href="REPO/blob/main/site/index.html">site/index.html</a> を開き、右上の「…」または ⤓（Download raw file）で保存する</li>
<li><strong>自分のスマホで読む（いちばん確実）</strong>：保存した index.html を AirDrop・LINE の Keep・メールなどでスマホに送り、「ファイル」アプリから開く（iPhone は共有→Safari で開く）。球場の電波が弱くても読めます</li>
<li><strong>URL で人に共有する</strong>：<a href="https://app.netlify.com/drop">Netlify Drop</a> を開いて index.html をドラッグ＆ドロップすると、すぐに URL が発行されます。この URL は誰でも開けるので、席の情報（1塁側・内野指定席B・Cゲート）が含まれる点に注意してください。1時間で消えるので、残したい場合は無料アカウントを作って「Claim」します</li>
</ol>
<p class="small">GitHub Pages は、無料プランでは公開リポジトリでしか使えません。リポジトリを非公開のままにするなら、上の方法を使ってください。</p>
<p class="small">記事がまだ少なくても動きます。書かれていない疑問は「準備中」と表示されます。</p>

<h2>5. 球場でサイトを使う</h2>
<ul>
<li><strong>もっと詳しく知りたいとき</strong>：記事の見出しごと・選手カードごとに「📋 GPTで深掘り」ボタンがあります。押すとその部分の本文入りのプロンプトがコピーされるので、ChatGPT に貼るだけで聞けます。まだ書かれていない疑問（準備中）には「📋 GPTに聞く」ボタンがあります</li>
<li><strong>スタメン・スコアを写真で更新</strong>：上部の「ライブ」を開き、「写真読み取りプロンプトをコピー」→ ChatGPT に<strong>写真と一緒に</strong>送る → 返ってきたコードブロックの中身を貼って「反映」。スタメン表が実際の並びに変わり、トップにスコアが出ます。カードがない選手には「📋 GPT」ボタンが付き、7項目のカードを GPT に作ってもらえます</li>
<li>写真からの更新は、その端末のそのブラウザの中だけに保存されます（リポジトリは変わりません）。同行者のスマホには、それぞれで貼ってください</li>
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
    return f"""<div class="card"><div class="row"><h3>#{issue} {html.escape(title)}</h3><span class="tag">{prio}</span>
<button data-copy="p{i}">コピー</button></div>
<div class="small">{len(prompt):,} 文字 ・ <a href="{REPO}/issues/{issue}">Issue #{issue}</a></div>
<details><summary>中身を見る</summary><textarea id="p{i}" readonly>{html.escape(prompt)}</textarea></details></div>"""


def main():
    cards = []
    order = JOBS[:4] + [None] + JOBS[4:]  # None = 選手カード（#9）
    for i, j in enumerate(order):
        if j is None:
            cards.append(card(i, 9, "日本ハムの選手カード（候補・ブルペン・代打代走）", "高", players_prompt()))
        else:
            cards.append(card(i, j["issue"], j["title"], j["prio"], article_prompt(j)))
    out = PAGE.replace("REPO", REPO).replace("CARDS", "\n".join(cards))
    (ROOT / "docs/gpt-prompts.html").write_text(out, encoding="utf-8")
    print(f"docs/gpt-prompts.html: プロンプト {len(cards)} 件")


if __name__ == "__main__":
    main()
