import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://aitoolsnav.net',
  output: 'static',
  build: {
    assets: '_assets',
  },
});
