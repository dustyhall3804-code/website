// Central place for business info and placeholders. Replace every {{TOKEN}}
// below with confirmed real values before launch — see README.md for the
// full checklist.

export const SITE = {
  name: 'Cooper Appraisal Company',
  shortName: 'Cooper Appraisal',
  tagline: 'Certified Residential & Commercial Appraisals',
  // TODO: replace with the real production domain (also update astro.config.mjs
  // and public/robots.txt so they stay in sync).
  url: 'https://www.example.com',
  description:
    'Certified residential and commercial real estate appraisals and ANSI-standard house measuring services serving Greenbrier and Central Arkansas.',

  // Public records (Arkansas / ASC national appraiser registry) suggest this
  // business is licensed to Justin Cooper, Certified General Appraiser,
  // credential #CG-1302 — NOT set below since it wasn't confirmed directly
  // by the client. Confirm and fill in before launch.
  appraiserName: '{{APPRAISER_NAME}}',
  licenseNumber: '{{LICENSE_NUMBER}}',
  yearsInBusiness: '{{YEARS_IN_BUSINESS}}',
  turnaroundTime: '{{TURNAROUND_TIME}}',
  schedulingWindow: '{{SCHEDULING_WINDOW}}',

  officePhone: '(501) 679-6844',
  officePhoneHref: 'tel:+15016796844',
  cellPhone: '(501) 733-6436',
  cellPhoneHref: 'tel:+15017336436',
  // Used as the primary phone site-wide (nav, hero, final CTA); the cell
  // number is shown alongside it in the footer.
  phone: '(501) 679-6844',
  phoneHref: 'tel:+15016796844',
  email: '{{EMAIL}}',
  emailHref: 'mailto:{{EMAIL}}',

  addressLine1: '109 North Broadview',
  addressCity: 'Greenbrier',
  addressState: 'AR',
  addressZip: '72058',
  // NOTE: Friday was written as "8p–4p", which can't be right for a
  // business open 8a–5p the rest of the week — assumed to mean 8:00 AM–4:00
  // PM below. Confirm/correct if that's wrong.
  hours: [
    { days: 'Mon–Thu', time: '8:00 AM–5:00 PM' },
    { days: 'Fri', time: '8:00 AM–4:00 PM' },
    { days: 'Sat–Sun', time: 'Closed' },
  ],
  // schema.org LocalBusiness openingHours format, kept in sync with `hours` above.
  openingHoursSchema: ['Mo-Th 08:00-17:00', 'Fr 08:00-16:00'],

  latitude: '{{LATITUDE}}',
  longitude: '{{LONGITUDE}}',

  serviceCounties: ['Faulkner County', 'Pulaski County', 'White County', 'Van Buren County'],
  serviceCities: ['Greenbrier', 'Conway', 'Vilonia', 'Mayflower', 'Guy', 'Quitman', 'Damascus'],

  // Existing AppraiserXsites site — kept live for client login / document
  // delivery while this site handles marketing. Points at the confirmed
  // homepage rather than a guessed deep link; if there's a more direct
  // "Client Login" URL on that platform, swap it in here.
  clientPortalUrl: 'https://cooperappraisalcompanyinc2.appraiserxsites.com/Home',
} as const;

export type NavLink = { label: string; href: string };

export const NAV_LINKS: NavLink[] = [
  { label: 'Home', href: '/' },
  { label: 'Commercial', href: '/commercial' },
  { label: 'Residential', href: '/residential' },
  { label: 'House Measuring', href: '/house-measuring' },
  { label: 'About', href: '/about' },
  { label: 'Contact', href: '/contact' },
];

export const FOOTER_SERVICE_LINKS: NavLink[] = [
  { label: 'Commercial Appraisals', href: '/commercial' },
  { label: 'Residential Appraisals', href: '/residential' },
  { label: 'House Measuring', href: '/house-measuring' },
];

export const FOOTER_COMPANY_LINKS: NavLink[] = [
  { label: 'About', href: '/about' },
  { label: 'Contact', href: '/contact' },
];
