import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string().max(45),
    description: z.string().max(160),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    cluster: z.enum(['accident', 'repair', 'insurance', 'vintage', 'trend']),
    articleType: z.enum(['trend', 'search-intent', 'first-party']),
    keywords: z.array(z.string()),
    heroImage: z.string().optional(),
    heroAlt: z.string().optional(),
    faqs: z
      .array(z.object({ q: z.string(), a: z.string() }))
      .min(3)
      .max(8),
    sources: z.array(z.object({ label: z.string(), url: z.string().url() })).optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
