import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

// Set SITE_URL in your host's environment once the domain is live.
export default defineConfig({
  site: process.env.SITE_URL || 'https://brockintonlandmanagement.com',
  integrations: [react(), sitemap()],
  build: { inlineStylesheets: 'auto' },
  vite: {
    build: { chunkSizeWarningLimit: 1200 },
    ssr: { noExternal: ['three'] },
  },
});
