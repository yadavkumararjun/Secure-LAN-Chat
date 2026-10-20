import os
import io
import uuid
import hashlib
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.config import settings


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def _register_user(client: TestClient, prefix: str = "file_user"):
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Password123!", "display_name": f"Name {username}"},
    )
    assert res.status_code == 201
    return res.json()


def _receive_event(ws, expected_event: str):
    """Drain frames until the expected event is encountered."""
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == expected_event:
            return frame
    raise TimeoutError(f"Event '{expected_event}' was not received within frame window.")


def test_small_text_file_upload_and_download_integrity():
    """Verify that uploading a small text file succeeds, SHA-256 matches, and downloaded content matches."""
    with TestClient(app) as client:
        user = _register_user(client, "alice")
        test_content = b"This is a local LAN chat text configuration file with line breaks\nLine 2: status=OK\nLine 3: port=8000\n"
        expected_sha256 = hashlib.sha256(test_content).hexdigest()

        # Upload file to broadcast conversation
        files = {"file": ("config_report.txt", io.BytesIO(test_content), "text/plain")}
        data = {"conversation_id": "broadcast-general", "caption": "Project configuration file"}
        upload_res = client.post("/api/files/upload", files=files, data=data)

        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        assert upload_data["original_name"] == "config_report.txt"
        assert upload_data["file_size"] == len(test_content)
        assert upload_data["checksum_sha256"] == expected_sha256
        assert upload_data["uploader_id"] == user["id"]
        assert upload_data["download_url"] == f"/api/files/{upload_data['id']}/download"

        file_id = upload_data["id"]

        # Fetch metadata
        meta_res = client.get(f"/api/files/{file_id}")
        assert meta_res.status_code == 200
        meta_data = meta_res.json()
        assert meta_data["checksum_sha256"] == expected_sha256

        # Download file
        download_res = client.get(f"/api/files/{file_id}/download")
        assert download_res.status_code == 200
        assert download_res.content == test_content
        assert download_res.headers["x-file-checksum-sha256"] == expected_sha256
        assert 'attachment; filename="config_report.txt"' in download_res.headers["content-disposition"]


def test_larger_binary_file_upload_and_download_integrity():
    """Verify that uploading a larger binary file (1 MB) succeeds, SHA-256 matches, and binary bytes match byte-for-byte."""
    with TestClient(app) as client:
        user = _register_user(client, "binary_user")
        # 1 MB of pseudorandom binary bytes
        binary_payload = os.urandom(1024 * 1024)
        expected_sha256 = hashlib.sha256(binary_payload).hexdigest()

        files = {"file": ("firmware_payload.bin", io.BytesIO(binary_payload), "application/octet-stream")}
        data = {"conversation_id": "broadcast-general", "caption": "1 MB binary firmware archive"}
        upload_res = client.post("/api/files/upload", files=files, data=data)

        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        assert upload_data["file_size"] == 1024 * 1024
        assert upload_data["checksum_sha256"] == expected_sha256
        assert upload_data["uploader_id"] == user["id"]

        file_id = upload_data["id"]

        # Download file
        download_res = client.get(f"/api/files/{file_id}/download")
        assert download_res.status_code == 200
        assert len(download_res.content) == 1024 * 1024
        assert download_res.content == binary_payload
        assert hashlib.sha256(download_res.content).hexdigest() == expected_sha256
        assert download_res.headers["x-file-checksum-sha256"] == expected_sha256


def test_file_appears_in_conversation_history():
    """Verify that uploaded file creates a linked message with attachment metadata in conversation history."""
    with TestClient(app) as client:
        _register_user(client, "history_user")
        test_content = b"Content inside conversation history."
        expected_hash = hashlib.sha256(test_content).hexdigest()

        files = {"file": ("dataset.csv", io.BytesIO(test_content), "text/csv")}
        data = {"conversation_id": "broadcast-general", "caption": "Shared dataset for analysis"}
        res = client.post("/api/files/upload", files=files, data=data)
        assert res.status_code == 201

        # Check messages endpoint
        history_res = client.get("/api/conversations/broadcast-general/messages")
        assert history_res.status_code == 200
        messages = history_res.json()["messages"]
        assert len(messages) >= 1

        latest_msg = messages[-1]
        assert latest_msg["message_type"] == "file"
        assert latest_msg["content"] == "Shared dataset for analysis"
        assert latest_msg["file"] is not None
        assert latest_msg["file"]["name"] == "dataset.csv"
        assert latest_msg["file"]["checksum"] == expected_hash
        assert latest_msg["file"]["bytes"] == len(test_content)


def test_unsafe_filename_sanitization():
    """Verify that dangerous directory traversal filenames are strictly sanitized."""
    with TestClient(app) as client:
        _register_user(client, "safe_user")
        evil_filename = "../../../etc/passwd\x00_dangerous.sh"
        test_content = b"malicious traversal attempt"

        files = {"file": (evil_filename, io.BytesIO(test_content), "text/plain")}
        data = {"conversation_id": "broadcast-general"}
        res = client.post("/api/files/upload", files=files, data=data)

        assert res.status_code == 201
        upload_data = res.json()
        # Filename must not contain path separators or null bytes
        assert "/" not in upload_data["original_name"]
        assert "\\" not in upload_data["original_name"]
        assert "\x00" not in upload_data["original_name"]
        assert not upload_data["stored_filename"].startswith("..")
        assert upload_data["stored_filename"].endswith(".bin")

        # Verify disk path stays within sandboxed upload dir
        safe_path = settings.get_absolute_upload_dir() / upload_data["stored_filename"]
        assert safe_path.exists()
        assert safe_path.parent == settings.get_absolute_upload_dir()


def test_empty_file_rejected():
    """Verify that 0-byte uploads are rejected with 400 Bad Request."""
    with TestClient(app) as client:
        _register_user(client, "empty_user")
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        data = {"conversation_id": "broadcast-general"}
        res = client.post("/api/files/upload", files=files, data=data)
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "EMPTY_FILE"


def test_oversized_file_rejected(monkeypatch):
    """Verify that files exceeding the size limit quota are rejected with 413 Payload Too Large and cleaned up."""
    # Temporarily set max upload quota to 100 bytes for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)

    with TestClient(app) as client:
        _register_user(client, "oversized_user")
        oversized_content = b"X" * 150
        files = {"file": ("big_file.bin", io.BytesIO(oversized_content), "application/octet-stream")}
        data = {"conversation_id": "broadcast-general"}
        res = client.post("/api/files/upload", files=files, data=data)

        assert res.status_code == 413
        assert res.json()["error"]["code"] == "FILE_TOO_LARGE"

        # Verify no orphan .tmp files remain in upload dir
        upload_dir = settings.get_absolute_upload_dir()
        tmp_files = list(upload_dir.glob("*.tmp"))
        assert len(tmp_files) == 0


def test_private_file_authorization_isolation():
    """Verify that files shared in a 1-to-1 direct conversation can ONLY be downloaded by conversation members."""
    with TestClient(app) as client_a, TestClient(app) as client_b, TestClient(app) as client_c:
        user_a = _register_user(client_a, "peer_a")
        user_b = _register_user(client_b, "peer_b")
        user_c = _register_user(client_c, "peer_c")  # Third-party outsider

        # User A opens direct conversation with User B
        conv_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # User A uploads a private confidential file to User B
        private_content = b"Confidential financial sheet between A and B"
        files = {"file": ("finances.pdf", io.BytesIO(private_content), "application/pdf")}
        data = {"conversation_id": conv_id, "caption": "Strictly confidential"}
        upload_res = client_a.post("/api/files/upload", files=files, data=data)
        assert upload_res.status_code == 201
        file_id = upload_res.json()["id"]

        # 1. User A (uploader) can download
        res_a = client_a.get(f"/api/files/{file_id}/download")
        assert res_a.status_code == 200
        assert res_a.content == private_content

        # 2. User B (recipient) can download
        res_b = client_b.get(f"/api/files/{file_id}/download")
        assert res_b.status_code == 200
        assert res_b.content == private_content

        # 3. User C (unauthorized outsider) is BLOCKED with 403 Forbidden
        res_c = client_c.get(f"/api/files/{file_id}/download")
        assert res_c.status_code == 403
        assert res_c.json()["error"]["code"] == "ACCESS_FORBIDDEN"

        # User C also cannot fetch metadata
        res_c_meta = client_c.get(f"/api/files/{file_id}")
        assert res_c_meta.status_code == 403


def test_unauthenticated_download_rejected():
    """Verify that unauthenticated requests to download or metadata are rejected with 401 Unauthorized."""
    # First upload a valid file as authenticated user
    with TestClient(app) as client:
        _register_user(client, "auth_user")
        files = {"file": ("doc.txt", io.BytesIO(b"Hello world"), "text/plain")}
        res = client.post("/api/files/upload", files=files, data={"conversation_id": "broadcast-general"})
        file_id = res.json()["id"]

    # Now anonymous client attempts download
    with TestClient(app) as anon_client:
        dl_res = anon_client.get(f"/api/files/{file_id}/download")
        assert dl_res.status_code == 401

        meta_res = anon_client.get(f"/api/files/{file_id}")
        assert meta_res.status_code == 401


def test_nonexistent_file_returns_404():
    """Verify that requesting non-existent file ID returns 404 Not Found."""
    with TestClient(app) as client:
        _register_user(client, "query_user")
        res = client.get("/api/files/99999999/download")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_realtime_websocket_notification_on_file_upload():
    """Verify that uploading a file dispatches a NEW_MESSAGE WebSocket event to peers with complete file metadata."""
    with TestClient(app) as client_a, TestClient(app) as client_b:
        user_a = _register_user(client_a, "ws_sender")
        user_b = _register_user(client_b, "ws_listener")

        with client_b.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_b:
            # Drain handshake
            auth_b = _receive_event(ws_b, "AUTH_SUCCESS")
            assert auth_b["data"]["user_id"] == user_b["id"]

            # User A uploads a file to broadcast channel
            file_bytes = b"Streaming binary content notification test"
            files = {"file": ("diagram.png", io.BytesIO(file_bytes), "image/png")}
            data = {"conversation_id": "broadcast-general", "caption": "Architecture diagram"}
            upload_res = client_a.post("/api/files/upload", files=files, data=data)
            assert upload_res.status_code == 201

            # User B should receive NEW_MESSAGE event over WebSocket in real time
            event = _receive_event(ws_b, "NEW_MESSAGE")
            assert event["data"]["conversation_id"] == "broadcast-general"
            msg = event["data"]["message"]
            assert msg["message_type"] == "file"
            assert msg["content"] == "Architecture diagram"
            assert msg["file"] is not None
            assert msg["file"]["name"] == "diagram.png"
            assert msg["file"]["bytes"] == len(file_bytes)
            assert msg["file"]["download_url"] == f"/api/files/{upload_res.json()['id']}/download"


def test_interrupted_upload_temporary_file_cleanup():
    """Verify that if an upload stream is abruptly interrupted mid-flight, temporary staging files are unlinked."""
    from app.services import file_service
    from app.database import get_db

    class FaultyUploadFile:
        filename = "interrupted_payload.bin"
        content_type = "application/octet-stream"

        def __init__(self):
            self.calls = 0

        async def read(self, size):
            self.calls += 1
            if self.calls == 1:
                return b"Part 1 chunk of incomplete upload" * 100
            # Abrupt network connection interruption / client disconnect
            raise ConnectionResetError("Client aborted socket connection mid-transfer.")

    async def execute_aborted_upload():
        db = next(get_db())
        try:
            await file_service.save_upload_stream(
                file=FaultyUploadFile(),
                conversation_id="broadcast-general",
                uploader_id=1,
                db=db,
            )
        finally:
            db.close()

    with pytest.raises(Exception):
        asyncio.run(execute_aborted_upload())

    # Guarantee zero orphan .tmp files remain on disk
    upload_dir = settings.get_absolute_upload_dir()
    leftover_tmp = list(upload_dir.glob("*.tmp"))
    assert len(leftover_tmp) == 0

