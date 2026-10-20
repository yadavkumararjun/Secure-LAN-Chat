# Secure LAN Chat & File Sharing — LAN Setup & Deployment Guide

**Version:** 1.0.0  
**Host Operating System:** Windows 11  
**Default Port:** `8000` (TCP)  
**Deployment Model:** Single-Origin Host Architecture (Offline-Capable)

---

## 1. System Architecture & Single-Origin Deployment

Secure LAN Chat is engineered as a **single-origin application**. The host machine (Windows 11) runs a single FastAPI process on port `8000` that handles:
1. Serving compiled, static React UI files (`frontend/dist`) directly at `/` and `/assets/*`.
2. Servicing REST API endpoints (`/api/*`).
3. Managing real-time bidirectional WebSocket channels (`/ws/chat`).

```mermaid
flowchart TD
    subgraph Host Machine (Windows 11)
        direction TB
        FW["Windows Defender Firewall<br/>(TCP Port 8000 Inbound Allowed on Private Profile)"]
        
        subgraph FastAPI Single-Origin Server [FastAPI Process : 8000]
            Static["Static File Engine<br/>(frontend/dist & SPA Catch-All)"]
            API["REST API Router<br/>(/api/auth, /api/conversations, /api/files)"]
            WS["WebSocket Engine<br/>(/ws/chat & Connection Quotas)"]
            DB[(SQLite WAL<br/>storage/data.db)]
            FS[(File Storage<br/>storage/uploads)]
        end
    end

    subgraph Local Wi-Fi / LAN Subnet
        Router["Wi-Fi Router / Access Point<br/>(Client Isolation Disabled)"]
        Device1["Host Browser (You)<br/>http://localhost:8000"]
        Device2["Second Device (Phone / Laptop)<br/>http://172.16.235.234:8000"]
    end

    Device1 --> Static
    Device1 --> API
    Device1 --> WS

    Device2 --> Router
    Router --> FW
    FW --> Static
    FW --> API
    FW --> WS

    API --> DB
    API --> FS
    WS --> DB
```

### Why Single-Origin is Critical for LAN Deployments

* **Zero CORS Complications:** Both the web interface and the API live on the exact same port (`8000`). Browsers on second devices do not need complex cross-origin cookie sharing headers.
* **Automatic Origin & Dynamic Addressing:** The frontend never hardcodes IP addresses. When a second device navigates to `http://<HOST_LAN_IP>:8000`, the frontend dynamically derives API requests and WebSocket endpoints from `window.location.host`.
* **Single Firewall Port:** Only one inbound port (TCP `8000`) needs to be opened in Windows Firewall.
* **Offline Independence:** Zero external runtime dependencies. Google Fonts and external CDNs have been completely removed in favor of native system font stacks (`Segoe UI`, `ui-sans-serif`) and pre-bundled assets.

---

## 2. Prerequisites & Initial Installation

> [!NOTE]
> Initial setup requires Internet access to install Python packages and Node modules. Once installed and built, the application operates **100% offline** on your local network.

### 2.1 Software Requirements
* **Windows 11** (Host Machine)
* **Python 3.10+** (with `pip` added to PATH)
* **Node.js 18+** & `npm` (for compiling the frontend)

### 2.2 First-Time Setup Commands

Run the following commands in PowerShell from the project root:

```powershell
# 1. Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# 2. Install frontend dependencies and build production bundle
cd frontend
npm install
npm run build
cd ..
```

---

## 3. Windows Firewall Configuration

Windows Defender Firewall blocks unsolicited incoming network traffic by default. You **do not** need to disable your firewall; you only need to create a targeted inbound rule for TCP port `8000`.

### 3.1 Add Inbound Port Rule (Run Once as Administrator)

Open **PowerShell as Administrator** (Right-click Windows Start menu $\rightarrow$ *Terminal (Admin)* or *PowerShell (Admin)*) and run:

```powershell
New-NetFirewallRule -DisplayName "Secure LAN Chat" `
                    -Direction Inbound `
                    -LocalPort 8000 `
                    -Protocol TCP `
                    -Action Allow `
                    -Profile Private
```

> [!IMPORTANT]
> The rule restricts inbound connections to the **Private** network profile. Ensure your home/office Wi-Fi connection is set to **Private Network** in Windows Settings (see Section 6).

### 3.2 Verify or Remove Firewall Rule

To verify the rule is active:
```powershell
Get-NetFirewallRule -DisplayName "Secure LAN Chat" | Select-Object DisplayName, Enabled, Direction, Action, Profile
```

To remove the rule in the future:
```powershell
Remove-NetFirewallRule -DisplayName "Secure LAN Chat"
```

---

## 4. Starting the Server

You can launch the server using any of the following methods:

### Option A: Windows PowerShell Launcher (Recommended)
```powershell
.\Start-LanServer.ps1
```
* Automatically checks Python installation.
* Verifies `frontend/dist` production build.
* Queries Windows Firewall rule status for port `8000`.
* Prints all discovered local network IP addresses.

### Option B: Windows Batch File (Double-Click)
Double-click `start_lan_server.bat` in File Explorer.

### Option C: Python Direct Command
```powershell
python run_server.py
```

### Startup Output Example

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
 [Windows Firewall Quick Note]
   If other devices cannot connect, allow inbound TCP port 8000 in Windows Firewall:
   PowerShell (Admin): New-NetFirewallRule -DisplayName 'Secure LAN Chat' \
                       -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
------------------------------------------------------------------------------
 [Clean Shutdown]
   Press Ctrl+C to gracefully stop the server and release connections.
==============================================================================
```

### Clean Shutdown Procedure
Press `Ctrl+C` once in the command window. The server cleanly releases active WebSocket connections, commits pending SQLite transactions, and shuts down gracefully without corrupting database state.

---

## 5. Connecting a Second Device (Step-by-Step Checklist)

Follow this checklist to test communication from another device (smartphone, tablet, or second laptop):

- [ ] **Step 1: Wi-Fi Network Check**  
  Connect the second device to the **exact same Wi-Fi network (SSID)** as your Windows 11 host.
- [ ] **Step 2: Note Host LAN IP**  
  Look at the startup banner printed in your terminal (e.g. `172.16.235.234`). Alternatively, run `ipconfig` on the host and find the IPv4 address under your Wi-Fi adapter.
- [ ] **Step 3: Open Mobile Browser**  
  On the second device, open Chrome, Safari, Edge, or Firefox.
- [ ] **Step 4: Navigate to the Application**  
  Enter the host address in the browser address bar:  
  `http://<HOST_LAN_IP>:8000` (e.g. `http://172.16.235.234:8000`).
- [ ] **Step 5: Register User Account**  
  Click "Register", choose a new username (e.g. `mobile_user`), and create a password.
- [ ] **Step 6: Real-Time Chat Verification**  
  - On the second device, send a message in the **LAN Broadcast Channel**; observe it appear instantly on the host.
  - Open a **Direct Message** with your host user and exchange private messages.
- [ ] **Step 7: File Sharing Verification**  
  - Upload a photo or file from the second device; download it on the host machine.
  - Verify filename, size, and download integrity.

---

## 6. Troubleshooting Common LAN Issues

### Issue 1: "This site can't be reached" or Connection Timed Out

1. **Firewall Blocking:**  
   Ensure you created the firewall rule from Section 3.1.
2. **Network Profile Set to "Public":**  
   Windows Defender blocks local incoming traffic on Public networks.  
   *Fix:* Open Windows Settings $\rightarrow$ **Network & Internet** $\rightarrow$ **Wi-Fi** $\rightarrow$ Click your connected network $\rightarrow$ Change **Network profile type** from *Public* to **Private network**.
3. **Wi-Fi Client Isolation (AP Isolation):**  
   Guest Wi-Fi networks and corporate/university Wi-Fi networks frequently enable **Client Isolation**, which forbids wireless devices on the same subnet from communicating with one another.  
   *Fix:* Connect both devices to a standard home Wi-Fi network, or enable a **Mobile Hotspot** on your Windows 11 machine (Settings $\rightarrow$ Network & Internet $\rightarrow$ Mobile hotspot) and connect your second device directly to it.

### Issue 2: Changing Host IP (DHCP Lease Expiry)

Routers dynamically allocate IP addresses using DHCP. If your router reboots or your lease expires, your host IP might change (e.g., from `172.16.235.234` to `172.16.235.240`).  
*Fix:* Check the startup banner when launching `Start-LanServer.ps1`. If you want a permanent address:
- Set up a **DHCP Reservation** in your router admin console for your computer's MAC address.
- Or assign a static IP address in Windows Network Adapter settings.

### Issue 3: WebSocket Disconnections on Mobile Browsers

Mobile operating systems (iOS and Android) aggressively freeze background browser tabs to save battery. When switching apps, the WebSocket connection may close.  
*Behavior:* The application automatically transitions to an amber "Reconnecting..." state and silently reconnects with exponential backoff when you switch back to the browser tab.

---

## 7. Verification Status

| Test Scope | Status | Details |
| :--- | :--- | :--- |
| **Local Automated Suite** | **VERIFIED (53/53 Passed)** | Comprehensive tests covering SPA single-origin serving, MIME types, dynamic LAN origins, and secrecy. |
| **Local Multi-Browser Loopback** | **VERIFIED** | Simultaneous sessions across incognito/separate browser windows on `localhost` and `127.0.0.1`. |
| **Physical Second Device (Cross-Device)** | **PENDING USER VERIFICATION** | Ready for execution by testing with a smartphone/laptop following the Section 5 checklist. |
