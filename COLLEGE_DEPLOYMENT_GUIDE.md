# Secure LAN Chat — College Lab & Department Deployment Guide

**Target Audience:** College System Administrators, Lab Assistants, Evaluators, and Faculty  
**Application:** Secure LAN Chat & File Sharing System  
**System Architecture:** Single-Origin (FastAPI + React), Zero Cloud Dependencies, Offline-Capable  
**Default Port:** `8000` (TCP)

---

## 1. Executive Summary

This application allows students, teachers, and laboratory peers to communicate in real-time and exchange files over the **college's local intranet / campus Wi-Fi network**.

* **No internet connection is required** to run or use the application after initial setup.
* **No software installation is required on student/teacher devices** — any mobile phone, laptop, or desktop with a standard web browser (Chrome, Safari, Edge, Firefox) connects instantly via the local network IP.
* **Single-Origin Port**: Both the web application interface and backend API run on a single port (`8000`), requiring only one firewall rule.

---

## 2. Delivery Package Contents

When submitting the project to the college on a USB drive or ZIP archive, include:

```text
Secure-LAN-Chat/
├── backend/                  # Python FastAPI source code & database schemas
│   ├── app/                  # Application routers, models, rate limiters
│   ├── storage/              # SQLite data.db & uploaded file directory
│   └── requirements.txt      # Python dependencies
├── frontend/
│   └── dist/                 # Pre-compiled production React web application
├── start.bat                 # Windows 1-Click Server Launcher
├── setup.bat                 # Windows 1-Click Dependency Installer
├── Start-LanServer.ps1       # Windows PowerShell Launcher with firewall check
├── run_server.py             # Cross-platform server runner (Windows/Linux/Mac)
├── Dockerfile                # Container deployment definition
├── docker-compose.yml        # Docker compose configuration
├── clean_db.py               # Database maintenance and cleanup utility
├── README.md                 # Project documentation
├── ARCHITECTURE.md           # Architecture, data flows, and protocol design
├── LAN_SETUP.md              # Detailed network and firewall configuration
└── DEMO_GUIDE.md             # Step-by-step viva presentation script
```

> [!TIP]
> **No Node.js Required:** The React user interface is already pre-built in `frontend/dist/`. The college laboratory **only needs Python 3.10+ installed** to run the complete server.

---

## 3. How the College Can Deploy It

Choose the deployment method that fits your laboratory or server infrastructure:

### Method A: On a Windows Lab Computer (Simplest / Recommended)

This runs the server on a dedicated PC in the computer lab or department office:

1. **One-Time Setup:**
   * Double-click [`setup.bat`](file:///c:/Users/Arjun/Desktop/MyProgramFiles/Secure-LAN-Chat/setup.bat).
   * This automatically installs the Python backend dependencies from `backend/requirements.txt`.
2. **Launch the Server:**
   * Double-click [`start.bat`](file:///c:/Users/Arjun/Desktop/MyProgramFiles/Secure-LAN-Chat/start.bat).
   * The server will launch and display the department LAN access URL:
     ```text
     ==============================================================================
      SECURE LAN CHAT — SERVER RUNNING
     ==============================================================================
      🌐 Host Local URL:     http://localhost:8000
      📡 LAN Network URL:    http://172.16.235.234:8000
     ==============================================================================
     ```
3. **Allow Inbound Port 8000 (Run once as Administrator in PowerShell):**
   ```powershell
   New-NetFirewallRule -DisplayName "Secure LAN Chat" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
   ```

---

### Method B: On a Linux / Ubuntu Department Server (24/7 Hosting)

If the college department has a dedicated Linux server or Raspberry Pi:

1. Copy the project folder to the server.
2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run as a background service (or systemd daemon):
   ```bash
   python3 run_server.py
   ```
4. Allow port 8000 in UFW:
   ```bash
   sudo ufw allow 8000/tcp
   ```

---

### Method C: Using Docker (Containerized Deployment)

If the college laboratory uses Docker:

1. Open a terminal in the project root folder.
2. Run:
   ```bash
   docker compose up -d
   ```
3. The server starts inside an isolated container with port 8000 mapped. Database records and files persist automatically in `./backend/storage/`.

---

## 4. How Students & Teachers Connect

Once the server is running on the lab PC or server:

1. Connect any laptop or smartphone to the **college Wi-Fi or laboratory LAN switch**.
2. Open any web browser and visit the server's IP address:
   ```text
   http://<LAB_SERVER_IP>:8000
   ```
3. **First-time users:** Click **"Register"** to create a username and password.
4. **Returning users:** Log in with their credentials.
5. All connected users can now:
   * Chat publicly in `#general-lan`.
   * Start encrypted 1-to-1 private direct chats.
   * Send and download documents, assignments, and files with SHA-256 integrity checks.

---

## 5. Lab Administration & Maintenance

The project includes built-in tools for the lab assistant or administrator:

* **View Active Users:**
  ```powershell
  python clean_db.py --list
  ```
* **Remove Specific User:**
  ```powershell
  python clean_db.py --delete <username>
  ```
* **Factory Reset (Wipe all chat history & files for a new semester/batch):**
  ```powershell
  python clean_db.py --reset-all
  ```
* **Backup Data:**
  Simply make a copy of the [`backend/storage/`](file:///c:/Users/Arjun/Desktop/MyProgramFiles/Secure-LAN-Chat/backend/storage) folder. It contains all database records (`data.db`) and uploaded files (`uploads/`).
