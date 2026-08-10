# セットアップ手順(初回のみ・約30分)

このリポジトリは「収集→採否→執筆→検証→下書きPR」まで毎朝自動で動き、
**だいちさんがPRをマージした記事だけが公開される**仕組みです。

## 手順1: GitHubリポジトリ作成とpush

```bash
cd palms-blog
git init && git add -A && git commit -m "initial: blog automation system"
gh repo create palms-blog --private --source=. --push
```

## 手順2: GitHub Pages有効化

リポジトリの Settings → Pages → Source を「GitHub Actions」にする。

## 手順3: ドメイン設定(推奨)

1. 独自ドメインを取得(例: palms-lab.com)
2. 以下の3ファイルの `palms-blog.example.com` を実ドメインに置換:
   - `astro.config.mjs`
   - `scripts/update-llms-txt.mjs`
   - `public/robots.txt`
   - `.github/workflows/deploy.yml`(SITE変数)
3. Settings → Pages → Custom domain に設定

※独自ドメインなしでも `palmsosaka.github.io/palms-blog` で動作します(その場合も上記置換は必要)。

## 手順4: Secrets設定

Settings → Secrets and variables → Actions で登録:

| Secret | 必須 | 内容 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Anthropic APIキー(編集部パイプライン用) |
| `YOUTUBE_API_KEY` | 任意 | YouTube Data API v3キー(無料枠)。未設定ならYouTube収集をスキップ |
| `INDEXNOW_KEY` | 任意 | IndexNow用キー(下記手順6) |

## 手順5: 動作確認

1. Actions → `collect-and-draft` → Run workflow を手動実行
2. 数分後、下書きPRができていることを確認
3. PRの本文(ファクトチェック結果・【要確認】箇所)を見て、修正指示があればPRコメントで指示
4. マージ → 自動で公開される

## 手順6: IndexNow(任意・公開後のインデックス促進)

1. 任意の32文字hexキーを生成: `openssl rand -hex 16`
2. `public/<キー>.txt` というファイルを作り、中身にキー自体を書く
3. Secretsに `INDEXNOW_KEY` として登録

## 手順7: Google Search Console / GA4

1. GSCにサイトを登録し、sitemap(`/sitemap-index.xml`)を送信
2. GA4プロパティを作成(タグの設置は今後の改善で対応可)

## 日常運用(だいちさんの作業は1日5〜10分)

- 毎朝6時: 自動で収集→執筆→PR作成(0〜2本)
- スマホのGitHubアプリでPRを確認 → 【要確認】箇所を実数に直す指示 or 自分で編集 → マージ
- 毎週月曜: 自動で週次レポートissueが立つ → Cowork(FABLE)に貼って30分の分析セッション
  → CLAUDE.md / scoring-weights.json / keyword-map.md の更新をコミット

## 運用上の注意

- **自動マージは絶対に設定しない**(スパム判定回避の生命線)
- 週5本ペースを超えない
- 検索アルゴリズム・各プラットフォームの仕様は変わるため、月1回は
  Google Search Central のポリシー更新を確認する
- claude-code-action のバージョン・記法は更新されることがあるため、初回実行でエラーが出たら
  https://github.com/anthropics/claude-code-action の最新READMEを確認する
