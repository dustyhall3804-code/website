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

  appraiserName: '{{APPRAISER_NAME}}',
  licenseNumber: '{{LICENSE_NUMBER}}',
  yearsInBusiness: '{{YEARS_IN_BUSINESS}}',
  turnaroundTime: '{{TURNAROUND_TIME}}',
  schedulingWindow: '{{SCHEDULING_WINDOW}}',

  phone: '{{PHONE}}',
  phoneHref: 'tel:{{PHONE_E164}}',
  email: '{{EMAIL}}',
  emailHref: 'mailto:{{EMAIL}}',

  addressLine1: '{{STREET_ADDRESS}}',
  addressCity: 'Greenbrier',
  addressState: 'AR',
  addressZip: '{{POSTAL_CODE}}',
  hours: '{{BUSINESS_HOURS}}',

  latitude: '{{LATITUDE}}',
  longitude: '{{LONGITUDE}}',

  serviceCounties: ['Faulkner County', 'Pulaski County', 'White County', 'Van Buren County'],
  serviceCities: ['Greenbrier', 'Conway', 'Vilonia', 'Mayflower', 'Guy', 'Quitman', 'Damascus'],
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
