"""
Secure LAN Chat & File Sharing System — Production LAN Runner
============================================================
Launches the single-origin FastAPI application server configured for
LAN access and offline operation on Windows 11.
"""

import os
import sys
import socket
from pathlib import Path

# Add backend directory to sys.path so app modules are discoverable
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import uvicorn
    from app.config import settings
    from app import __version__
except ImportError as err:
    print(f"\n[ERROR] Failed to import backend dependencies: {err}")
    print("Please install requirements first: pip install -r backend/requirements.txt\n")
    sys.exit(1)


def get_local_lan_ips() -> list[str]:
    """
    Detect all non-loopback IPv4 addresses associated with local network adapters.
    Prioritizes the primary default route IP if available.
    """
    ips = []
    # 1. Primary outbound adapter (UDP socket trick without sending packets)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # 8.8.8.8 does not need to be reachable; kernel routing table selects default interface
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            ips.append(primary)
    except Exception:
        pass

    # 2. Enumerate all adapter addresses via hostname
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            addr = info[4][0]
            if (
                addr not in ips
                and not addr.startswith("127.")
                and not addr.startswith("169.254.")
            ):
                ips.append(addr)
    except Exception:
        pass

    return ips or ["127.0.0.1"]


def print_startup_banner(host: str, port: int, lan_ips: list[str]):
    """Print informative Windows LAN access and troubleshooting banner."""
    print("=" * 78)
    print(f" SECURE LAN CHAT & FILE SHARING — v{__version__} [Windows 11 LAN Mode]")
    print("=" * 78)
    print(f" Server Interface : {host}:{port}")
    print(f" Single-Origin UI : {'READY (frontend/dist)' if (FRONTEND_DIST / 'index.html').is_file() else 'MISSING (Run: cd frontend && npm run build)'}")
    print(f" Offline Capable  : YES (Zero external CDNs or cloud dependencies)")
    print("-" * 78)
    print(" [Host Local Access]")
    print(f"   * http://localhost:{port}")
    print(f"   * http://127.0.0.1:{port}")
    print()
    print(" [LAN Access for Second Devices (Phones, Laptops, Tablets on same Wi-Fi)]")
    for ip in lan_ips:
        print(f"   * http://{ip}:{port}")
    print("-" * 78)
    print(" [Windows Firewall Quick Note]")
    print(f"   If other devices cannot connect, allow inbound TCP port {port} in Windows Firewall:")
    print(f"   PowerShell (Admin): New-NetFirewallRule -DisplayName 'Secure LAN Chat' \\")
    print(f"                       -Direction Inbound -LocalPort {port} -Protocol TCP -Action Allow")
    print("-" * 78)
    print(" [Clean Shutdown]")
    print("   Press Ctrl+C to gracefully stop the server and release connections.")
    print("=" * 78 + "\n")


def main():
    host = os.getenv("HOST", settings.HOST)
    port = int(os.getenv("PORT", settings.PORT))
    lan_ips = get_local_lan_ips()

    # Verify frontend build
    if not (FRONTEND_DIST / "index.html").is_file():
        print("\n[WARNING] Compiled frontend not found at frontend/dist/index.html")
        print("To access the web chat UI, build the frontend first:")
        print("  cd frontend && npm run build\n")

    print_startup_banner(host, port, lan_ips)

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=True,
            reload=False,
        )
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped cleanly via keyboard interrupt (Ctrl+C).")


if __name__ == "__main__":
    main()
