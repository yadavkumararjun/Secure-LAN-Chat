# Secure LAN File Sharing Subsystem Specification

## 1. Overview
The Secure LAN File Sharing subsystem enables authorized users on the same local network subnet to share files reliably without relying on external cloud storage. File transfers are executed directly between the client browser and the local FastAPI backend over HTTP multipart streams, bypassing WebSocket frames to prevent Head-of-Line (HoL) blocking on low-latency chat messages.

---

## 2. Supported File Types & Transfer Quotas

### Supported Formats
The system treats all file payloads as arbitrary binary streams without executing or rendering them on the server:
- **Documents**: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.csv`, `.md`, `.json`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`
- **Archives**: `.zip`, `.tar`, `.gz`, `.7z`
- **Binary/Code**: `.bin`, `.iso`, `.py`, `.c`, `.cpp`, `.rs`, `.java`
- **Media**: `.mp3`, `.wav`, `.mp4`, `.mkv`

If a file's MIME type cannot be inferred from its sanitized extension, the system defaults safely to `application/octet-stream`.

### Size Limits
- **Maximum File Quota**: **50 MB** (`52,428,800 bytes`).
- **Minimum File Size**: **1 byte** (0-byte empty files are rejected with `400 Bad Request`).
- Files exceeding 50 MB are terminated mid-stream with `413 Payload Too Large` and temporary files are immediately unlinked from disk.

---

## 3. Storage Architecture & Sandboxing

```
backend/
├── app/
│   ├── routers/files.py        <-- REST endpoints: /api/files/upload, /api/files/{id}/download
│   ├── services/file_service.py <-- Streaming ingest, sanitization, path verification
│   └── models/file_record.py   <-- SQLite metadata records
└── storage/
    ├── data.db                 <-- SQLite database (WAL mode)
    └── uploads/                <-- Isolated storage directory (NOT in public static root)
        ├── 7cf601e8dc2d46a1...bin
        └── a858a7f34c124bc3...bin
```

1. **Storage Identifier Isolation**: Files are never stored under user-supplied names. Each upload receives a 32-character hexadecimal UUID (`<uuid>.bin`).
2. **Outside Public Static Roots**: The `uploads/` directory is isolated outside any web root or static mount. No arbitrary HTTP direct file access is possible.
3. **Chunked Ingest**: Files stream in 64 KB buffers to minimize server RAM footprint, streaming to a temporary `<uuid>.tmp` file.
4. **Atomic Promotion**: The file is atomically renamed from `<uuid>.tmp` to `<uuid>.bin` only when the entire stream is successfully written and the SHA-256 hash verified.
5. **Abandoned Stream Cleanup**: If a client disconnects, aborts, or violates the 50 MB limit, exception handlers guarantee the `.tmp` staging file is unlinked immediately.

---

## 4. Security & Hardening Controls

| Threat / Risk | Mitigation Mechanism |
| :--- | :--- |
| **Directory Traversal (`../`, `..\`)** | `sanitize_filename()` strips all path separators, null bytes (`\x00`), and control characters. `get_safe_storage_path()` asserts that the resolved absolute path is strictly a direct child of the uploads directory. |
| **Arbitrary Code Execution** | Files are never executed or evaluated by the backend. When downloaded, files are delivered with `Content-Disposition: attachment; filename="..."` and `X-Content-Type-Options: nosniff` to prevent browser MIME sniffing. |
| **Unauthorized File Access** | `GET /api/files/{id}/download` verifies that the authenticated user is an active member of the conversation where the file was uploaded (`403 Forbidden` for outsiders). |
| **Data Corruption & Tampering** | SHA-256 checksum is computed incrementally during ingest and returned in headers (`X-File-Checksum-SHA256`). Clients and tests verify integrity byte-for-byte. |
| **Head-of-Line (HoL) Blocking** | File uploads run over independent HTTP POST streams rather than WebSocket frames, keeping the real-time chat connection responsive. |

---

## 5. Security Notices & Phase Boundaries

> [!CAUTION]
> **No Malware Scanning**: The system currently does **NOT** perform antivirus or malware scanning. All uploaded files are treated as untrusted binary payloads. Users should exercise caution when executing binaries received over the local network.

> [!NOTE]
> **No End-to-End Encryption in Phase 5**: Files are transferred in clear binary format over local LAN connections. End-to-end payload encryption (E2EE) and key exchange are scheduled for **Phase 6**.
