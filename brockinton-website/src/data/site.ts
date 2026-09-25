// All business facts in one place. Wording for services and testimonials is
// Cody's own (from his current site); do not add services or claims here
// without confirming them with him.

export const business = {
  name: 'Brockinton Land Management LLC',
  shortName: 'Brockinton Land Management',
  owner: 'Cody Brockinton',
  city: 'Sherwood',
  region: 'AR',
  serviceArea: 'Central Arkansas',
  phone: '501-992-8818',
  phoneHref: 'tel:+15019928818',
  tagline:
    'Land clearing, debris removal, pond construction, tree and brush removal, brush hogging, vegetation control, mulching, demolition, and more.',
  facebook: 'https://www.facebook.com/BrockintonLandManagement',
  instagram: 'https://www.instagram.com/brockinton_land_managment',
  // TODO(confirm with Cody): business hours and a public email address.
  hours: null as string | null,
  email: null as string | null,
};

export type Service = { id: string; title: string; text: string };

// Order matches the scroll story; Pond Construction is last, timed with the water.
export const services: Service[] = [
  { id: 'land-clearing', title: 'Land Clearing', text: 'Land clearing for your new home.' },
  {
    id: 'tree-removal',
    title: 'Tree Removal',
    text: 'When it comes to tree removal, safety should always be the top priority for everyone involved.',
  },
  { id: 'mulching', title: 'Mulching', text: 'For soil health and plant growth.' },
  // No description on Cody's site for these two; titles only until he supplies wording.
  { id: 'brush-hogging', title: 'Brush Hogging and Vegetation Control', text: '' },
  { id: 'trenching', title: 'Trenching', text: 'Trenching for cable or pipe, from three inches to three feet deep.' },
  { id: 'debris-removal', title: 'Debris Removal', text: 'Need some major clean-up done? We can do it!' },
  { id: 'demolition', title: 'Demolition', text: '' },
  {
    id: 'pond-construction',
    title: 'Pond Construction',
    text: "Water for the farm animals or your own private fishin' hole. We can make it happen.",
  },
];

export const testimonials = [
  {
    name: 'Jim Garner',
    quote:
      'Impressed with our storm shelter installation. Quick, reliable, and reasonably priced. I am thrilled with the results.',
  },
  {
    name: 'Ellen Johnson',
    quote: 'Outstanding service for dirt moving and tree removal. The team was punctual, skilled, and left the site spotless.',
  },
  {
    name: 'Bertie Norton',
    quote:
      'I hired them for mulching and tree removal. They did an excellent job, very efficient and professional. I highly recommend their services!',
  },
];

export const partner = {
  name: 'Cozy Caverns Storm Shelters',
  url: 'https://cozycaverns.com',
};

// Formspree form endpoint. Create the form at formspree.io and put its ID in
// PUBLIC_FORMSPREE_ID (see README). Until then the form shows a call-us notice.
export const formspreeId = import.meta.env.PUBLIC_FORMSPREE_ID as string | undefined;
