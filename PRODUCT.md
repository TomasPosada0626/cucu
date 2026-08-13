# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: **buyers** near a seller — people who want a quick, affordable, home-cooked meal instead of a restaurant order, and choose CUCU because a "coca" (a home cook's surplus portion) is close by and about to go to waste.

Secondary, on the same account model (no separate account types — a single `User` gains courier capability via an `es_repartidor` flag):
- **Sellers / home cooks** who publish extra portions of what they already made, bounded by `stock` and `maximo_por_venta` (max per sale) — this is publishing surplus, not running a restaurant menu.
- **Couriers (repartidores)** who fulfill nearby deliveries and earn tips (`propina`) per order.

Buyer is the primary lens for future design decisions; seller and courier flows exist to make the buyer's supply possible and should not be designed as co-equal "modes."

## Product Purpose

CUCU redistributes surplus home-cooked food to nearby buyers before it goes to waste, using proximity as the mechanism that makes pickup/delivery fast enough to be worth choosing over a restaurant order.

Current success criterion: this is a **purely academic/portfolio project** (an active solo fork of a graded team deliverable — see the Wiki's `Entregable2` and other course entregables). Success today means demonstrating sound architecture, security, and test coverage against course rubric, not real-world adoption metrics. There is no live user base yet.

## Positioning

CUCU's mechanism is **anti-food-waste**, not "yet another delivery app": listings represent a home cook's *leftover, limited-quantity* portions (enforced by `stock`/`maximo_por_venta`), not an ongoing restaurant catalog. Combined with hyperlocal proximity (every listing and delivery address is geo-located; a dedicated geo microservice handles geocoding/routing), this is what a generic aggregator like Uber Eats or Rappi could not truthfully claim — CUCU exists because someone nearby cooked too much today, not because a kitchen has a permanent menu.

## Operating Context

- Hybrid architecture: Django monolith (core views/logic) + Flask microservices (`geo-service`, `payment-service`, `auth-service`, `market-service`, etc.), RabbitMQ + Redis/Celery for async work, all behind an Nginx API gateway, run via Docker Compose.
- Single account model: every `User` can buy; `es_repartidor` toggles courier tooling on the same account rather than a separate identity.
- Order lifecycle: `Pedido` (order) has an `estado` (status) field driving the buyer/seller/courier flow, a `total`, and a `propina` (tip) that factors into courier earnings.
- Listings (`Publicacion`) are explicitly quantity-bounded (`stock`, `maximo_por_venta`) and tied to a geo `Ubicacion`.
- Buyers can save multiple addresses (`DireccionGuardada`) with one marked default.
- Fully bilingual: Spanish (default) and English, user-switchable.
- Deployed/documented for AWS (see `README_DEPLOY_AWS.md`); business/academic context lives in the repo Wiki.

## Capabilities and Constraints

- No multi-tenant or separate seller/courier accounts — role capability is a flag on one `User` model. Future design work should assume a buyer can become a seller or courier without switching identity.
- Listings are inherently finite/perishable (stock-limited, no restock-as-menu pattern) — UI and copy should not imply an always-available catalog.
- Payments run through a dedicated Flask microservice (`/api/v2/payments`), separate from the Django monolith.
- Undecided / not yet established: no confirmed food-safety or payments-compliance requirement, no confirmed production payment provider details beyond the existing microservice route, no confirmed accessibility standard.

## Brand Commitments

- Name: **CUCU**, tagline "Comida casera en cocas cerca de ti" (per README/product framing).
- A visual identity (palette, type pairing, illustration style) already exists across the shipped templates. Per `init` scope this is recorded as evidence for future design work, not restated or made binding here — `/impeccable document` or `new-work` owns deciding whether to preserve or replace it.

## Evidence on Hand

- No real user data, testimonials, sales figures, or case studies exist — this is a portfolio/academic project. Future work must not fabricate reviews, ratings, testimonials, or usage numbers.
- Placeholder/sample content exists: dish images under `static/images/` (e.g. `pizza.png`, `ramen.png`, `bowl.png`) and two hero/scene illustrations (`scene-home.png`, `scene-seller.png`) used on the landing page.
- Team/collaborator credits and course-deliverable links are documented in `README.md` and the repo Wiki (`Entregable2`, etc.).

## Product Principles

1. Design for the buyer's job first — finding a fast, cheap, nearby home-cooked meal — and treat seller and courier surfaces as supporting infrastructure, not co-equal modes.
2. Every surface should read as "surplus, limited, and nearby," not as a generic always-on restaurant menu — this is the product's entire reason to exist over a delivery aggregator.
3. Keep geography functionally legible (not decorative) in publishing, ordering, and delivery flows — proximity is the mechanism, not a feature.
4. This is currently an academic/portfolio deliverable: engineering demonstrability (architecture, security, tests) matters as much as user-facing polish when trading off effort.
5. Preserve the single-account, flag-based role model (`es_repartidor`) — do not design flows that assume separate seller/courier identities or logins.
