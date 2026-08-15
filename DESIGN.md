---
name: CUCU
description: Comida casera en cocas cerca de ti — a hyperlocal marketplace for surplus home-cooked food.
colors:
  ember: "#ff6a1a"
  ember-deep: "#f25c10"
  ember-soft: "#fff1e7"
  sage: "#5aa851"
  sage-soft: "#eef8eb"
  toasted-amber: "#ff8f3d"
  amber-soft: "rgba(255, 143, 61, 0.14)"
  terracotta: "#de5f58"
  terracotta-soft: "rgba(222, 95, 88, 0.14)"
  charcoal-ink: "#1f2430"
  slate-muted: "#676c7a"
  ink-hairline: "rgba(31, 36, 48, 0.08)"
  warm-paper: "#fcf8f3"
  warm-paper-2: "#fffdfa"
  warm-white: "rgba(255, 255, 255, 0.96)"
typography:
  display:
    fontFamily: "'Outfit', sans-serif"
    fontSize: "clamp(2.25rem, 7vw, 3.5rem)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.06em"
  headline:
    fontFamily: "'Outfit', sans-serif"
    fontSize: "2.125rem"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.04em"
  title:
    fontFamily: "'Outfit', sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "'Manrope', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "'Outfit', sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0.08em"
rounded:
  pill: "999px"
  xl: "32px"
  lg: "24px"
  md: "18px"
  sm: "14px"
  xs: "7px"
components:
  button-primary:
    backgroundColor: "{colors.ember}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0 28px"
    height: "56px"
  button-primary-hover:
    backgroundColor: "{colors.ember-deep}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
  button-secondary:
    backgroundColor: "{colors.warm-white}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.pill}"
    padding: "0 28px"
    height: "56px"
  card-food:
    backgroundColor: "{colors.warm-white}"
    rounded: "{rounded.xl}"
    padding: "16px"
  input-field:
    backgroundColor: "#fffdfb"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.md}"
    height: "56px"
---

# Design System: CUCU

## Overview

**Creative North Star: "The Extra Plate"**

CUCU exists because someone nearby cooked one plate too many. Every visual decision should read as a neighbor handing you food directly — not a restaurant scrolling its permanent menu, not a delivery aggregator's endless catalog. The system is warm and appetite-forward by design: a cream-and-ember palette, big honest food photography, and soft, fully-rounded shapes that feel closer to bakery signage or a farmers-market stall than a SaaS dashboard. Nothing here should feel sterile, corporate, or algorithmic — the product's entire premise is human-scale surplus, and the interface should feel that way even on its most transactional screens (checkout, order tracking, courier payouts).

The palette stays almost entirely warm neutrals (cream, paper-white, charcoal ink) punctuated by a single confident ember orange used for action and status, never as a large flat fill. Depth comes from soft, color-tinted shadows rather than hard edges or pure-black elevation — nothing in this system should look like it was clipped out with scissors.

**Convergence status:** the auth/landing surfaces and the app shell (`base_app.html`, extended by `carrito`, `checkout`, `perfil`, `seguimiento`, `pedido`-flow screens, etc.) have been converged onto the one ink hex, one ember hex, one Sage green, and pill buttons documented below — verified by grep across `templates/` for every form the palette can appear in (hex *and* the equivalent decimal `rgba()` triplets; an earlier pass only grepped hex literals and missed `rgba(30, 174, 122, …)`/`rgba(25, 165, 123, …)` — the legacy greens expressed as decimals — in 8 files). This file remains the source of truth for that unified system; treat any future code that disagrees with it as new drift to converge, not as an alternate style.

**Key Characteristics:**
- Warm, appetite-forward, human-scale — never corporate or sterile
- One confident accent (ember orange) used for action/status, not decoration
- Fully rounded everywhere: pill for anything interactive, sweeping large radii for containers
- Shadows are always color-tinted (ink or ember), never neutral black
- Real food photography and one illustrated "phone in hand" hero moment, not stock-icon abstraction

## Colors

The palette is a warm, near-monochrome cream-and-charcoal base with a single confident accent and a restrained semantic set for status. Nothing is saturated except the ember accent itself.

### Primary
- **Ember Orange** (`#ff6a1a`): the one confident accent — primary buttons, focus rings, active nav state, price emphasis, the brand mark. Always as a gradient, glow, or thin line — never a large flat fill.
- **Ember Deep** (`#f25c10`): the gradient's dark stop and the hover/active state of anything Ember-colored.
- **Ember Soft** (`#fff1e7`): tint background for badges, icon-rings, and subtle section washes behind Ember content.

### Secondary
- **Sage Green** (`#5aa851`): the system's "positive/success" color — accepted orders, completed deliveries, confirmation states. Muted and earthy on purpose, so it reads as "homemade/organic" rather than a generic UI-kit green. Reserve raw `#5aa851` for borders, icons, and dots — at text size on a light background it's only ~2.9:1, below WCAG AA.
- **Sage Soft** (`#eef8eb`): background tint for success badges and confirmation panels.
- **Sage Deep** (`#386832`): success/positive *text* on a light background (badges, confirmation copy) — ~6.6:1 on white. Same hue family as Sage Green, just dark enough to read as body text.

### Tertiary (status semantics)
- **Toasted Amber** (`#ff8f3d`) / soft `rgba(255, 143, 61, 0.14)`: pending/waiting states — an order not yet accepted, a step not yet complete.
- **Terracotta** (`#de5f58`) / soft `rgba(222, 95, 88, 0.14)`: danger/cancelled/unavailable states. Deliberately warm, not a cold alarm red — it stays inside the food-warm palette even when signaling a problem. Reserve raw `#de5f58` for borders, icons, and dots — at text size on a light background it's only ~3.6:1, below WCAG AA.
- **Terracotta Deep** (`#8a3b37`): danger/error *text* on a light background (form errors, cancelled-state copy) — ~7.6:1 on white. Same hue family as Terracotta, dark enough to read as body text. Same role as Sage Deep below, for the danger side of the palette.

### Neutral
- **Charcoal Ink** (`#1f2430`): primary text, icon strokes, and (at low alpha) every hairline border in the system.
- **Slate Muted** (`#676c7a`): secondary/supporting text — descriptions, timestamps, helper copy. Darkened from the original `#6f7483` (4.4:1 on Warm Paper, just under WCAG AA's 4.5:1 for normal text) to `#676c7a` (~5:1) — same warm-slate hue, imperceptibly darker, now compliant everywhere it's used at body/small size.
- **Warm Paper** (`#fcf8f3`) / **Warm Paper 2** (`#fffdfa`): the cream background gradient stops every screen sits on. Never pure white.
- **Warm White** (`rgba(255, 255, 255, 0.96)`): card and surface backgrounds — a near-white translucent layer over the paper gradient, not a flat opaque white.
- **Ink Hairline** (`rgba(31, 36, 48, 0.08)`): every border in the system. There is no solid/opaque border color anywhere.
- **Quiet Icon** (`#9a98a0`): input-prefix icons only (the small envelope/lock glyph inside a field, left of the placeholder) — lighter than Slate Muted on purpose, so it doesn't compete with the field's own text. Not a general icon color; every other icon in the system follows the "icon strokes = Charcoal Ink" rule below.

### Named Rules
**The Warm Signal Rule.** Ember orange is the color you *act on*, not the color you read. It appears on buttons, focus rings, active states, price, and the brand mark — never as body text, never as a large background fill. The one exception is a very low-alpha radial wash (~8%) behind hero content, which is atmosphere, not a color block.

**The One Green Rule.** Sage `#5aa851` (and its dark text variant Sage Deep `#386832`) is the only success/positive color family in the system. `#1eae7a`/`#19a57b`/`#7ea86f` (hex or decimal `rgba()`) are drift from before this file existed, not sanctioned variants — converge any you find to Sage.

**The One Red Rule.** Terracotta `#de5f58` (and its dark text variant Terracotta Deep `#8a3b37`) is the only danger/error color family in the system. `#a63c3c` / `rgba(218, 86, 86, …)` is the same category of pre-DESIGN.md drift as the greens above — converge any you find to Terracotta.

## Typography

**Display Font:** Outfit (with `sans-serif` fallback)
**Body Font:** Manrope (with `sans-serif` fallback)
**Label/Mono Font:** `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` — reserved for the rare debug/raw-output block, not a general UI face.

**Character:** Outfit carries every headline at a tight, confident negative tracking (−0.04em to −0.06em) that gives the brand its slightly compressed, appetite-forward voice; Manrope stays open and readable at neutral tracking for anything meant to be read at length. The pairing is deliberately a two-family system — no third typeface anywhere.

### Hierarchy
- **Display** (800, `clamp(2.25rem, 7vw, 3.5rem)`, line-height 1): hero/landing headlines only.
- **Headline** (700, 2.125rem/34px, line-height 1.05): section titles within a page.
- **Title** (700, 1.5rem/24px, line-height 1.1): card titles, profile names, panel headers.
- **Body** (400–500, 1rem/16px, line-height 1.6): all prose and descriptions; keep to a comfortable measure, don't let body text run full-bleed on wide containers.
- **Label** (800, 0.8125rem/13px, letter-spacing 0.08em, uppercase): eyebrow tags, button text, badge/status-pill text.

### UI Chrome Sizes

The five steps above are content hierarchy (what the reader reads); interface chrome — nav, badges, prices, card meta — needs finer steps between them. These were already in consistent use across the codebase (each appearing 6+ times for the same role) before being documented here; formalizing them is not a design change, it's finishing the scale that was already implicit in the code.

| Size | Weight | Use |
|---|---|---|
| 22px | 800 | Brand wordmark, standalone emphasis just under Title |
| 20px | 800–900 | Price/amount emphasis, compact modal headers |
| 18px | 700–900 | Component-level card titles (smaller than page Title) |
| 17px | 400 | Lead/subtext directly under a heading, `--muted` |
| 15px | 800 | Compact inline label (e.g. the brand-mark's "C") |
| 14px | 700 | Nav links, small interface text |
| 12px | 700–800 | Badges, chips, small status/meta text |
| 11px | 400 | Dense captions — timestamps, secondary meta |

A one-off size outside both this table and the Hierarchy above is real drift — snap it to the nearest documented step rather than adding a ninth size for one element. An exception already named by a signature component elsewhere in this file (e.g. the Courier Payout Card's 26px) stays as documented there.

### Named Rules
**The Tight Headline Rule.** Anything set in Outfit at Display or Headline size carries negative letter-spacing (−0.04em minimum). A headline with default tracking reads as off-system immediately.

## Layout

Two container widths by design, not drift: **1080px** on landing and auth surfaces (a narrower, editorial measure that suits a single persuasive column) and **1180px** on the logged-in app shell (more room for the grid-based operate screens). Both use the same gutter pattern: `width: min(var(--wrap), calc(100vw - 36px))`.

The app shell's primary layout is a two-column grid — a sticky `0.92fr` hero/summary panel beside a `1.08fr` content column — collapsing to a single column under **1020px**. Card grids (catalog, quick-links, stats) run `repeat(3, minmax(0, 1fr))`, collapsing to a single column under **760px**, where padding also drops to ~20px and card radii step up slightly (20–24px) to stay proportional at the smaller size.

## Elevation & Depth

Layered, not flat: surfaces rest with a soft, low-alpha shadow, and interactive/primary elements get a second, color-tinted "glow" layer that signals importance. No shadow in the system is ever neutral black — it is always tinted by what's casting it (ink for ambient depth, ember for action).

### Shadow Vocabulary
- **Ambient** (`box-shadow: 0 18px 54px rgba(31, 36, 48, 0.08)`): resting elevation for every card, panel, and surface.
- **Ember Glow** (`box-shadow: 0 16px 32px rgba(242, 92, 16, 0.22)`): primary buttons, the brand mark, and any element that should visually announce itself as the important action on screen.
- **Focus Ring** (`box-shadow: 0 0 0 4px rgba(255, 106, 26, 0.10)`): a solid ring (not a blurred glow) on input focus — deliberately different from the Ember Glow so focus reads as precise, not decorative.
- **Inset Hairline** (`box-shadow: inset 0 0 0 1px rgba(255, 106, 26, 0.12)`): a border-via-shadow trick used on circular avatar/profile images in place of an actual border.
- **Sheet** (`box-shadow: 0 -20px 60px rgba(0, 0, 0, 0.25)`): the one deliberately heavier, near-neutral shadow in the system — reserved for the bottom-sheet address picker, where the extra weight signals "this is a modal, not a card."

### Named Rules
**The Warm Shadow Rule.** A shadow always tells you what's beneath it: ink-tinted for resting surfaces, ember-tinted for actionable ones. A generic `rgba(0,0,0,…)` shadow is off-system outside the Sheet exception above.

## Shapes

Fully rounded, with radius doing the work of signaling a component's role. **Pill (999px)** is the default for anything a user acts on or scans quickly: buttons (primary and secondary, both), chips, nav pills, status pills, FABs, avatars, and slider/toggle controls. **32px** marks the largest containers (hero panels, page-level surfaces); **24px** marks standard cards and food tiles; **18px** marks inputs and secondary/nested cards; **14px** marks the smallest nested rows (mini-stat blocks, chip-as-row layouts). The only sharp-ish corner in the system is the **7px** brand-mark square — small enough that it reads as a wordmark, not a container, so it doesn't break the soft-everywhere rule.

Borders are always a 1px Ink Hairline at low alpha — never a solid, opaque border color. The one intentional break from "everything rounded" is the bottom-sheet pattern (address picker), which is rounded only on its top corners (`24px 24px 0 0`) to read correctly as a sheet rising from the bottom edge.

### Named Rules
**The Soft-Everywhere Rule.** Every interactive surface is rounded. A 0px/sharp-cornered button or card is off-system; use the smallest radius in the scale (14px) before ever using none.

## Components

### Buttons
- **Shape:** Pill (999px) for every button — primary and secondary alike. (Some app-shell screens still ship 16px-radius buttons; that is drift to converge, not a sanctioned secondary style — see Do's and Don'ts.)
- **Primary:** `linear-gradient(135deg, #ff6a1a, #f25c10)` background, white text, 56–58px height, Ember Glow shadow beneath it. `hover`/`active` lifts the button `translateY(-1px)`.
- **Secondary / Ghost:** Warm White background, Charcoal Ink text, 1px Ink Hairline border, no shadow at rest.

### Status Pills (unified)
A single canonical component now covers every status badge in the app — order status, delivery status, and any future status surface — rather than separate hand-rolled badge classes per screen.
- **Shape:** pill, `padding: 6px 14px`, Label typography (13px/800/uppercase/0.08em tracking).
- **State → color:** pending/waiting → Toasted Amber text on Amber Soft background; accepted/completed/positive → Sage text on Sage Soft background; in-progress → Ember text on Ember Soft background; cancelled/unavailable → Terracotta text on Terracotta Soft background.
- Adding a new status means adding a new state-color mapping to this one component, never a new pill implementation.

### Cards / Containers — Food/Dish Card (signature)
- **Corner Style:** 24px (`{rounded.xl}`).
- **Background:** Warm White, 1px Ink Hairline border, Ambient shadow.
- **Photo:** `aspect-ratio: 1.22/1`, `object-fit: cover`, plain rectangle (radius comes only from the parent card) — never a circular food photo. Card hover scales the photo to `1.03`.
- **Unavailable state:** desaturating filter + dark gradient overlay + a small Terracotta status pill top-left reading "unavailable" — never just grayed out with no label.
- **Internal Padding:** 16px.

### Inputs / Fields
- **Style:** 56–58px height, 18px radius (`{rounded.md}`), 1px Ink Hairline border, `#fffdfb` background.
- **Focus:** border tints to Ember + Focus Ring shadow (a hard ring, not a blur) — deliberately more precise-feeling than the Ember Glow used on buttons.

### Navigation
- **Top nav:** sticky, `backdrop-filter: blur(16px)` over a translucent cream background. Brand mark is a 28px gradient square (Ember → Ember Deep), 7px radius, 15px "C", with a CSS-generated "C" — there is no logo image file; the mark is pure CSS/typography. This exact size/radius/glyph-size trio is the one brand mark, used identically everywhere it appears (nav, auth pages' centered logo lockup, footer) — the auth pages once drifted to a 30px/8px/16px copy-pasted variant; if you find another one-off size, that's the same class of drift, not a sanctioned "large variant."
- **Nav tools:** pill-shaped buttons. Active link state is a 3px Ember underline via `::after`, not a background fill.
- **Mobile:** below 760px, navigation stacks into a column. **There is no bottom tab bar** — do not add one; it would break the established mobile pattern.

### Floating Action Buttons (signature)
Used for `back_fab` and `language_fab` — a distinct "floating over content" register, separate from in-flow buttons: fixed position (top-left/top-right), 40px circle or pill, 95%-alpha white, `backdrop-filter: blur(8px)`, a subtle Ambient shadow. Lighter and more transparent than any in-flow card or button.

### Address Picker Bottom Sheet (signature)
A bottom-sheet modal: `border-radius: 24px 24px 0 0`, the one place the heavier near-neutral **Sheet** shadow (`0 -20px 60px rgba(0,0,0,0.25)`) appears. Its extra visual weight is intentional — it's the system's cue for "modal," distinct from every other panel's soft Ambient shadow.

### Courier Payout Card (signature)
`repartidor_perfil.html`'s earnings display: a soft Ember gradient wash background (`linear-gradient(135deg, rgba(255,106,26,.1), rgba(255,106,26,.03))`), 18px radius, and a large Outfit 800 26px amount figure. This is the one place a currency amount gets Display-adjacent typographic weight — reserve that treatment for money the courier has actually earned, not for prices elsewhere in the app.

### Phone-Mockup Hero (signature)
The landing page's "how it works" moment: a literal illustrated phone frame containing miniature dish cards, used to show the product living inside a device rather than as a flat screenshot. This is a landing-page-only device; don't reuse the phone-chrome motif inside the logged-in app.

### Icon-Ring
A circular Ember-Soft badge with a centered inline SVG icon — used for the landing page's step-by-step explainer. Icons throughout the system are inline SVG (`stroke="currentColor"`, `stroke-width: 1.8–2`, 18–34px) — no icon font or library reference. Emoji is used, deliberately, only in informal/low-stakes decorative spots (contact rows, share sheets) — never for a primary functional icon.

### Live-Tracking Map Pins (signature)
`seguimiento.html`'s map uses three colors reserved *only* for pin markers, never for UI chrome elsewhere — buyer delivery point in orange (`#ff8a1f`), seller/pickup point via the brand mark, courier position in a dark marker (`#1f9d73`). These sit outside the main palette on purpose: pins need to read instantly against a live map tile, at a glance, at small size — the same constraint that makes cartographic marker colors different from interface colors everywhere. Don't converge them into Ember/Sage; don't reuse them outside this map.

## Do's and Don'ts

### Do:
- **Do** use pill radius (999px) for every button, chip, badge, FAB, and nav element — the one unified shape language.
- **Do** reserve Ember Orange for action, status, and price — as a gradient, glow, or thin line, never a large flat fill.
- **Do** tint every shadow — ink for resting/ambient, ember for primary actions — per the Warm Shadow Rule.
- **Do** pair Outfit (tight tracking) with Manrope; no third typeface.
- **Do** keep food photography as full-bleed rectangles inside a card's own radius, never circular crops.
- **Do** extend the unified Status Pill component with a new state-color mapping when a new status is needed.

### Don't:
- **Don't** introduce a new hex for ember, sage, ink, danger, or warning. The auth pages' `#ff6a17`/`#24262f`/`#73727c` family and the app-shell's other greens (`#1eae7a`, `#19a57b`, `#7ea86f`) are legacy drift, not alternate brand colors — converge to the values in this file. Check decimal `rgba()` too, not just hex literals — that's exactly how the green drift survived one prior "convergence" pass undetected.
- **Don't** ship a 16px-radius button anywhere going forward; pill is the one canonical button shape now.
- **Don't** add a bottom tab bar on mobile — navigation stacks into a column below 760px.
- **Don't** hand-roll a new badge/status class — extend the unified Status Pill instead.
- **Don't** use a neutral/pure-black shadow outside the Address Picker's Sheet exception, and don't use emoji for a primary functional icon.
