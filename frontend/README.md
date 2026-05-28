# Digital Manpur UI Shell

This folder contains a standalone React + Vite demo shell for the hybrid 3D MandiTrade interface.

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Modes

- CSS fallback only: comment out `Hero3D` usage in route pages and keep the shared background system.
- Hybrid mode: keep `Hero3D` on `LoginPage`, `MarketplacePage`, and `DashboardPage`.
- If WebGL is unavailable, `Hero3D` automatically shows a static fallback panel.

## Streamlit adaptation

- Keep backend logic in the existing Streamlit codebase.
- Use the CSS token and background files as a visual reference for Streamlit HTML-rendered panels.
- Build this frontend and copy its `dist` output into `streamlit_component/manpur_hero/frontend/dist` when you want the standalone hero component available inside Streamlit.
- The Python wrapper lives at `streamlit_component/manpur_hero/__init__.py`.
