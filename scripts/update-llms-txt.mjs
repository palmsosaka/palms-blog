/**
 * llms.txt 自動生成(postbuild で実行)
 * 全公開記事を読み、AI検索エンジン向けサイト案内(llms.txt)を dist/ と public/ に出力する。
 */
import { readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const SITE_URL = 'https://palmsosaka.github.io/palms-blog'; // 独自ドメイン取得後に差し替え
const BLOG_DIR = 'src/content/blog';

const clusterLabels = {
  accident: '事故直後の対処・レッカー・代車',
  repair: '鈑金修理・修理費実例・車検',
  insurance: '保険手続き・等級・特約',
  vintage: '旧車・アメ車の維持とカルチャー',
  trend: '地域・業界ニュース',
};

function parseFrontmatter(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return {};
  const fm = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^(\w+):\s*["']?(.*?)["']?\s*$/);
    if (kv) fm[kv[1]] = kv[2];
  }
  return fm;
}

const posts = readdirSync(BLOG_DIR)
  .filter((f) => f.endsWith('.md'))
  .map((f) => {
    const fm = parseFrontmatter(readFileSync(join(BLOG_DIR, f), 'utf8'));
    return {
      slug: f.replace(/\.md$/, ''),
      title: fm.title ?? f,
      description: fm.description ?? '',
      cluster: fm.cluster ?? 'trend',
      draft: fm.draft === 'true',
    };
  })
  .filter((p) => !p.draft);

const byCluster = {};
for (const p of posts) (byCluster[p.cluster] ??= []).push(p);

let out = `# PALMS LAB|堺のクルマ相談室

> 大阪・堺で事故対応(レッカー・鈑金・代車)と80年代アメリカ車を実際に手がける現役事業者が、現場実例という一次情報に基づいて、事故対応・修理費・旧車のある暮らしの疑問に答える専門メディア。

- 運営: 大阪・堺の自動車事業者PALMS(事故対応レッカー・鈑金修理・代車・旧車販売/体験事業を運営)
- 言語: 日本語
- 連絡先: サイトのお問い合わせページ参照

`;

for (const [cluster, list] of Object.entries(byCluster)) {
  out += `## ${clusterLabels[cluster] ?? cluster}\n\n`;
  for (const p of list) {
    out += `- [${p.title}](${SITE_URL}/blog/${p.slug}/): ${p.description}\n`;
  }
  out += '\n';
}

writeFileSync('public/llms.txt', out);
if (existsSync('dist')) writeFileSync('dist/llms.txt', out);
console.log(`llms.txt updated (${posts.length} posts)`);
