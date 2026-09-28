# はじめての野球観戦ガイド（2026/9/28 ロッテ×日本ハム版）

野球をほとんど知らない人が、球場の待ち時間にスマホで読むための読み物サイトです。
トップの「疑問ボタン」を押すと答えの記事が開きます。記事の下には「さらに気になる？」の派生ボタンがあり、2階層までたどれます。

## 構成

```
docs/
  question-tree.md     疑問ボタンの一覧（ID・階層・優先度）← 仕様の中心
  content-template.md  記事の書き方とテンプレート
  handoff.md           Claude / GPT の分担と受け渡しルール
data/
  today.md             今日の試合の前提情報（順位・先発・記録）
  players/             選手・監督カード（7項目）。README.md に書式と予想スタメン
content/
  1/ … 8/              記事本体（1問＝1ファイル、ID名）
site/index.html        表示用のサイト（1ファイル。scripts/build_site.py で生成。main への push で自動更新）
scripts/               サイトとプロンプト集を作るスクリプト
docs/gpt-prompts.html  ChatGPT に貼るプロンプト集と、PR の確認・共有のしかた（ブラウザで開く）
```

## GPT で作業するには
`docs/gpt-prompts.html` をダウンロードしてブラウザで開き、プロンプトをコピーして ChatGPT に送る。ChatGPT がリポジトリに1記事ずつ直接コミットして PR を作るので、出力を手で貼る必要はない。

## 進め方
1. `docs/question-tree.md` で疑問を確定する（済）
2. カテゴリごとに Issue を立て、GPT が記事を書いて PR を出す（今ここ。Issue #1〜#10）
3. Claude がファクトチェックとレビューをしてマージする
4. サイトを組んで公開し、スマホで開けるようにする

詳しくは `docs/handoff.md` を参照してください。
