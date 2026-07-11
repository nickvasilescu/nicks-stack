"""Local Orgo Desktop API client (loopback :8080).

When Hermes runs inside an Orgo VM, computer-use actions should hit
http://127.0.0.1:8080 (orgo-desktop-api) with the per-VM VNC password,
not the cloud MCP hop.
"""

from .client import DesktopAPIError, OrgoDesktopClient, discover_token, is_colocated

__all__ = [
    "DesktopAPIError",
    "OrgoDesktopClient",
    "discover_token",
    "is_colocated",
]
