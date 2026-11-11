# STRIDE® — Performance & Sportswear Store

A premium, responsive storefront concept built as a frontend portfolio project. STRIDE demonstrates a complete shopping journey at the UI level: editorial landing page, product discovery, saved items, quick views, persistent cart, and a clearly labelled demo checkout.

> **Live website:** https://arshiataheri851-ops.github.io/arshiataheri851-ops/  
> **Important:** This is a static frontend demonstration. It does not process payments, create real orders, connect to inventory, or send emails.

## Experience

- Editorial hero, campaign feature, brand manifesto, values and newsletter section.
- 12 sample products across Training, Running and Accessories.
- Live search, category filtering, wishlist-only view and four sort modes.
- Product quick-view dialog with descriptions and add-to-bag action.
- Shopping bag with quantity controls, remove actions and live subtotal.
- Cart and wishlist persistence using localStorage.
- Demo checkout with browser form validation and an explicit no-payment disclaimer.
- Responsive navigation, mobile-first layouts, keyboard-friendly controls and reduced-motion support.
- Custom page metadata, favicon and social preview metadata.

## Tech stack

- HTML5 semantic structure
- CSS3 custom properties, Grid, Flexbox and responsive breakpoints
- Vanilla JavaScript (ES6+), DOM events and localStorage
- Google Fonts (DM Sans and Space Grotesk)
- Unsplash remote photography
- GitHub Actions + GitHub Pages deployment

No framework, package manager or build step is required.

## Run locally

From the repository root:

```bash
py -m http.server 8000
```

Open http://localhost:8000/projects/stride-store/

Or open `index.html` directly in a modern browser. A local server is recommended for consistent browser behavior.

## Project structure

```text
projects/stride-store/
├── index.html
├── styles.css
├── app.js
└── README.md
```

## State model

The storefront keeps a small client-side state object for the selected category, search query, sorting mode, cart contents, saved product IDs and wishlist filter. Cart and wishlist are saved locally in the visitor's browser. No personal information is transmitted to a server.

## Deployment

The repository includes `.github/workflows/stride-store-pages.yml`. It validates the storefront files and publishes the contents of `projects/stride-store` as a GitHub Pages artifact.

Expected project URL:

`https://arshiataheri851-ops.github.io/arshiataheri851-ops/`

For the repository's Pages site to publish, set **Settings → Pages → Build and deployment → Source → GitHub Actions** once. GitHub Pages sites are public. After that one-time setting, pushes affecting this project trigger deployment automatically.

## Quality checks

The deployment workflow checks:
- required storefront files exist;
- HTML includes the CSS and JavaScript entry points;
- the expected catalog and interactive features are present;
- JavaScript passes Node syntax validation.

## Production roadmap

This repository intentionally remains a static frontend demo. A real store would require a backend API, database-backed product and inventory data, secure authentication, server-side order validation, a payment provider, verified webhooks, shipping/tax integrations, admin tooling, observability and automated end-to-end tests.

**STRIDE — Gear for the long run.**
