# Cooper Appraisal Company — Website

A premium marketing site for Cooper Appraisal Company (Greenbrier, AR), built with
[Astro](https://astro.build) and [Tailwind CSS v4](https://tailwindcss.com).

## Status: Phase 1 — Design system + Home page

This delivery includes the full design system (colors, type, spacing, components) and a
complete Home page. The remaining pages (Commercial, Residential, House Measuring, About,
Contact) are scaffolded in the site structure (nav/footer links) but not yet built — they'll
follow once the Home page look is approved.

## Getting started

Requires Node.js 18.17+ (Node 20/22 recommended).

```bash
npm install
npm run dev
```

Then open http://localhost:4321.

### Other commands

| Command           | Action                                      |
| ------------------ | -------------------------------------------- |
| `npm run dev`       | Start the local dev server                    |
| `npm run build`     | Build the production site to `./dist/`        |
| `npm run preview`   | Preview the production build locally          |

## Project structure

```
src/
  components/     Button, Section, Card, Nav, Footer, PlaceholderImage
  data/site.ts     Business info + placeholder tokens + nav links
  layouts/Layout.astro   Page shell: <head>, SEO meta, JSON-LD, Nav/Footer
  pages/index.astro      Home page
  styles/global.css      Tailwind import + design tokens (@theme) + base styles
public/            Static assets (favicon, robots.txt)
```

## Design system

- **Type**: Fraunces (variable serif) for headings, Inter (variable sans) for body text.
  Both are self-hosted via `@fontsource-variable/*` — no external font requests.
- **Color**: `navy` (anchor, deep navy/charcoal), `cream` (warm off-white neutrals), `brass`
  (single restrained gold accent). Defined as Tailwind v4 theme tokens in
  `src/styles/global.css` — see the `@theme` block. All text/background pairings in the
  Home page were checked against WCAG AA contrast.
- **Components**: `Button` (primary/accent/outline/outlineLight/ghost variants), `Section`
  (consistent section padding + tone + max-width), `Card`, `Nav` (fixed, condenses on
  scroll, accessible mobile menu), `Footer`.
- **Motion**: subtle scroll-reveal via `data-reveal` attributes + `IntersectionObserver`.
  Progressive enhancement only — content is never hidden if JS fails or
  `prefers-reduced-motion: reduce` is set.

## Placeholders to fill in before launch

Real contact info, credentials, and testimonials were intentionally **not** invented. Search
the project for these tokens (mainly in `src/data/site.ts`) and replace them:

- `{{PHONE}}` / `{{PHONE_E164}}` — business phone (display + `tel:` link format)
- `{{EMAIL}}` — business email
- `{{APPRAISER_NAME}}` — appraiser's full name
- `{{LICENSE_NUMBER}}` — Arkansas appraiser license number
- `{{STREET_ADDRESS}}` / `{{POSTAL_CODE}}` — mailing/office address
- `{{BUSINESS_HOURS}}` — hours of operation
- `{{YEARS_IN_BUSINESS}}` — years in business (hero trust line)
- `{{TURNAROUND_TIME}}` / `{{SCHEDULING_WINDOW}}` — typical report turnaround and
  scheduling lead time
- `{{LATITUDE}}` / `{{LONGITUDE}}` — geocoordinates for the LocalBusiness schema
  (`src/layouts/Layout.astro`)
- `{{TESTIMONIAL_QUOTE}}`, `{{CLIENT_NAME}}`, `{{CLIENT_ROLE}}` — real client testimonials
  (`src/pages/index.astro`, Testimonials section) — currently 3 placeholder cards
- Production domain: replace `https://www.example.com` in `astro.config.mjs`,
  `src/data/site.ts`, and `public/robots.txt` (keep all three in sync)

## Images

All photography on the site is currently a **placeholder** — an abstract navy/gold
architectural line illustration rendered by the `PlaceholderImage` component (see
`src/components/PlaceholderImage.astro`), each labeled in the corner with what it should
become (e.g. "Placeholder photo — Exterior of a central Arkansas home at dusk"). Swap these
for real photography by replacing the `<PlaceholderImage ... />` usage with a real `<img>`
(or Astro's `<Image />`) and a matching, descriptive `alt`.

Also add a real 1200×630 social share image and wire it up as `og:image`/`twitter:image` in
`src/layouts/Layout.astro` (currently omitted rather than pointing at a broken asset — see the
TODO comment there).

## Contact form (upcoming)

The Contact page (not yet built) will include a real client-side-validated form. Per the
brief, submission will be wired to a placeholder handler with a `TODO` comment for
Formspree/Netlify Forms/email — to be finalized when that page is built.

## SEO

- Per-page `<title>` and meta description via the `Layout` component's `title`/`description`
  props.
- Open Graph + Twitter card tags.
- `LocalBusiness` JSON-LD structured data (`src/layouts/Layout.astro`), with placeholders for
  unconfirmed fields.
- `@astrojs/sitemap` generates `sitemap-index.xml` automatically at build time.
- `public/robots.txt` references the sitemap (update the domain there too).

## Accessibility

- Semantic landmarks (`header`, `nav`, `main`, `footer`), one `<h1>` per page, logical heading
  order.
- Visible focus states on all interactive elements (`focus-visible` rings).
- Skip-to-content link.
- Mobile nav menu: `aria-expanded`/`aria-controls`, closes on Escape, label on the dialog.
- Decorative icons are `aria-hidden`; placeholder image blocks use `role="img"` with a
  descriptive `aria-label` standing in for future alt text.
