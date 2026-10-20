import sys
import socket
import uvicorn
from app.config import settings

# Ensure UTF-8 stdout encoding on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def detect_lan_ip() -> str:
    """Detect the host machine's active local IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a dummy broadcast address to identify the outbound routing interface
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    lan_ip = detect_lan_ip()
    port = settings.PORT

    print("\n" + "=" * 64)
    print(f"[*] {settings.APP_NAME}")
    print("=" * 64)
    print(f"  • Local URL:      http://localhost:{port}")
    print(f"  • LAN / Wi-Fi:    http://{lan_ip}:{port}")
    print(f"  • Health Check:   http://{lan_ip}:{port}/api/health")
    print(f"  • API Swagger:    http://{lan_ip}:{port}/docs")
    print(f"  • Storage Dir:    {settings.get_absolute_upload_dir()}")
    print("=" * 64 + "\n")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
