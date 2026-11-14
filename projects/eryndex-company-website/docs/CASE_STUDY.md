# ERYNDEX Company Website — Portfolio Project

**Project type:** B2B company website / responsive static front end  
**Status:** Initial implementation committed to the portfolio repository  
**Implementation:** HTML5, CSS3, vanilla JavaScript  
**Hosting target:** GitHub Pages

## Overview

This project documents the design and implementation of the ERYNDEX company website: a dark, editorial, responsive web presence for a software engineering and applied AI company targeting international B2B clients and agency partnerships.

The company site itself lives in the `/eryndex/` directory. This directory is the portfolio case study: it explains the brief, information architecture, design system, implementation, responsive behavior, content decisions and launch checklist.

## Links

- Company website (expected GitHub Pages URL): https://arshiataheri851-ops.github.io/portfolio/eryndex/
- Company website source: https://github.com/arshiataheri851-ops/portfolio/tree/main/eryndex
- Portfolio home: https://arshiataheri851-ops.github.io/portfolio/

## Goals

1. Explain ERYNDEX's positioning and service capabilities to international business visitors.
2. Establish credibility through transparent project demonstrations and source links.
3. Introduce the founding partners by their actual responsibilities.
4. Explain the engagement process from discovery to handover.
5. Provide a direct route for prospective clients to initiate contact.
6. Keep the implementation lightweight, responsive and straightforward to maintain.

## Main sections

- Hero / positioning
- Company introduction
- Backend & API engineering
- Applied AI integration
- Knowledge retrieval / RAG foundations
- Integration and webhook delivery systems
- Selected work: FarsiPulse, AtlasRAG and RelayForge
- Founding team and role split
- Four-step delivery process
- Contact call to action

## Design system

- Deep navy background and layered dark surfaces
- Mint accent for key actions and active details
- Blue-gray secondary accent and muted text
- Space Grotesk display typography and DM Sans body typography
- Fine borders, restrained card treatments and generous section spacing
- CSS custom properties for centralized design tokens
- Responsive breakpoints for tablet and mobile

## Technical implementation

### HTML
Semantic sections and landmarks, navigation, headings, project cards, team profiles, service descriptions and contact links.

### CSS
Responsive grid and flex layouts, custom properties, mobile navigation presentation, hover feedback, reduced-motion preference and typography system.

### JavaScript
- Mobile navigation toggle
- `aria-expanded` state synchronization
- Scroll progress indicator
- Dynamic copyright year

### Hosting
The site is static and does not require a bundler or server-side runtime. It can be hosted from the existing GitHub Pages repository under the `/portfolio/eryndex/` path.

## Repository layout

```text
portfolio/
├── index.html
├── assets/
│   └── style.css
├── eryndex/
│   ├── index.html
│   └── assets/
│       ├── style.css
│       └── script.js
└── eryndex-company-website/
    ├── index.html
    ├── README.md
    └── assets/
        └── eryndex-preview.svg
```

## Content accuracy

The project pages intentionally avoid unsupported claims:
- Portfolio projects are presented as demonstrators, not verified enterprise deployments.
- Team biographies and credentials should be published only after approval.
- No client logos, testimonials, performance claims or compliance certifications are fabricated.
- The current contact email is a placeholder and must be replaced before public launch.

## Validation checklist

- [ ] Confirm GitHub Pages is enabled and verify the live URL.
- [ ] Replace placeholder company email.
- [ ] Confirm legal/company identity wording.
- [ ] Obtain team member approval for bios, photos and profile links.
- [ ] Test all internal and external links.
- [ ] Test mobile menu with keyboard and touch.
- [ ] Test current Chrome, Firefox, Safari and mobile browsers.
- [ ] Run Lighthouse and accessibility checks.
- [ ] Capture real browser screenshots after deployment.
- [ ] Add a verified company domain when available.

## Run locally

Because this is a static site, open `eryndex/index.html` in a browser or serve the repository directory with any static file server. No package installation is required.

## Notes

The SVG preview included in this case study is an illustrative design visual, not a screenshot of the deployed website. The source code in `/eryndex/` is the actual website implementation.
