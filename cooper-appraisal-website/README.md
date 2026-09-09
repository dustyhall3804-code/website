# Cooper Appraisal Company — Website

A premium marketing site for Cooper Appraisal Company (Greenbrier, AR), built with
[Astro](https://astro.build) and [Tailwind CSS v4](https://tailwindcss.com).

## Status: All six pages built

Home, Commercial, Residential, House Measuring, About, and Contact are all built on the
shared design system. Lighthouse (Performance/Accessibility/Best Practices/SEO) scores 100
across all six pages; axe-core reports 0 accessibility violations on each.

### Functionality carried over from the previous AppraiserXsites site

At the client's request, a few functions from the existing AppraiserXsites-hosted site were
incorporated (that site couldn't be inspected directly due to a network restriction, so this
was scoped via a follow-up conversation rather than screenshots):

- **Order an Appraisal** and **Get a Fee Quote** are both handled by the same form on
  `/contact` (`src/components/ContactForm.astro`) via a segmented "What can we help with?"
  control. CTAs elsewhere on the site deep-link into the right mode with
  `/contact?type=order` or `/contact?type=quote` (also `?type=general`).
- **Client Login** — a nav/footer link (desktop nav, mobile menu, footer, and the Contact
  page's info card) points at the existing AppraiserXsites site
  (`https://cooperappraisalcompanyinc2.appraiserxsites.com/Home`) so client login and
  document delivery keep working there while this site handles marketing. A true client
  portal (accounts, document storage) isn't something a static site can provide on its own —
  see `clientPortalUrl` in `src/data/site.ts` if you'd rather point it at a different/more
  direct login URL once you've confirmed one.

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
  components/     Button, Section, Card, Nav, Footer, PageHeader, PlaceholderImage,
                  ContactForm
  data/site.ts     Business info + placeholder tokens + nav links
  layouts/Layout.astro   Page shell: <head>, SEO meta, JSON-LD, Nav/Footer
  pages/          index, commercial, residential, house-measuring, about, contact
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

## Business info status

**Confirmed and already wired in** (`src/data/site.ts`):

- Office phone: (501) 679-6844 &middot; Cell: (501) 733-6436
- Address: 109 North Broadview, Greenbrier, AR 72058
- Hours: Mon–Thu 8:00 AM–5:00 PM, Fri 8:00 AM–4:00 PM, Sat–Sun Closed
  — **note:** Friday was given as "8p–4p"; assumed a typo for 8:00 AM–4:00 PM
  (matches the rest of the week's opening time). Confirm or correct.

**Still placeholders** — real contact info, credentials, and testimonials beyond the above
were intentionally **not** invented. Search the project for these tokens (mainly in
`src/data/site.ts`) and replace them:

- `{{EMAIL}}` — business email
- `{{APPRAISER_NAME}}` / `{{LICENSE_NUMBER}}` — public records (Arkansas / ASC national
  registry) suggest this business is licensed to **Justin Cooper, Certified General
  Appraiser, credential #CG-1302** — not set automatically since it wasn't confirmed
  directly by the client. Confirm and fill in `src/data/site.ts`.
- `{{YEARS_IN_BUSINESS}}` — years in business (hero trust line)
- `{{TURNAROUND_TIME}}` / `{{SCHEDULING_WINDOW}}` — typical report turnaround and
  scheduling lead time
- `{{LATITUDE}}` / `{{LONGITUDE}}` — geocoordinates for the LocalBusiness schema
  (`src/layouts/Layout.astro`) — for 109 North Broadview, Greenbrier, AR 72058
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

## Contact form

`/contact` includes a real, client-side-validated form (`src/components/ContactForm.astro`):
required-field + email-format validation with inline errors and focus management, a
"What can we help with?" segmented control (Order an Appraisal / Get a Fee Quote / General
Question, deep-linkable via `?type=`), and a success state on submit. It does **not** send
data anywhere yet — see the `TODO` comment at the top of that component's `<script>` for how
to wire it up to Formspree or Netlify Forms.

The Contact page also embeds a live, key-less Google Maps view of 109 North Broadview,
Greenbrier, AR 72058 (`https://www.google.com/maps?q=...&output=embed` — no API key or
billing account required).

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
