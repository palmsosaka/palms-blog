import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 現在: GitHub Pages(間借りURL)運用。
// 独自ドメイン取得後は site を独自ドメインに変え、base を削除する(README_SETUP.md 手順3)
export const SITE_URL = 'https://palmsosaka.github.io';

export default defineConfig({
  site: SITE_URL,
  base: '/palms-blog',
  integrations: [sitemap()],
  build: { format: 'directory' },
});
