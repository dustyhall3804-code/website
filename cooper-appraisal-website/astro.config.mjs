import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';

// TODO: replace with the real production domain before launch.
// This value drives canonical URLs, Open Graph tags, and the sitemap.
const SITE_URL = 'https://www.example.com';

export default defineConfig({
  site: SITE_URL,
  integrations: [sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
