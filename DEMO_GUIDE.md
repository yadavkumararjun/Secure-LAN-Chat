# College Project Demonstration & Viva Presentation Script

**Project:** Secure LAN Chat & File Sharing System  
**Demonstrators:** Arjun  
**Setup Requirements:** 1 Windows 11 Host Laptop + 1 Smartphone or Second Laptop (Same Wi-Fi)  
**Estimated Demo Time:** 8–10 Minutes  

---

## 1. Pre-Demonstration Checklist

Before calling the examiners or starting your viva, verify these four items:

- [ ] **1. Wi-Fi Network**: Ensure both your Windows 11 laptop and your smartphone/second device are connected to the **same Wi-Fi network**.
- [ ] **2. Windows Firewall**: Ensure inbound TCP port 8000 is allowed (run once in PowerShell as Admin):
  ```powershell
  New-NetFirewallRule -DisplayName "Secure LAN Chat" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
  ```
- [ ] **3. Production Frontend Built**: Ensure `frontend/dist/index.html` exists (run `cd frontend && npm run build` if needed).
- [ ] **4. Terminal Ready**: Open PowerShell in the project root directory.

---

## 2. Step-by-Step Demonstration Walkthrough

### Step 1: Server Startup & Dynamic IP Discovery (1 Minute)

1. In your PowerShell terminal, launch the application:
   ```powershell
   .\Start-LanServer.ps1
   ```
2. **What to point out to the examiner:**
   * Point out the **Server Interface** (`0.0.0.0:8000`). Explain that `0.0.0.0` tells the Windows kernel to accept connections on all active network adapters (Wi-Fi, Ethernet, loopback).
   * Point out the dynamically discovered **LAN IP address** in the banner (e.g., `http://172.16.235.234:8000`).
   * *Talking Point:* *"The application uses a socket lookup trick in `run_server.py` to automatically detect the host's actual network IP without hardcoding, so it adapts if the router's DHCP assigns a new lease."*

---

### Step 2: Host Browser Access & User Registration (1.5 Minutes)

1. Open Chrome or Edge on the host laptop and navigate to:
   ```text
   http://localhost:8000
   ```
2. Click **Register Account**:
   * Username: `alice_host`
   * Display Name: `Alice (Host PC)`
   * Password: `Password123!`
   * Click **Create Local Account**.
3. **What to point out to the examiner:**
   * Open Developer Tools (**F12** $\rightarrow$ **Application** $\rightarrow$ **Cookies**).
   * Show the `session_id` cookie: point out that the cookie is marked `HttpOnly` and `SameSite=Lax`.
   * *Talking Point:* *"Passwords are never stored in plaintext; they are hashed with Argon2id using 64 MiB memory cost. The session token is a 256-bit cryptographically secure random hex string protected against XSS theft via the `HttpOnly` flag."*

---

### Step 3: Second Device Connection via LAN IP (1.5 Minutes)

1. On your smartphone (or second laptop), open a browser (Chrome / Safari).
2. Enter the host's LAN URL:
   ```text
   http://172.16.235.234:8000
   ```
3. Click **Register Account**:
   * Username: `bob_mobile`
   * Display Name: `Bob (Mobile)`
   * Password: `Password123!`
   * Click **Create Local Account**.
4. **What to point out to the examiner:**
   * Notice that the phone immediately loads the full React single-origin web application from the Windows host without installing any mobile app!
   * *Talking Point:* *"This is a single-origin architecture. The host's FastAPI process serves the compiled React SPA, REST endpoints, and WebSocket connections on the exact same port (8000), eliminating cross-origin cookie bugs on mobile browsers."*

---

### Step 4: Real-Time Presence Detection (1 Minute)

1. Place both devices side-by-side (Host laptop and Smartphone).
2. On Alice's screen, look at the sidebar under **LAN Peers**.
3. Point out that `bob_mobile` appears with a **green online indicator badge**.
4. On Bob's phone, close the browser tab.
5. Within 1–2 seconds, observe Bob's status badge on Alice's screen turn **offline**.
6. Re-open the page on Bob's phone; observe the indicator return to **online**.
7. *Talking Point:* *"Presence is tracked in memory via active WebSocket handles in `ConnectionManager`. When a socket disconnects, the server automatically decrements connection counters and broadcasts a `PRESENCE_CHANGE` event across the subnet."*

---

### Step 5: Public Broadcast Messaging (1 Minute)

1. On Bob's phone, select `#general-lan` (Public LAN Broadcast Channel).
2. Type: `Hello everyone on the lab Wi-Fi!` and tap **Send**.
3. Observe the message appear **instantly** on Alice's laptop screen.
4. Point out the double checkmark icon ($\checkmark\checkmark$) next to the timestamp.
5. *Talking Point:* *"Delivery is over full-duplex WebSockets (RFC 6455). The double checkmark confirms that the server has written the message to the SQLite database and confirmed persistence back to the sender."*

---

### Step 6: Private 1-to-1 Direct Messaging & Isolation (1.5 Minutes)

1. On Alice's laptop, click on `Bob (Mobile)` under LAN Peers.
2. Point out the green security banner:
   * `"Private Direct Message — Visible only to you and @bob_mobile"`
3. Type: `Confidential: Examination results are ready.` and hit **Enter**.
4. Observe the message appear instantly on Bob's phone in his private conversation with Alice.
5. *Talking Point (Security & Horizontal Isolation):* *"To demonstrate horizontal isolation, our automated test suite (`test_security.py`) simulates a third user, Charlie, attempting to query this conversation endpoint. The server checks the `ConversationMember` table and rejects unauthorized queries with `403 Forbidden`."*

---

### Step 7: LAN File Upload & Download with SHA-256 Verification (1.5 Minutes)

1. In the private chat between Alice and Bob, click the **Attach File** icon (paperclip) or drag and drop a file (e.g. an image, PDF, or text document).
2. Click **Upload to LAN**.
3. Show the upload progress bar reaching 100%.
4. On Bob's phone, observe the file attachment bubble appear in the chat with the filename, file size, and download button.
5. Tap **Download**. Open the file on Bob's phone to verify it opens perfectly without corruption.
6. *Talking Point:* *"The file is streamed in 64 KB chunks directly to disk using a unique UUID storage identifier, preventing memory exhaustion and path traversal attacks (CWE-22). The backend calculates a SHA-256 checksum during streaming to guarantee bit-for-bit file integrity."*

---

### Step 8: Network Interruption & Reconnection Recovery (1 Minute)

1. On Bob's phone, toggle **Airplane Mode ON** (or disable Wi-Fi).
2. Notice the top header badge transition to an amber `"Connecting / Reconnecting..."` state.
3. Toggle **Airplane Mode OFF** (re-enable Wi-Fi).
4. Within 3 seconds, observe the badge seamlessly transition back to green `"Connected (LAN)"`.
5. *Talking Point:* *"The React client implements exponential backoff reconnection with heartbeat ping frames every 20 seconds. Idempotent `client_msg_id` deduplication guarantees no messages are duplicated during reconnects."*

---

### Step 9: Server Restart & Persistence Verification (1 Minute)

1. On the host laptop terminal, press `Ctrl+C` to cleanly stop the server.
2. Point out the clean shutdown log output.
3. Restart the server: `.\Start-LanServer.ps1`.
4. Refresh both Alice's browser and Bob's phone.
5. Point out that **all conversation messages, private chats, and file attachments are preserved**!
6. *Talking Point:* *"Data is persisted in SQLite using Write-Ahead Logging (`WAL`) mode, ensuring full ACID compliance and crash resilience across restarts."*

---

## 3. Anticipated Viva Examiner Questions & Answers

### Q1: "Why did you use WebSockets instead of normal HTTP polling?"
* **Answer:** *"HTTP polling requires the client to repeatedly send request headers every few seconds, generating significant network overhead, high battery drain on mobile devices, and inherent latency. WebSockets (RFC 6455) establish a persistent, full-duplex TCP connection via an HTTP Upgrade handshake. Once established, frames have only 2 to 10 bytes of header overhead, enabling sub-millisecond real-time message delivery."*

### Q2: "Can another student on the Wi-Fi read our private messages?"
* **Answer:** *"At the application layer, the server strictly isolates private conversations by checking membership in the database before routing messages. However, at the physical Wi-Fi layer, unencrypted Wi-Fi traffic can be captured by anyone running Wireshark in promiscuous mode with the shared Wi-Fi password. In production, we eliminate this by enabling TLS 1.3 (HTTPS/WSS) at the Uvicorn server using a local CA like `mkcert`."*

### Q3: "How does your file transfer handle large files without running out of server RAM?"
* **Answer:** *"Instead of loading the entire file into Python memory using `file.read()`, our endpoint streams binary chunks (`chunk = await upload_file.read(65536)`) directly into a disk buffer. This ensures memory consumption stays constant at ~64 KB regardless of whether the file is 100 KB or 50 MB."*

### Q4: "What happens if someone uploads a file named `../../Windows/System32/evil.exe`?"
* **Answer:** *"The application completely mitigates path traversal (CWE-22) in two ways: first, the file is never saved on disk under the user's filename; it is saved under a cryptographically random UUIDv4 key. Second, before any read or write, the path is resolved and validated with `path.is_relative_to(upload_dir)`, ensuring file operations cannot escape the sandboxed storage folder."*

### Q5: "What database does this use, and how does it handle concurrency?"
* **Answer:** *"It uses SQLite in Write-Ahead Logging (`WAL`) mode via SQLAlchemy. In WAL mode, read transactions never block write transactions, and write transactions never block readers, allowing high concurrent throughput for local network operations without requiring an external database server."*
