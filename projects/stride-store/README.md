# STRIDE — Sportswear & Equipment Store

![STRIDE storefront preview](https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1400&q=80)

**A responsive sports retail storefront concept** built to demonstrate modern e-commerce UX, product discovery, client-side state management, and polished frontend implementation.

> Portfolio/demo project. Product listings, prices, newsletter feedback, cart, and checkout are illustrative. No real inventory, payment processing, order creation, or email delivery is connected.

## Live preview

Open [index.html](./index.html) locally, or enable GitHub Pages for this repository and publish from the root of the repository. Since this project lives in a monorepo subdirectory, use a Pages workflow or deploy the `projects/stride-store` directory with a static hosting provider.

## Experience highlights

- **Editorial storefront:** bold typographic hero, campaign section, brand manifesto, value propositions, newsletter sign-up, and responsive footer.
- **Product discovery:** eight sample products across Training, Running, and Accessories.
- **Search and filtering:** live text search, category navigation, and featured / price / alphabetical sorting.
- **Wishlist:** add and remove favorites, then switch to a wishlist-only view.
- **Shopping bag:** add items, adjust quantities, remove products, and calculate a live subtotal.
- **Demo checkout:** validated customer form with an explicit no-payment notice; submitting clears the demo cart.
- **Responsive layout:** desktop, tablet, and mobile navigation and product grids.
- **Accessibility basics:** semantic landmarks, descriptive labels, keyboard-operable buttons, visible status feedback, and reduced-motion support.

## Tech stack

| Layer | Technology |
|---|---|
| Markup | HTML5 |
| Styling | CSS3, custom properties, Grid, Flexbox, media queries |
| Interaction | Vanilla JavaScript (ES6+) |
| Typography | DM Sans + Space Grotesk |
| Visual assets | Remote Unsplash image URLs |
| Quality automation | GitHub Actions |

No framework, package manager, build step, or runtime dependency is required.

## Run locally

### Option 1 — open directly

1. Download or clone the repository.
2. Open `projects/stride-store/index.html` in a modern browser.

### Option 2 — local development server

From the repository root:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000/projects/stride-store/
```

On Windows, `py -m http.server 8000` is also supported.

## Project structure

```text
projects/stride-store/
├── index.html      # Storefront structure and page sections
├── styles.css      # Visual system, responsive layout, and components
├── app.js          # Product data, filtering, wishlist, cart, and demo checkout
└── README.md       # Project documentation
```

## Interaction model

The storefront uses a small in-memory state object:

- `category` — selected product category
- `query` — current search term
- `sort` — active sort mode
- `cart` — product IDs and quantities
- `wishlist` — set of favorite product IDs
- `wishlistOnly` — whether the catalog is restricted to favorites

The UI is rendered from this state. Refreshing the page resets the demo state; persistence and user accounts are intentionally outside this frontend-only version.

## Quality checks

The repository workflow performs lightweight static checks on the STRIDE project:

- required project files exist;
- HTML references the stylesheet and JavaScript entry point;
- key storefront sections and interactions are present;
- JavaScript passes Node syntax validation.

Run the JavaScript syntax check locally if Node.js is installed:

```bash
node --check projects/stride-store/app.js
```

## Product roadmap

The current implementation is a frontend portfolio project. A production commerce platform would need additional engineering:

1. **Application architecture:** React or Next.js frontend with reusable components and typed domain models.
2. **Backend API:** product, category, inventory, customer, cart, and order endpoints.
3. **Database:** PostgreSQL schema, migrations, indexes, and transaction-safe stock management.
4. **Authentication:** secure customer accounts, sessions, password reset, and role-based admin access.
5. **Payments:** payment-provider integration, verified webhooks, refunds, and idempotent order processing.
6. **Operations:** shipping and tax rules, inventory reconciliation, email notifications, observability, and backups.
7. **Security:** server-side validation, rate limiting, CSRF protections where applicable, secure secrets, and privacy-aware data handling.
8. **Testing:** unit, integration, accessibility, and end-to-end checkout tests.

## Scope and limitations

- Product data and pricing are hard-coded sample content.
- Images load from Unsplash and therefore require an internet connection.
- Cart and wishlist state are in-memory only and are not persisted.
- The checkout is a UI demonstration only; it does not collect or transmit payment details.
- Newsletter submission displays local feedback only.
- This project is not presented as a production-ready commerce system.

## License

This project is provided as a portfolio demonstration. Review the licenses and usage terms of third-party images and fonts before commercial reuse.

---

**STRIDE — Gear for the long run.**