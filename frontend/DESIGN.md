version: alpha
name: Google Doodles Experience
description: Playful, interactive archive and discovery platform for Google Doodles.
colors:
primary: "#1A73E8"
text-main: "#202124"
surface: "#FFFFFF"
surface-warm: "#F5DEC3"
surface-blue-light: "#D3E3FD"
border-dark: "#1F1F1F"
google-blue: "#4285F4"
google-red: "#EA4335"
google-yellow: "#FBBC05"
google-green: "#34A853"
typography:
headline-lg:
fontFamily: Google Sans
fontSize: 48px
fontWeight: 500
lineHeight: 1.2
headline-md:
fontFamily: Google Sans
fontSize: 32px
fontWeight: 500
lineHeight: 1.3
body-md:
fontFamily: Google Sans
fontSize: 16px
fontWeight: 400
lineHeight: 1.5
label-sm:
fontFamily: Google Sans
fontSize: 14px
fontWeight: 500
lineHeight: 1.2
rounded:
sm: 8px
md: 16px
lg: 24px
full: 9999px
spacing:
sm: 8px
md: 16px
lg: 32px
xl: 64px
grid-cell: 48px
components:
card-default:
backgroundColor: "{colors.surface}"
rounded: "{rounded.lg}"
padding: 32px
button-next:
backgroundColor: "{colors.primary}"
textColor: "{colors.surface}"
rounded: "{rounded.md}"
padding: 24px
Overview
A playful, interactive, and brand-centric interface designed for exploring the archive of Google Doodles. The design language evokes a sense of creativity and drafting, utilizing sketchbook-style grid backgrounds, scattered stylized illustrations, and bold, clean typography. It balances the institutional Google identity with a fun, approachable user experience.
Colors
The palette relies on stark neutrals (white and dark gray/black) to provide high contrast, allowing the vibrant, diverse artwork of the Doodles to stand out. Google's core brand colors are used as accents in the background typography and illustrations.
Primary (#1A73E8): Standard Google blue, used for primary navigation and core actions (like the "Next" button).
Surface Warm (#F5DEC3): A warm, peachy-beige background used to differentiate specific discovery sections.
Surface Blue Light (#D3E3FD): A soft blue used as a container background for input areas.
Border Dark (#1F1F1F): High-contrast dark gray/black used for thin structural outlines on cards, tooltips, and form inputs.
Google Brand Accents: Blue (#4285F4), Red (#EA4335), Yellow (#FBBC05), and Green (#34A853) are used in decorative background elements and typography.
Typography
The interface exclusively relies on Google's proprietary geometric sans-serif typeface to maintain brand consistency.
Headlines: Google Sans Medium. Used for prominent section headers (e.g., "Find your Doodle", "Discover more Doodles by color").
Body & Metadata: Google Sans Regular and Medium. Used for dates, descriptions, and interactive labels.
Layout
The layout uses generous whitespace and a distinct architectural motif:
Background Grids: Several sections utilize a pale gray drafting grid pattern in the background, reinforcing the "doodle" and creation theme.
Scattered Elements: Interactive widgets (like the birthday selector) are centered, while decorative illustration cards are placed in the background with varied, playful rotations.
Split Views: The color discovery tool uses a 50/50 split layout, with the interactive color wheel anchored on the left and a scrollable list of corresponding Doodle cards on the right.
Elevation & Depth
The design largely eschews traditional soft drop shadows in favor of a flatter, more graphic "neo-brutalist" approach to depth.
Layering: Depth is achieved by overlapping solid shapes and utilizing distinct 1px dark borders around cards and input fields.
Stacked Cards: Features like the "Did you know?" trivia card use a rigid, offset stacking effect (multiple outlined cards layered behind one another) to imply a physical deck of cards.
Shapes
Shapes heavily favor friendly, rounded geometries to keep the interface approachable.
Cards and Containers: Feature large corner radii (typically 16px to 24px).
Interactive Elements: The color wheel is perfectly circular, and tooltips utilize a pill-shape (full radius) with a sharp directional arrow.
Input Fields: Dropdowns and form elements within widgets feature prominent rounded corners, framed by thin, crisp borders.
Components
Doodle Cards: White background, 1px dark border, rounded corners (24px). Contains a centered image of the Doodle and metadata aligned to the right.
Input Selectors (Birthday): White background, dark outline, rounded corners (16px), floating labels anchored to the top edge of the bounding box.
Card Stacks: Multiple cards sharing the same dimensions, staggered diagonally to show depth via physical layering rather than shadows.
Floating Tooltips: Pill-shaped, white background, dark outline, with an indicator dot and text.
Do's and Don'ts
Do utilize the background drafting grid to ground the designs and maintain the sketchbook theme.
Do rely on thin (1px) dark borders to define edges and create separation between overlapping elements.
Don't use soft, blurred drop shadows for elevation. Rely on layered vectors and solid offsets.
Don't clutter the primary content zones; use the background layers for playful, tilted, and scattered brand elements.