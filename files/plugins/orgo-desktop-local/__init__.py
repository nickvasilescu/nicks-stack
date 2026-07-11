"""orgo-desktop-local — Hermes tools for the in-VM Orgo Desktop API.

Follows the official Hermes user-plugin pattern:
  ~/.hermes/plugins/<name>/{plugin.yaml,__init__.py}
  register(ctx) -> ctx.register_tool(...)

Docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins
      https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
Bundled reference: plugins/spotify (ctx.register_tool + toolset + check_fn)
"""

from __future__ import annotations

from .tools import (
    DOCTOR_SCHEMA,
    SCREENSHOT_SCHEMA,
    CLICK_SCHEMA,
    DRAG_SCHEMA,
    CLICK_PATH_SCHEMA,
    TYPE_SCHEMA,
    KEY_SCHEMA,
    BASH_SCHEMA,
    SCROLL_SCHEMA,
    OPEN_URL_SCHEMA,
    WAIT_SCHEMA,
    check_desktop_available,
    handle_doctor,
    handle_screenshot,
    handle_click,
    handle_drag,
    handle_click_path,
    handle_type,
    handle_key,
    handle_bash,
    handle_scroll,
    handle_open_url,
    handle_wait,
)

_TOOLS = (
    ("orgo_desktop_doctor", DOCTOR_SCHEMA, handle_doctor, "🩺"),
    ("orgo_desktop_screenshot", SCREENSHOT_SCHEMA, handle_screenshot, "📸"),
    ("orgo_desktop_click", CLICK_SCHEMA, handle_click, "🖱"),
    ("orgo_desktop_drag", DRAG_SCHEMA, handle_drag, "↔"),
    ("orgo_desktop_click_path", CLICK_PATH_SCHEMA, handle_click_path, "↦"),
    ("orgo_desktop_type", TYPE_SCHEMA, handle_type, "⌨"),
    ("orgo_desktop_key", KEY_SCHEMA, handle_key, "⏎"),
    ("orgo_desktop_bash", BASH_SCHEMA, handle_bash, "💻"),
    ("orgo_desktop_scroll", SCROLL_SCHEMA, handle_scroll, "↕"),
    ("orgo_desktop_open_url", OPEN_URL_SCHEMA, handle_open_url, "🌐"),
    ("orgo_desktop_wait", WAIT_SCHEMA, handle_wait, "⏳"),
)


def register(ctx) -> None:
    """Register Desktop API tools into the global Hermes tool registry."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="orgo_desktop",
            schema=schema,
            handler=handler,
            check_fn=check_desktop_available,
            emoji=emoji,
            description=schema.get("description", name),
        )
