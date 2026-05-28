from pathlib import Path

import streamlit.components.v1 as components

_LOCAL_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"
_ROOT_BUILD_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_BUILD_DIR = _LOCAL_BUILD_DIR if _LOCAL_BUILD_DIR.exists() else _ROOT_BUILD_DIR

_manpur_hero = components.declare_component("manpur_hero", path=str(_BUILD_DIR))


def manpur_hero(scene: str = "market-hero", height: int = 320, motion: str = "auto", key: str | None = None):
    """Render the Digital Manpur hero component inside Streamlit.

    Preferred local build path:
    streamlit_component/manpur_hero/frontend/dist

    Fallback path:
    frontend/dist
    """

    return _manpur_hero(scene=scene, height=height, motion=motion, key=key, default=None)
