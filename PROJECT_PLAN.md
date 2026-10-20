# Secure LAN Chat & File Sharing System - Phased Implementation Plan

## Project Overview

This project plan lays out the complete development lifecycle for transforming the experimental Python socket prototype into a robust, secure, production-grade **Secure LAN Chat and File Sharing System** for local network deployment.

---

## Phase Breakdown Matrix

| Phase | Title | Focus Area | Deliverables | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | **Architectural Blueprint & Workspace Audit** | Codebase inspection, networking analysis, risk assessment | `ARCHITECTURE.md`, `PROJECT_PLAN.md`, migration plan | **Completed** |
| **Phase 1** | **Backend Core & Authentication** | FastAPI setup, SQLite ORM models, Argon2 password hashing, sessions | `backend/app/`, auth endpoints, user database, session cookies/tokens | **Next Up** |
| **Phase 2** | **Real-Time WebSocket Gateway** | Full-duplex messaging, presence tracking, broadcast & direct messages | `ConnectionManager`, event dispatcher, WS tests | Planned |
| **Phase 3** | **Secure Sandboxed File Sharing** | Chunked upload/download API, UUID storage, SHA-256 integrity, WS file alerts | File endpoints, storage sandbox, integrity checks | Planned |
| **Phase 4** | **Modern React + Vite Frontend** | Responsive UI, chat interface, presence sidebar, file dropzone & progress bars | React components, Context providers, Lucide icons | Planned |
| **Phase 5** | **LAN Deployment & Single-Port Packaging** | 0.0.0.0 binding, LAN IP auto-detect, firewall guidelines, production bundle | `run_server.py`, static asset mounting, LAN guide | Planned |
| **Phase 6** | **Academic Verification & Presentation Prep** | Concurrency stress testing, multi-device LAN tests, documentation | Test suite, project report notes, grading demo scripts | Planned |

---

## Detailed Phase Specifications

---

### Phase 0: Architectural Blueprint & Workspace Audit (Current)
* **Objective**: Evaluate existing prototype files, document technical limitations, specify target architecture, and map out migration path.
* **Tasks**:
  1. Inspect `client/client.py`, `server/server.py`, `uploads/`, and empty `frontend/` files.
  2. Document TCP message framing issues, arbitrary file overwrite risks, and lack of authentication.
  3. Formulate the technical rationale for WebSocket/HTTP over raw sockets in web browsers.
  4. Author `ARCHITECTURE.md` and `PROJECT_PLAN.md`.
* **Acceptance Criteria**:
  - [x] Full workspace file analysis completed.
  - [x] `ARCHITECTURE.md` created with database schema, WS event catalog, file transfer flow, and network topology.
  - [x] `PROJECT_PLAN.md` created with clear phases and testable criteria.
  - [x] Existing prototype files untouched and preserved.

---

### Phase 1: Backend Foundation & Authentication
* **Objective**: Scaffold the FastAPI backend, establish the SQLite persistence layer, and implement secure user registration, password hashing, and authentication.
* **Dependencies**:
  - `fastapi`
  - `uvicorn[standard]`
  - `sqlalchemy`
  - `pydantic`
  - `pwdlib[argon2]` or `passlib[bcrypt]`
  - `python-jose` or `pyjwt` (or secure cryptographic session tokens)
* **Key Tasks**:
  1. Archive original scripts cleanly into `legacy/` (upon approval).
  2. Setup `backend/` directory structure and virtual environment / `requirements.txt`.
  3. Implement database configuration (`backend/app/database.py`) enabling SQLite WAL mode.
  4. Create SQLAlchemy models for `User`, `Message`, and `FileRecord`.
  5. Implement password hashing utility with Argon2id / Bcrypt (`backend/app/security/hashing.py`).
  6. Implement authentication router (`POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`).
  7. Add authorization dependency (`get_current_user`) to guard protected endpoints.
* **Acceptance Criteria**:
  - Users can register with unique usernames and strong passwords.
  - Passwords are encrypted on disk with salted Argon2id hashes (no plaintext passwords).
  - Users can log in, receive a valid session token, and access `GET /api/auth/me`.
  - Duplicate usernames are rejected with standard HTTP 409 Conflict.
* **Verification Steps**:
  - Automated tests verifying password hashing, token validation, and SQLite persistence.
  - Interactive verification via Swagger UI (`/docs`).

---

### Phase 2: Real-Time WebSocket Engine & Messaging
* **Objective**: Build an asynchronous, full-duplex WebSocket communication engine with presence detection, public broadcasts, and private direct messaging.
* **Key Tasks**:
  1. Implement `ConnectionManager` class in `backend/app/websocket/manager.py` to maintain active client connections and user ID mappings in a thread-safe manner.
  2. Create the WebSocket endpoint `/ws/chat` with authentication token verification during the connection handshake.
  3. Implement event dispatcher for structured JSON frames (`CHAT_BROADCAST`, `CHAT_PRIVATE`, `TYPING_INDICATOR`, `PING`/`PONG`).
  4. Persist messages to the SQLite `messages` table before delivery.
  5. Broadcast real-time presence events (`USER_JOINED`, `USER_LEFT`, `PRESENCE_STATE`) whenever a peer connects or disconnects.
  6. Add heartbeat ping-pong mechanism to detect broken connections (e.g. abrupt Wi-Fi loss) within 30 seconds.
* **Acceptance Criteria**:
  - Multiple concurrent clients can connect simultaneously over WebSockets.
  - Messages sent to broadcast reach all connected users instantly.
  - Private messages (`recipient_id`) are routed only to the specified recipient and the sender.
  - Presence list updates automatically when clients join or disconnect.
  - Disconnecting a client does not crash the server or leave ghost users in the directory.
* **Verification Steps**:
  - Run concurrent Python WebSocket test scripts simulating 5 clients exchanging messages simultaneously.
  - Confirm all messages are saved in the SQLite database.

---

### Phase 3: Secure Sandboxed File Sharing
* **Objective**: Implement a secure, high-speed local file upload and download subsystem with chunked streaming, path traversal prevention, and real-time chat announcements.
* **Key Tasks**:
  1. Create a dedicated sandboxed storage directory (`backend/storage/uploads/`).
  2. Implement `POST /api/files/upload`:
     - Accept multipart form data.
     - Enforce maximum file size quota (e.g., 50 MB / 100 MB).
     - Stream file chunks to disk using a unique UUID filename (`<uuid>.bin`).
     - Calculate SHA-256 checksum during streaming.
     - Store metadata (original filename, size, MIME type, uploader ID, hash) in SQLite.
     - Trigger a WebSocket `FILE_SHARED` event announcing the file to the chat room or recipient.
  3. Implement `GET /api/files/{file_id}/download`:
     - Validate session authentication.
     - Stream file with `Content-Disposition: attachment; filename="<original_name>"`.
  4. Implement `GET /api/files`: list recent shared files.
* **Acceptance Criteria**:
  - Path traversal attempts (e.g., `../../etc/passwd` or `..\..\Windows\cmd.exe`) are completely mitigated by UUID isolation.
  - Any file format (images, PDFs, ZIPs, code) uploads and downloads intact with matching SHA-256 checksums.
  - File transfers do not block real-time chat messages.
* **Verification Steps**:
  - Upload a test binary file (e.g. 20 MB image or ZIP), download it, and verify `sha256sum` matches exactly.

---

### Phase 4: Modern React + Vite Frontend
* **Objective**: Build a clean, responsive, single-page web interface using React, Vite, and Lucide icons that runs smoothly on desktop and mobile browsers.
* **Dependencies**:
  - `react`, `react-dom`
  - `vite`
  - `lucide-react`
  - `axios` or native `fetch`
* **Key Tasks**:
  1. Scaffold modern React application inside `frontend/` using Vite.
  2. Configure `vite.config.js` with server host `0.0.0.0` for LAN access and API proxy.
  3. Create `AuthContext`: handles login, register, session persistence in `localStorage`, and logout.
  4. Create `WebSocketContext`: manages WebSocket lifecycle, auto-reconnection, heartbeat, and event dispatching.
  5. Build UI components:
     - **Auth Modal / Screen**: Clean login & registration forms with validation.
     - **Top Bar**: Shows connected LAN IP, current user, online peer counter, and logout button.
     - **Sidebar**: Channels (Public LAN Broadcast) and Direct Messages list with online status dots.
     - **Chat View**: Message history, message bubbles, timestamps, sender badges, typing status.
     - **File Transfer Components**: File drag-and-drop dropzone, upload progress bar, and clickable file download cards with file size and type badges.
* **Acceptance Criteria**:
  - UI is responsive, intuitive, and modern.
  - Seamless real-time chat updates without page reloads.
  - File upload shows live percentage progress.
  - Reconnects automatically if Wi-Fi flickers.
* **Verification Steps**:
  - Open two browser tabs (or browser + mobile phone on same Wi-Fi) and test real-time chat and file exchange.

---

### Phase 5: LAN Deployment & Single-Port Packaging
* **Objective**: Package the application so that any device on the local network can access the system by opening a single URL without installing software.
* **Key Tasks**:
  1. Build a LAN launcher script (`backend/run_server.py`):
     - Automatically scans host network interfaces and detects the host's LAN IP (e.g. `192.168.1.50`).
     - Binds FastAPI/Uvicorn to `0.0.0.0:8000`.
     - Displays formatted console instructions with the exact clickable URL for peers: `http://192.168.1.50:8000`.
  2. Configure frontend build (`npm run build`) to output to `backend/static/` or configure FastAPI to mount `frontend/dist/`.
  3. Ensure CORS and WebSocket origins support dynamic LAN IP access.
  4. Document Windows Defender Firewall rules for opening incoming port 8000.
* **Acceptance Criteria**:
  - Server starts with a single command (`python backend/run_server.py`).
  - A second device (e.g., smartphone or peer laptop) on the same Wi-Fi opens the URL, loads the web UI, registers, and chats with the host.
* **Verification Steps**:
  - Connect a secondary device to the local network and verify end-to-end communication.

---

### Phase 6: Academic Testing, Verification & Presentation Prep
* **Objective**: Perform automated and manual testing, verify performance under load, and assemble academic presentation materials highlighting Computer Networks concepts.
* **Key Tasks**:
  1. Write automated test scripts for:
     - Authentication flow (valid & invalid credentials).
     - Concurrent WebSocket connections.
     - File integrity verification (SHA-256 match).
  2. Document key Computer Networks principles demonstrated in the project:
     - Transport Layer (TCP vs UDP, byte stream framing, port multiplexing).
     - Application Layer (HTTP/1.1 vs WebSocket RFC 6455 framing, MIME types).
     - Network Security (Argon2id hashing, session authorization, path traversal mitigation, E2EE principles).
  3. Write a comprehensive `README.md` containing architecture summaries, setup guides, and demonstration scripts.
* **Acceptance Criteria**:
  - All test scripts pass cleanly.
  - Comprehensive documentation prepared for academic viva and grading demonstration.

---

## Technical Dependencies

### Backend Dependencies (`backend/requirements.txt`)
```txt
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
aiosqlite>=0.20.0
pydantic>=2.6.4
pydantic-settings>=2.2.1
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.9
aiofiles>=23.2.1
```

### Frontend Dependencies (`frontend/package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.359.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.6"
  }
}
```
