---
name: Vigilance SOC Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#5c403c'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#916f6b'
  outline-variant: '#e6bdb8'
  surface-tint: '#bf0715'
  primary: '#b70011'
  on-primary: '#ffffff'
  primary-container: '#dc2626'
  on-primary-container: '#fff6f5'
  inverse-primary: '#ffb4ab'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#004ed0'
  on-tertiary: '#ffffff'
  tertiary-container: '#2d68f0'
  on-tertiary-container: '#f8f7ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad6'
  primary-fixed-dim: '#ffb4ab'
  on-primary-fixed: '#410002'
  on-primary-fixed-variant: '#93000b'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#003ea8'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  code-sm:
    fontFamily: monospace
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-md: 1rem
  margin: 1rem
  margin-lg: 1.5rem
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

This design system establishes a high-density, authoritative command-center aesthetic tailored for enterprise Security Operations Centers (SOC), incident response teams, and threat intelligence analysts. The design language is rooted in **Corporate / Modern Precision**—unflinching, structured, and clinically efficient.

The user experience prioritizes operational clarity under pressure. Information architecture is utilitarian and hierarchical: high-contrast surfaces separate signal from telemetry noise, while intense crimson anchors focus immediate attention toward critical threat vectors, anomalies, and containment actions. The emotional response is one of surgical control, absolute reliability, and rapid cognition.

## Colors

The palette is engineered for prolonged operational focus in high-glare control rooms and multi-monitor setups. It relies on clean, high-luminance slate-tinted white canvases, disciplined structural slates, and surgical semantic indicators.

### Base Canvases & Structural Neutrals
- **Canvas Base:** `#FFFFFF` serves as primary container fill.
- **Canvas Alternate:** `#F8FAFC` provides subtle contrast for global viewports, sub-panels, and navigation rails.
- **Borders & Dividers:** `#E2E8F0` defines primary structural boundaries, with `#CBD5E1` reserved for focused elements, column splitters, and table headers.
- **Typography & Structural Slates:** `#0F172A` (Primary Slate 900), `#334155` (Secondary Slate 700), and `#64748B` (Muted Slate 500) provide distinct semantic hierarchy without muddying visual clarity.

### Semantic & Risk Anchors
- **Primary / Critical (Crimson Red):** `#DC2626` (with `#BE123C` for active states and `#FEF2F2` for soft risk washes) anchors high-severity alerts, destructive interventions, and urgent incident thresholds.
- **Operational / Healthy (Emerald):** `#059669` (with `#ECFDF5` container fills) confirms verified workloads, healthy nodes, and mitigated threats.
- **Warning / Degraded (Amber):** `#D97706` (with `#FFFBEB` container fills) signifies pending validations, perimeter alerts, and system anomalies.
- **Informational / Telemetry (Blue):** `#2563EB` indicates routine network transactions, active filters, and informational logs.

## Typography

Typography in this design system emphasizes extreme tabular legibility and rapid skimming. Built on `Inter`, the type hierarchy relies on controlled font weights and tight tracking for high information density without sacrificing optical balance.

- **Tabular Figures:** Always apply `font-feature-settings: "tnum"` to numeric metrics, packet counts, threat counters, and IP indicators to eliminate horizontal jitter during live telemetry polling.
- **Monospace Usage:** Use platform-native monospace stacks (`ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `Consolas`) for machine artifacts: SHA-256 hashes, raw packet decodes, payload strings, and shell output.
- **Capitalization Rules:** Reserve all-caps strictly for small technical badges (`label-sm`), table headers, and HTTP/SOC protocol verbs (`GET`, `POST`, `SIGINT`, `CVE`).

## Layout & Spacing

This design system uses a high-density, multi-pane command-console architecture optimized for 1440px+ enterprise displays, backed by a responsive 12-column grid.

### Layout Principles
- **Shell Architecture:** Fixed left-hand global tool rail (56px collapsed / 240px expanded), multi-split operational workspace, and dynamic slide-out threat inspection drawer (380px–480px width).
- **Density Control:** The base rhythmic unit is 4px. Operational interfaces rely predominantly on `space-xs` (4px) and `space-sm` (8px) gaps to ensure high data volume within primary viewports, preventing excessive vertical scrolling during incident triage.
- **Grid & Panels:** Use 12-column layouts with `gutter` (12px) for analytical dashboards. Card widgets maintain internal padding of `space-md` (12px) or `space-lg` (16px).
- **Responsive Adaptations:** On viewports below 1024px, right-side inspection drawers transition into modal bottom sheets, and secondary metric widgets collapse into vertical stacked queues.

## Elevation & Depth

Visual hierarchy is maintained via clean structural lines and subtle, low-opacity ambient shadows. The system intentionally avoids deep skeuomorphic drop shadows, preserving an architectural and uncluttered UI.

### Elevation Levels
- **Level 0 (Flat Canvas):** `#FFFFFF` surfaces inset within a `#F8FAFC` global frame, separated by a crisp 1px `#E2E8F0` border.
- **Level 1 (Card & Module Resting):** Used for workspace data widgets, triage tables, and metric cards. Border: `1px solid #E2E8F0`; Shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.03)`.
- **Level 2 (Interactive Floating / Active Hover):** Used for hovered cards, active drag handles, and docked control ribbons. Border: `1px solid #CBD5E1`; Shadow: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`.
- **Level 3 (Overlays & Slide-out Panels):** Used for contextual context menus, filter dropdowns, and inspector sheets. Shadow: `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03)`.

## Shapes

The design system employs a soft, disciplined corner profile (`roundedness: 1` / 4px base radius) to establish a crisp, computational visual boundary.

- **Base Radius (`0.25rem` / 4px):** Standard buttons, text fields, chips, status pills, table cells, and internal card compartments.
- **Container Radius (`0.5rem` / 8px):** Primary dashboard modules, data grid containers, modal dialogue windows, and floating command panels.
- **Sharp Exclusions (`0px`):** Split-view separators, breadcrumb dividers, active status indicator side-stripes, and continuous log streams to maintain technical precision.

## Components

### Buttons
- **Primary (Action / Mitigate):** Solid crimson `#DC2626` background, white bold text, 4px corner radius. Hover: `#BE123C`. Focus: Outline 2px `#DC2626` with 2px white offset.
- **Secondary (Inspect / Query):** `#FFFFFF` surface with `1px solid #CBD5E1` border, `#0F172A` text. Hover: `#F8FAFC` background with `#0F172A` border.
- **Ghost / Utility:** Transparent background, `#64748B` text. Hover: `#F1F5F9` background, `#0F172A` text. Height defaults: 32px standard, 28px compact.

### Status Badges & Threat Indicators
- Small, high-contrast, compact pills (20px height) using `label-sm` font.
- **Critical (P0 / Active Breach):** `#FEF2F2` background, `#991B1B` text, `1px solid #FECACA` border, accompanied by a solid `#DC2626` 6px pulse dot.
- **Verified / Clean:** `#ECFDF5` background, `#065F46` text, `1px solid #A7F3D0` border.
- **Warning / Anomalous:** `#FFFBEB` background, `#92400E` text, `1px solid #FDE68A` border.

### Tables & Live Data Grids
- **Header:** `#F8FAFC` background, `1px solid #E2E8F0` bottom edge, uppercase 11px bold text (`#64748B`).
- **Row Architecture:** 36px fixed row height in dense mode (44px in standard mode). Alternating border: `1px solid #F1F5F9`. Hover state: `#F8FAFC`.
- **Active Incident Row:** Inset left border: `3px solid #DC2626` with a soft `#FEF2F2` background tint.

### Inputs & Filters
- Compact height (32px), `#FFFFFF` fill, `1px solid #CBD5E1` border.
- Placeholder text: `#94A3B8`.
- Focus state: `1px solid #0F172A` with a soft slate glow (`box-shadow: 0 0 0 1px #0F172A`).

### Cards & Telemetry Containers
- Structured with an explicit header bar (36px height) featuring an icon, module title in `headline-sm`, quick-action buttons, and a bottom border of `1px solid #E2E8F0`.
- Card body uses padding of `12px` or `16px` depending on nested chart or log view density.