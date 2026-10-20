# Secure LAN Chat & File Sharing System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-58%20Passed%20(100%25)-success.svg)](TEST_REPORT.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A high-performance, self-hosted web application for real-time messaging, private conversations, and reliable local file transfers across a Local Area Network (LAN). Architected specifically for college laboratories, campus Wi-Fi, and private network environments with **zero external cloud or internet dependencies**.

---

## 1. System Overview

Secure LAN Chat bridges modern browser clients with an asynchronous Python backend through a unified **single-origin architecture**. Hosted on a single Windows 11 computer, any smartphone, tablet, or laptop connected to the same Wi-Fi or Ethernet subnet can open a browser, register an account, and communicate with other connected peers.

```
+-----------------------------------------------------------------------------+
|                          LOCAL SUBNET (Wi-Fi / Ethernet)                    |
|                                                                             |
|   [ Host PC: Windows 11 ]         [ Client 2: Mobile Phone ]   [ Client 3 ] |
|    http://localhost:8000           http://172.16.235.234:8000   http://...  |
|            |                                   |                    |       |
|            +------------------+----------------+--------------------+       |
|                               |                                             |
|                               v                                             |
|                 [ Inbound TCP Port 8000 ]                                   |
|                               |                                             |
|      +------------------------v------------------------+                    |
|      |         FastAPI Single-Origin Server            |                    |
|      |                                                 |                    |
|      |   * Serves React SPA (frontend/dist)            |                    |
|      |   * Serves REST API (/api/*)                    |                    |
|      |   * Manages Full-Duplex WebSockets (/ws/chat)   |                    |
|      |   * Streams Uploads/Downloads (storage/uploads) |                    |
|      |   * Persists Data in SQLite WAL (data.db)       |                    |
|      +-------------------------------------------------+                    |
+-----------------------------------------------------------------------------+
```

---

## 2. Key Features

* **Single-Origin Deployment**: FastAPI serves the production frontend bundle (`frontend/dist`), REST endpoints, and WebSocket channels on a single port (`8000`), completely eliminating cross-origin cookie quirks and multi-port firewall rules.
* **100% Offline Capable**: Zero runtime external dependencies. Google Fonts and external CDNs have been removed in favor of clean offline system font stacks (`Segoe UI`, `ui-sans-serif`).
* **Real-Time Full-Duplex WebSockets (RFC 6455)**: Sub-millisecond latency messaging with automatic heartbeat pings (every 20s), typing indicators, and presence tracking.
* **Private DMs & LAN Broadcast**: Public broadcast room (`#general-lan`) for all connected subnet users alongside horizontally isolated 1-to-1 direct messaging.
* **Reliable Chunked File Transfers**: Drag-and-drop file sharing supporting uploads up to 50 MB, streaming chunk writes, SHA-256 checksum verification, and authorized downloads.
* **Persistent ACID Storage**: SQLite database operating in Write-Ahead Logging (`WAL`) mode with foreign key integrity. Messages and metadata survive server restarts.
* **Defense-in-Depth Security**:
  * Passwords securely hashed with **Argon2id**.
  * Cryptographically random 256-bit session cookies with `HttpOnly` and `SameSite=Lax`.
  * Sliding-window rate limiters defending against authentication brute force, chat spam, and upload flooding.
  * Cross-Site WebSocket Hijacking (CSWSH) defense via RFC 1918 private subnet origin validation.
  * Strict HTTP security headers (`nosniff`, `DENY`, and Content Security Policy).
* **Automated Network Discovery**: Startup scripts inspect local network interfaces and print ready-to-use URLs for host and second-device access.

---

## 3. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend Framework** | React 18 + Vite | Component-driven UI, fast production bundling, responsive layout. |
| **Frontend Styling** | Custom CSS3 Design System | Charcoal dark theme default, light theme support, zero heavy UI frameworks. |
| **Icons** | Lucide React | Pre-bundled lightweight SVG icons with zero runtime CDN calls. |
| **Backend Framework** | Python 3.10+ / FastAPI | High-throughput asynchronous ASGI framework with native async/await. |
| **ASGI Server** | Uvicorn | High-performance ASGI web server implementing HTTP/1.1 and RFC 6455 WebSockets. |
| **Database** | SQLite 3 via SQLAlchemy | Zero-configuration ACID database in WAL mode; zero cloud database dependencies. |
| **Password Hashing** | Argon2id (`argon2-cffi`) | Memory-hard, state-of-the-art password hashing algorithm. |
| **Testing** | Pytest + Starlette TestClient | 58 comprehensive automated tests covering integration, security, and reliability. |

---

## 4. Project Directory Structure

```text
Secure-LAN-Chat/
│
├── run_server.py                 # Single-origin production launcher with auto-IP detection
├── Start-LanServer.ps1           # Windows 11 PowerShell launcher with firewall checking
├── start_lan_server.bat          # Windows double-click batch startup script
├── .gitignore                    # Protects .env, storage databases, uploads, and dist
│
├── README.md                     # Project overview and setup guide
├── ARCHITECTURE.md               # Detailed technical architecture specification
├── NETWORKING_CONCEPTS.md        # Academic networking reference (OSI, TCP/IP, WebSockets)
├── SECURITY.md                   # Security model, threat analysis, and hardening
├── LAN_SETUP.md                  # Windows host setup, firewall rules, and troubleshooting
├── TEST_REPORT.md                # 58-test verification matrix and reliability results
├── DEMO_GUIDE.md                 # Step-by-step viva / lab demonstration script
│
├── backend/                      # Python FastAPI application
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment template without secrets
│   ├── app/
│   │   ├── main.py               # FastAPI factory, SPA static mounting, lifespan manager
│   │   ├── config.py             # Settings, paths, and RFC 1918 origin validation regex
│   │   ├── database.py           # SQLAlchemy engine, session maker, SQLite PRAGMAs
│   │   ├── logging_config.py     # Centralized logging configuration
│   │   ├── errors.py             # Custom exceptions and centralized JSON error handlers
│   │   ├── middleware/           # HTTP SecurityHeadersMiddleware (nosniff, CSP, DENY)
│   │   ├── models/               # SQLAlchemy models (User, Session, Conversation, Message, File)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── routers/              # HTTP routers (auth, users, conversations, files, health)
│   │   ├── services/             # Core business logic (auth, chat, files, rate_limiter)
│   │   └── websocket/            # WebSocket ConnectionManager and session handler
│   ├── storage/                  # Local persistence directory
│   │   ├── data.db               # SQLite database in WAL mode
│   │   └── uploads/              # Sandboxed file storage with UUID keys
│   └── tests/                    # Automated Pytest test suite (58 tests)
│       ├── conftest.py           # Test database and rate limiter reset fixtures
│       ├── test_auth.py          # Registration, login, validation tests
│       ├── test_chat.py          # WebSocket messaging, isolation, deduplication tests
│       ├── test_database.py      # SQLite WAL and relationship CRUD tests
│       ├── test_files.py         # File streaming, SHA-256 integrity, isolation tests
│       ├── test_health.py        # System health probe tests
│       ├── test_presence.py      # Real-time presence and cleanup tests
│       ├── test_security.py      # Security headers, CSWSH, DoS, rate limiting tests
│       ├── test_lan_deployment.py# Single-origin SPA serving and LAN origin tests
│       └── test_e2e_reliability.py# Persistence across restart and atomic error tests
│
└── frontend/                     # React 18 + Vite frontend
    ├── package.json              # NPM dependencies
    ├── vite.config.js            # Vite configuration
    ├── index.html                # HTML entrypoint with offline system font stacks
    ├── src/
    │   ├── main.jsx              # React entrypoint
    │   ├── App.jsx               # Root application component with state management
    │   ├── index.css             # Comprehensive charcoal design system
    │   ├── services/
    │   │   └── api.js            # Fetch API client using relative routes
    │   └── components/
    │       ├── auth/             # AuthScreen (Sign in & registration)
    │       ├── chat/             # ChatArea, EmptyChatState
    │       ├── sidebar/          # Sidebar (Channels, peers, search, filter tabs)
    │       ├── files/            # FileUploadModal
    │       ├── layout/           # AppHeader
    │       ├── settings/         # SettingsModal (Topology, profile, keys)
    │       └── common/           # ConfirmDialog, Toast
    └── dist/                     # Production compiled bundle served by FastAPI
```

---

## 5. Quick Start Guide (Windows 11)

### 5.1 Prerequisites
1. **Python 3.10+**: Ensure `python` and `pip` are on your system PATH.
2. **Node.js 18+**: For building the frontend bundle.

### 5.2 Initial Setup (Requires Internet Once)

Open PowerShell in the project root directory:

```powershell
# 1. Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# 2. Install frontend dependencies and build production assets
cd frontend
npm install
npm run build
cd ..
```

### 5.3 Configure Windows Firewall (Run Once as Administrator)

Windows Defender Firewall blocks unsolicited incoming TCP connections by default. Allow port 8000 on your private network:

```powershell
New-NetFirewallRule -DisplayName "Secure LAN Chat" `
                    -Direction Inbound `
                    -LocalPort 8000 `
                    -Protocol TCP `
                    -Action Allow `
                    -Profile Private
```

> [!NOTE]
> Do **not** disable Windows Firewall. The rule selectively allows TCP port 8000 on your Private network profile.

---

## 6. Running the Application

### Method A: PowerShell Launcher (Recommended)
```powershell
.\Start-LanServer.ps1
```

### Method B: Windows Batch File (Double-Click)
Double-click `start_lan_server.bat` in File Explorer.

### Method C: Python Direct Command
```powershell
python run_server.py
```

### Example Startup Banner

```text
==============================================================================
 SECURE LAN CHAT & FILE SHARING — v1.0.0 [Windows 11 LAN Mode]
==============================================================================
 Server Interface : 0.0.0.0:8000
 Single-Origin UI : READY (frontend/dist)
 Offline Capable  : YES (Zero external CDNs or cloud dependencies)
------------------------------------------------------------------------------
 [Host Local Access]
   * http://localhost:8000
   * http://127.0.0.1:8000

 [LAN Access for Second Devices (Phones, Laptops, Tablets on same Wi-Fi)]
   * http://172.16.235.234:8000
------------------------------------------------------------------------------
 Press Ctrl+C to gracefully stop the server and release connections.
==============================================================================
```

### Clean Shutdown
Press `Ctrl+C` once in the terminal window. Uvicorn will cleanly close all active WebSocket client connections and flush pending SQLite database transactions before exiting.

---

## 7. Connecting from a Second Device

1. Ensure your second device (phone, tablet, laptop) is connected to the **same Wi-Fi network** as the host computer.
2. Open a web browser (Chrome, Safari, Firefox, Edge) on the second device.
3. Enter the LAN URL displayed on the host terminal:
   ```text
   http://172.16.235.234:8000
   ```
4. Click **Register Account**, choose a username, and begin chatting.

For complete connection checklists and network troubleshooting, see [`LAN_SETUP.md`](LAN_SETUP.md).

---

## 8. Running Automated Tests

Run the full automated test suite (58 tests) from the `backend/` directory:

```powershell
cd backend
python -m pytest tests/ -v
```

All 58 tests pass with 100% success rate in ~35 seconds. For the comprehensive scenario report, see [`TEST_REPORT.md`](TEST_REPORT.md).

---

## 9. College Project Documentation Directory

* [`ARCHITECTURE.md`](ARCHITECTURE.md): Technical architecture specification, sequence diagrams, and database schemas.
* [`NETWORKING_CONCEPTS.md`](NETWORKING_CONCEPTS.md): Academic analysis of TCP/IP, IPv4, sockets, framing, and WebSockets.
* [`SECURITY.md`](SECURITY.md): Threat modeling, password hashing, transport vs. rest vs. E2EE cryptography.
* [`LAN_SETUP.md`](LAN_SETUP.md): Windows 11 host setup, firewall rules, and Wi-Fi troubleshooting.
* [`TEST_REPORT.md`](TEST_REPORT.md): Complete 12-scenario test matrix and verification evidence.
* [`DEMO_GUIDE.md`](DEMO_GUIDE.md): Step-by-step viva demonstration script for examiners.

---

## 10. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
