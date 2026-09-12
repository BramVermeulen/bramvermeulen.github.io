// @ts-check
import { defineConfig } from 'astro/config';

import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://bramvermeulen.github.io',
  // Every page is generated from the same commit, so one build-time timestamp
  // is the honest <lastmod> for all of them.
  integrations: [sitemap({ lastmod: new Date() })],

  vite: {
    plugins: [tailwindcss()],
  },
});
