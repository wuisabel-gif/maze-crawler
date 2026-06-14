# Maze Crawler — UI spec

The design language for the arcade dev-log site (`site/index.html`). This is the
single source of truth for sizes, colors, transparency, backgrounds, glows and
motion. Everything is defined as CSS custom properties in `:root` plus a few
canvas constants in the maze script. Change values here first, then mirror them
in the code.

Concept in one line: **a CRT arcade cabinet running a replay** — deep blue-black
screen, scanlines, a saturated HUD palette, hand-drawn display type over rounded
UI type, pink "energy" as the player's color.

---

## 1. Color tokens (OKLCH)

OKLCH = `oklch(Lightness Chroma Hue)`. L is 0–1, C is ~0–0.37, H is 0–360.
Transparency is the `/ alpha` at the end (0–1).

| Token | Value | Role | Notes |
|---|---|---|---|
| `--bg` | `oklch(0.135 0.022 266)` | page background | the CRT screen, "on" |
| `--bg2` | `oklch(0.105 0.020 266)` | deepest background | inside screens/footers |
| `--panel` | `oklch(0.175 0.026 266)` | card / panel fill | one step up from bg |
| `--panel2` | `oklch(0.205 0.028 266)` | raised panel | hover / nested |
| `--ink` | `oklch(0.975 0.01 95)` | primary text + headings | ~16:1 on bg |
| `--ink2` | `oklch(0.85 0.015 95)` | body text | ~9:1 on bg, the default reading color |
| `--muted` | `oklch(0.66 0.03 266)` | labels, meta, captions | ~4.6:1 — secondary only, never long body |
| `--pink` | `oklch(0.71 0.215 352)` | **P1 / energy / you** | the hero accent |
| `--cyan` | `oklch(0.82 0.135 205)` | info / vision / walls | second accent |
| `--gold` | `oklch(0.84 0.155 82)` | score / coins | numbers, HI-SCORE |
| `--green` | `oklch(0.84 0.19 150)` | win / go / escort | positive states |
| `--red` | `oklch(0.65 0.235 25)` | danger / scroll / game over | the dark that chases you |

**Transparency of lines (borders):**

| Token | Value | Use |
|---|---|---|
| `--line` | `oklch(1 0 0 / 0.14)` | hairline dividers, faint card borders |
| `--line2` | `oklch(1 0 0 / 0.28)` | panel borders, button borders, the visible frame |

Rule of thumb: borders are pure white at **14%** (quiet) or **28%** (structural).
Never a solid colored border — color lives in glows and fills, not outlines.

---

## 2. Background layers (transparency stack)

The page has three fixed background layers, bottom to top:

1. **Glow field** (`body::before`, `z-index:-2`) — two radial color washes + a
   vertical gradient:
   - top wash: `radial-gradient(120% 75% at 50% -8%, oklch(0.30 0.10 330 / 0.40), transparent 60%)`
   - corner wash: `radial-gradient(90% 60% at 108% 112%, oklch(0.30 0.13 205 / 0.16), transparent 55%)`
   - base: `linear-gradient(--bg → --bg2)`
2. **Pixel grid** (`body::after`, `z-index:-1`) — a 34px grid of white lines at
   **2.2% opacity**, the whole layer at **50% opacity**, masked to fade out below
   the fold: `mask-image: radial-gradient(120% 100% at 50% 0%, #000 30%, transparent 90%)`.
3. **CRT overlay** (`.crt`, `z-index:60`) — see §6.

Panel fills are **opaque** (`--panel`), not translucent. The only translucent
surfaces are the sticky HUD (`oklch(0.105 0.02 266 / 0.82)` + `backdrop-filter: blur(8px)`)
and the score ribbon band (`oklch(0.10 0.02 266 / 0.6)`). Glassmorphism is
deliberately avoided everywhere else.

---

## 3. Typography

| Family | Token | Use | Notes |
|---|---|---|---|
| ALK Life (hand-drawn) | `--display` | h1/h2, big playful moments, "GAME OVER" | letter-spacing `+0.01em`; never for body |
| ALK Rounded | `--ui` | body, UI labels, card titles | the workhorse; legible at 0.88–1.1rem |
| JetBrains Mono | `--mono` | scores, tags, code chips, HUD readouts | weights 400/500/700 |

**Type scale (clamp = min, fluid, max):**

| Element | Size |
|---|---|
| Hero `h1` | `clamp(3.4rem, 1.8rem + 8vw, 7rem)` line-height `.92` |
| Section `h2` | `clamp(2rem, 1.3rem + 3.2vw, 3.7rem)` |
| Lede / lead `p` | `clamp(1.05rem, 1rem + .4vw, 1.25rem)` |
| Body | `clamp(1rem, .95rem + .2vw, 1.1rem)` line-height `1.62` |
| Card title `h3` | `1.05rem` weight 700 |
| Small / caption | `0.88rem` |
| Tag / HUD label | `0.66–0.72rem`, tracking `.08–.18em`, uppercase |

Body line length capped at ~62ch via `max-width` on `.shead p` and card `p`.

---

## 4. Spacing, radius, layout

| Property | Value |
|---|---|
| Page max width | `--maxw: 1180px` |
| Page side padding | `--pad: clamp(1rem, 4.5vw, 3.5rem)` |
| Section vertical padding | `clamp(3rem, 7vw, 5.5rem)` |
| Card padding | `clamp(1.1rem, 2.5vw, 1.6rem)` |
| Card gap (grids) | `clamp(.7rem, 2vw, 1.3rem)` |
| Radius — panels/screens | `6–8px` (hard-ish, arcade) |
| Radius — cards | `7px` |
| Radius — buttons | `5px` |
| Radius — tags/chips | `3px` |

Responsive grid default: `repeat(auto-fit, minmax(220–250px, 1fr))`. Hero and
two-column sections collapse to one column at `880–900px`.

---

## 5. Borders, shadows, glows

**Panel frame** (the arcade-window look):
```
border: 2px solid var(--line2);            /* 28% white, 2px */
box-shadow: 0 0 0 4px var(--bg),           /* matte gap ring */
            0 18px 50px -24px #000;         /* soft drop */
```

**Accent glow** (buttons, mines, factory). Glow = a colored `box-shadow` or
`drop-shadow` with **no spread offset**, sized by blur:

| Element | Glow |
|---|---|
| Primary button | `0 0 24px -4px var(--pink)`, hover `0 0 34px 0 var(--pink)` |
| Card hover | `0 0 26px -10px <accent>` |
| Score number | `text-shadow: 0 0 18px oklch(<accent> / 0.4)` |
| Title `CRAWLER` | `0 0 40px oklch(0.71 0.215 352 / .55)` + `4px 4px 0 oklch(0.82 .135 205 / .25)` offset |

Keep glow blur in the **18–40px** band; alpha **0.3–0.55**. Above that it turns
to haze and kills contrast.

---

## 6. CRT overlay (`.crt`)

Three stacked effects, all `pointer-events:none`, fixed, `z-index:60`:

| Effect | Spec |
|---|---|
| Scanlines | `repeating-linear-gradient(transparent 0 2px, oklch(0 0 0/0.22) 2px 3px)` at layer `opacity: 0.5` → a ~1px black line every 3px, effective darkness ~11% |
| Vignette (inset) | `box-shadow: inset 0 0 180px 30px oklch(0 0 0/0.55)` |
| Vignette (radial) | `radial-gradient(130% 120% at 50% 50%, transparent 62%, oklch(0 0 0/0.4))` |
| Flicker | `opacity` 1 → .92 → .97 over 5s, `steps(60)`; disabled under reduced-motion |

To dial intensity: scanline darkness = the `0.22`; overall presence = the layer
`opacity: 0.5`. Vignette weight = the `0.55` and `0.4` alphas.

---

## 7. The attract-mode maze screen (canvas) — tuning guide

This is the screen in the reference. Canvas is `#maze`, ~`clamp(320px, 44vh, 440px)`
tall, drawn at devicePixelRatio. Grid is **16 columns** (`COLS = 16`), so one
`cell = canvasWidth / 16`. All sizes below are **multiples of `cell`** so they
scale. Colors are `rgba()` (canvas can't read OKLCH directly).

### Current values

| Element | Size | Color / transparency |
|---|---|---|
| Cell grid outline | 1px stroke | `rgba(120,150,200, 0.06)` — barely-there blue |
| Wall (north edge) | 1px stroke | `rgba(95,213,232, 0.30)` — cyan, on ~38% of cells |
| Wall (east edge) | 1px stroke | `rgba(95,213,232, 0.24)` — cyan, on a thin band |
| Mine glow halo | radius `cell × (0.16–0.32) × 3.2` | radial `pink → rgba(236,70,176,0.30) → transparent` |
| Mine core | square `cell × 0.8 × rad` | solid pink |
| Factory body | square `cell × 0.64` (r = `cell×0.32`) | `#efece4` (warm white) |
| Factory glow | radius `cell × 0.32 × 4` | radial `rgba(239,236,228, 0.45) → transparent` |
| Escort marker | square `cell × 0.2` | `--green` |
| Scroll danger band | height `cell × 2.5` | linear `rgba(190,30,30, 0.55) → 0` |
| Scroll line | 2px | solid `--red` |
| Fog (north) | height `cell × 3` | linear `rgba(18,16,30, 0.95) → 0` |

### What I'd change to make it look better (recommended values)

1. **Tighten the factory glow** — right now it's a big soft white blob (radius
   `4× r`, alpha `0.45`). Drop to **radius `2.6× r`, alpha `0.32`**, and tint it
   pink not white: inner stop `rgba(255,210,235, 0.40)`. A smaller, hotter,
   colored glow reads as "energy," not "blur."
2. **Make walls feel pixel-built** — increase wall contrast and add the *south*
   edges too so corridors close. Wall alpha **0.30 → 0.42**, and add a 1px inner
   shadow line at `rgba(0,0,0,0.5)` just below each wall for a 3D "tile" edge.
3. **Brighten the grid slightly + snap to pixels** — grid `0.06 → 0.08`, and
   `Math.round()` all x/y so lines stay crisp at any DPR (no half-pixel blur).
4. **Mine = a 2×2 pixel sprite, not a soft dot** — keep the halo but make the
   core a small **dithered square cluster** (4 pink pixels) so it reads arcade.
   Add a slow `0.6s` pulse on the halo alpha (`0.30 ↔ 0.45`).
5. **Scroll danger: add a dither edge** — instead of a smooth gradient top, draw
   a 1–2 row band of alternating red pixels above the solid band (Bayer/checker)
   so the "lava" has a retro hard edge. Bump the solid line to **3px** with a
   `0 0 10px var(--red)` glow.
6. **Optional bloom pass** — after drawing, `ctx.globalCompositeOperation =
   'lighter'` and redraw the factory + mines at `0.25` alpha, blurred, for a
   cheap CRT bloom. Gate behind `prefers-reduced-motion: no-preference`.
7. **Screen curvature (subtle)** — a `border-radius` on the canvas plus an inset
   highlight `box-shadow: inset 0 1px 0 rgba(255,255,255,0.06)` sells the glass.

Target feel: fewer, **harder, brighter** pixels with **tighter, hotter** glows —
not more haze. Keep total bright area under ~15% of the screen so the dark reads
as menacing.

---

## 8. Motion

| Property | Value |
|---|---|
| Easing (all) | `cubic-bezier(0.22, 1, 0.36, 1)` (ease-out-quint) |
| Reveal on scroll | `opacity 0→1`, `translateY 16px→0`, `0.6s` |
| Button press | `translateY(2px)` on `:active`, `0.12s` |
| Bar fill | `transform: scaleX()` `1.1s` |
| Blink (insert coin) | `1.1s steps(2)` |
| Maze scroll speed | `dt × 0.0016` rows/ms |
| Trail draw (ascent) | `9s` loop |

Every animation has a `@media (prefers-reduced-motion: reduce)` fallback
(reveals show instantly, blink/flicker/trail/climber stop, bars fill with no
transition). Keep it that way.

---

## 9. What would help me push it further

If you want a bigger jump in polish, the highest-value inputs from you:

1. **A real replay** — a short GIF or a recorded action log from one game, so the
   attract screen shows *actual* play instead of a procedural fake.
2. **Intensity preference** — scanlines/glow/flicker: subtle, medium, or
   full-arcade? (Current = subtle-medium.) One word and I'll retune §6–§7.
3. **A pixel display font** (optional) — if you want true arcade lettering for the
   HUD labels (e.g. "Press Start 2P"), drop one in `site/fonts/` and I'll wire it
   to the `--mono`/tag layer while keeping ALK for the big type.
4. **Accent priority** — should pink stay the dominant color, or do you want gold
   (score) to lead? That decides the 60% color.
