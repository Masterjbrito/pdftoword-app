# AITools - Design System Rules

## Project Overview

AITools is a Flask web application providing document conversion, PDF editing, media download, and text processing tools. The UI is server-rendered with Jinja2 templates and vanilla CSS.

## Technology Stack

- **Backend:** Python 3 + Flask
- **Templating:** Jinja2 (`.html` files in `templates/`)
- **Styling:** Single vanilla CSS file (`static/styles.css`)
- **JavaScript:** Vanilla JS, inline `<script>` blocks in templates
- **No frontend framework, no CSS framework, no build step**

## Project Structure

```
templates/          # Jinja2 HTML templates
  home.html         # Landing page with hero, categories mega-menu, ad grid
  tools.html        # All tools grid (ferramentas)
  tool_detail.html  # Individual tool detail page
  converter.html    # Legacy single-tool converter page
  index.html        # PDF-to-Word standalone page
  tools_list.html   # Tool listing
static/
  styles.css        # All CSS styles (single file)
web_app.py          # Flask app with all routes and tool logic
```

## Color Palette

- **Brand green:** `#0b7d52` (brand text, CTA buttons, hover accents)
- **Body background:** `linear-gradient(135deg, #d8ecff 0%, #f4f7fb 45%, #eef9f1 100%)`
- **Dark text:** `#1c2833`
- **Subtitle/muted text:** `#4b6073`
- **Hint text:** `#6a7785`
- **Nav link:** `#305067`
- **Heading secondary:** `#2f4f65`, `#27465b`, `#28465c`
- **Card border:** `#d8e1eb`
- **Input border:** `#bfd0e2`
- **Header border:** `#d4dee8`
- **Error background:** `#fde6e8`, border `#f1b8bf`, text `#7a1f2b`
- **Card/header background:** `#ffffff` (with `rgba(255,255,255,0.95)` + blur on sticky header)
- **Ad placeholder border:** `#8ca6bc` (dashed)

## Typography

- **Font family:** `"Segoe UI", Tahoma, sans-serif`
- **h1:** `2rem` (mobile: `1.6rem`)
- **h2 in cards:** `1.05rem`
- **Labels:** `0.94rem`, `font-weight: 600`
- **Body/buttons:** `0.95rem`-`0.98rem`
- **Brand:** `1.2rem`, `font-weight: 800`, `letter-spacing: 0.4px`

## Spacing & Layout

- **Max content width:** `min(1200px, 100%)`
- **Page padding:** `20px` (mobile: `14px`)
- **Card padding:** `16px`-`28px`
- **Card border-radius:** `12px`
- **Input/button border-radius:** `8px`-`10px`
- **Grid gaps:** `10px`-`16px`
- **Three-column layout:** `220px | flex | 220px` (collapses to single column below `980px`)

## Component Patterns

### Cards
All cards share: `border: 1px solid #d8e1eb; border-radius: 12px; background: #ffffff;`
- `.hero-card` — large padding (`28px`), box-shadow
- `.feature-card` — standard padding (`16px`)
- `.tool-card` — standard padding (`16px`), contains `<form>` with `display: grid; gap: 10px`
- `.ad-box` — dashed border, placeholder for ads

### Buttons
```css
border: 0; border-radius: 10px; padding: 11px 14px;
background: #0b7d52; color: white; font-weight: 700;
```

### Form Inputs
```css
width: 100%; border: 1px solid #bfd0e2; border-radius: 8px;
padding: 10px; font-size: 0.95rem; background: #fff;
```

### Header
- Sticky, `backdrop-filter: blur(8px)`, semi-transparent white
- Brand link + nav links in a flex row
- Mega-menu (`.hover-panel`) shown on hover with CSS grid (4 columns)

## Responsive Breakpoints

- `max-width: 980px` — collapse three-column to single, hide sidebars
- `max-width: 680px` — stack header, full-width nav, smaller headings

## Figma MCP Integration Rules

### Required Flow (do not skip)

1. Run `get_design_context` first to fetch the structured representation for the exact node(s)
2. If the response is too large or truncated, run `get_metadata` to get the high-level node map, then re-fetch only the required node(s) with `get_design_context`
3. Run `get_screenshot` for a visual reference of the node variant being implemented
4. Only after you have both `get_design_context` and `get_screenshot`, download any assets needed and start implementation
5. Translate the output into this project's conventions: **vanilla CSS classes in `static/styles.css`** and **Jinja2 templates in `templates/`**
6. Validate against Figma for 1:1 look and behavior before marking complete

### Implementation Rules

- IMPORTANT: Treat Figma MCP output (React + Tailwind) as a design reference, NOT final code
- IMPORTANT: Convert all Tailwind utility classes to vanilla CSS in `static/styles.css`
- IMPORTANT: Never hardcode colors — use the palette defined above
- Reuse existing CSS classes (`.card`, `.tool-card`, `.feature-card`, `.ad-box`, `.hero-card`, etc.) instead of creating duplicates
- Match the existing naming convention: lowercase, hyphenated class names (`.tool-card`, `.hero-card`, `.ad-box`)
- Keep all JS inline in `<script>` blocks at the bottom of templates (no external JS files)
- Templates must extend the existing header/nav pattern with `.site-header > .header-inner > .brand + .main-nav`
- Maintain responsive behavior with the existing breakpoints (`980px`, `680px`)

## Asset Handling

- IMPORTANT: If the Figma MCP server returns a localhost source for an image or SVG, use that source directly
- IMPORTANT: DO NOT import/add new icon packages — all assets should come from the Figma payload
- IMPORTANT: DO NOT use or create placeholders if a localhost source is provided
- Store downloaded assets in `static/` directory
- Currently there are no images or icons — the project uses text-only UI

## Project-Specific Conventions

- All routes are defined in `web_app.py` — no blueprints
- Tool forms POST to `/tools/<slug>` endpoints
- File uploads go to `uploads/`, outputs to `outputs/`, temp files to `temp/`
- Templates use Portuguese labels for the UI (e.g., "Converter", "Funcionalidades", "Publicidade")
- Ad placeholders use dashed borders with descriptive size text (e.g., "Ad 300x250")
- The app supports 18+ tools organized in categories: Conversion, PDF Editing, Security, Text & Media
