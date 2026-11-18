import io
from datetime import datetime, timezone
import hashlib
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import PropertyMock, patch

from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.models import Board, CanvasItem, MediaItem, User
from app.routers.auth import get_current_user
from app.services.storage import MediaStorageService, storage


def _make_png_bytes(width: int = 32, height: int = 24, color=(20, 120, 220)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color)
    img.save(buf, format="PNG")
    return buf.getvalue()


class FakeR2Client:
    """Cloudflare R2 (S3互換) API をメモリ上で忠実に模倣するテスト用フェイククライアント。"""

    def __init__(self) -> None:
        self.buckets: dict[str, dict[str, dict]] = {}

    def ensure_bucket(self, bucket: str) -> None:
        self.buckets.setdefault(bucket, {})

    def _not_found(self, key: str = "") -> ClientError:
        return ClientError(
            {
                "Error": {"Code": "NoSuchKey", "Message": f"Not found: {key}"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "GetObject",
        )

    def head_bucket(self, Bucket: str):
        if Bucket not in self.buckets:
            raise self._not_found(Bucket)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str = "application/octet-stream"):
        self.ensure_bucket(Bucket)
        data = Body if isinstance(Body, (bytes, bytearray)) else Body.read()
        etag = f'"{hashlib.md5(data).hexdigest()}"'
        self.buckets[Bucket][Key] = {
            "body": bytes(data),
            "content_type": ContentType,
            "etag": etag,
            "last_modified": datetime.now(timezone.utc),
        }
        return {"ETag": etag}

    def head_object(self, Bucket: str, Key: str):
        entry = self.buckets.get(Bucket, {}).get(Key)
        if not entry:
            raise self._not_found(Key)
        return {
            "ContentType": entry["content_type"],
            "ContentLength": len(entry["body"]),
            "ETag": entry["etag"],
            "LastModified": entry["last_modified"],
        }

    def get_object(self, Bucket: str, Key: str):
        entry = self.buckets.get(Bucket, {}).get(Key)
        if not entry:
            raise self._not_found(Key)
        raw = io.BytesIO(entry["body"])
        return {
            "Body": StreamingBody(raw, len(entry["body"])),
            "ContentType": entry["content_type"],
            "ContentLength": len(entry["body"]),
            "ETag": entry["etag"],
            "LastModified": entry["last_modified"],
        }

    def delete_object(self, Bucket: str, Key: str):
        self.buckets.get(Bucket, {}).pop(Key, None)
        return {"ResponseMetadata": {"HTTPStatusCode": 204}}

    def get_paginator(self, operation_name: str):
        if operation_name != "list_objects_v2":
            raise NotImplementedError(operation_name)
        fake = self

        class _Paginator:
            def paginate(self, Bucket: str, Prefix: str = ""):
                items = []
                for key, entry in sorted(fake.buckets.get(Bucket, {}).items()):
                    if key.startswith(Prefix):
                        items.append({"Key": key, "Size": len(entry["body"])})
                yield {"Contents": items}

        return _Paginator()


class StorageServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.tmp_dir.name) / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.fake_r2 = FakeR2Client()
        self.fake_r2.ensure_bucket("reflens-io")

        self.svc = MediaStorageService()
        self.cfg_patch = patch.multiple(
            settings,
            UPLOAD_DIR=self.upload_dir,
            ROOT_PATH="",
            STORAGE_BACKEND="auto",
            R2_ACCOUNT_ID="acc123",
            R2_BUCKET_NAME="reflens-io",
            R2_ACCESS_KEY_ID="key123",
            R2_SECRET_ACCESS_KEY="secret123",
            R2_KEY_PREFIX="uploads",
            R2_PUBLIC_URL="",
            R2_LOCAL_CACHE=False,
        )
        self.cfg_patch.start()
        self.client_patch = patch.object(self.svc, "_get_client", return_value=self.fake_r2)
        self.client_patch.start()

    def tearDown(self) -> None:
        self.client_patch.stop()
        self.cfg_patch.stop()
        self.tmp_dir.cleanup()

    def test_mode_resolution_and_validation(self):
        self.assertEqual(self.svc.mode, "r2")
        with patch.object(settings, "R2_ACCESS_KEY_ID", ""):
            self.assertEqual(self.svc.mode, "local")
            with patch.object(settings, "STORAGE_BACKEND", "r2"):
                with self.assertRaises(RuntimeError):
                    _ = self.svc.mode
        with patch.object(settings, "STORAGE_BACKEND", "local"):
            self.assertEqual(self.svc.mode, "local")

    def test_path_extraction_and_traversal_protection(self):
        self.assertEqual(self.svc.extract_relative_path("/uploads/test.jpg"), "test.jpg")
        self.assertEqual(self.svc.extract_relative_path("uploads/test.jpg"), "test.jpg")
        self.assertEqual(self.svc.extract_relative_path("test.jpg"), "test.jpg")
        with patch.object(settings, "ROOT_PATH", "/RefLens.io"):
            self.assertEqual(self.svc.extract_relative_path("/RefLens.io/uploads/test.jpg"), "test.jpg")
        self.assertIsNone(self.svc.extract_relative_path("https://images.unsplash.com/photo-123"))

        with patch.object(settings, "R2_PUBLIC_URL", "https://cdn.wawa-app.me"):
            self.assertEqual(
                self.svc.extract_relative_path("https://cdn.wawa-app.me/uploads/pic.png"),
                "pic.png",
            )
            self.assertEqual(
                self.svc.file_path_for("pic.png"),
                "https://cdn.wawa-app.me/uploads/pic.png",
            )

        for unsafe in ("../etc/passwd", "/uploads/../../secret", "foo\\bar.jpg", "bad\x00.jpg"):
            with self.assertRaises(ValueError):
                self.svc.extract_relative_path(unsafe)

    def test_save_read_temp_context_and_delete_on_r2(self):
        data = _make_png_bytes()
        stored_path = self.svc.save_bytes_sync("sample.png", data, content_type="image/png")
        self.assertEqual(stored_path, "/uploads/sample.png")
        # R2 に存在し、R2_LOCAL_CACHE=False のためローカルディスクには残らないこと
        self.assertIn("uploads/sample.png", self.fake_r2.buckets["reflens-io"])
        self.assertFalse((self.upload_dir / "sample.png").exists())

        # R2 から読み出し可能
        self.assertTrue(self.svc.exists_sync(stored_path))
        self.assertEqual(self.svc.get_bytes_sync(stored_path), data)

        # local_file_path コンテキストで一時ファイルに展開され、抜けたら掃除されること
        with self.svc.local_file_path(stored_path) as tmp_path:
            self.assertIsNotNone(tmp_path)
            self.assertTrue(tmp_path.exists())
            self.assertEqual(tmp_path.read_bytes(), data)
        self.assertFalse(tmp_path.exists())

        # シード画像は保護され、通常画像は削除されること
        self.svc.save_bytes_sync("seed_ref_1.jpg", b"seed", content_type="image/jpeg")
        self.assertFalse(self.svc.delete_sync("/uploads/seed_ref_1.jpg", protect_seed=True))
        self.assertIn("uploads/seed_ref_1.jpg", self.fake_r2.buckets["reflens-io"])

        self.assertTrue(self.svc.delete_sync(stored_path))
        self.assertNotIn("uploads/sample.png", self.fake_r2.buckets["reflens-io"])
        self.assertFalse(self.svc.exists_sync(stored_path))


class StorageApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.tmp_dir.name) / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.fake_r2 = FakeR2Client()
        self.fake_r2.ensure_bucket("reflens-io")

        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        db = self.TestingSession()
        self.user = User(email="r2test@example.com", username="R2 Tester", auto_tagging=False)
        db.add(self.user)
        db.commit()
        db.refresh(self.user)
        self.board = Board(user_id=self.user.id, title="R2 Test Board")
        db.add(self.board)
        db.commit()
        db.refresh(self.board)
        self.user_id = self.user.id
        self.board_id = self.board.id
        db.close()

        def override_get_db():
            s = self.TestingSession()
            try:
                yield s
            finally:
                s.close()

        def override_current_user():
            s = self.TestingSession()
            try:
                return s.query(User).filter(User.id == self.user_id).first()
            finally:
                s.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        self.patches = [
            patch.multiple(
                settings,
                UPLOAD_DIR=self.upload_dir,
                ROOT_PATH="",
                STORAGE_BACKEND="r2",
                R2_ACCOUNT_ID="acc123",
                R2_BUCKET_NAME="reflens-io",
                R2_ACCESS_KEY_ID="key123",
                R2_SECRET_ACCESS_KEY="secret123",
                R2_KEY_PREFIX="uploads",
                R2_PUBLIC_URL="",
                R2_LOCAL_CACHE=False,
                LLM_PROVIDER="heuristic",
            ),
            patch.object(storage, "_get_client", return_value=self.fake_r2),
            patch("app.core.database.SessionLocal", self.TestingSession),
        ]
        for p in self.patches:
            p.start()

        self.client = TestClient(app, raise_server_exceptions=True)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        for p in reversed(self.patches):
            p.stop()
        self.engine.dispose()
        self.tmp_dir.cleanup()

    def test_upload_serve_head_etag_reanalyze_and_ref_delete(self):
        png_data = _make_png_bytes(64, 48, (250, 90, 40))

        # 1. アップロード → R2 へ保存され、ローカルには残らないこと
        resp = self.client.post(
            "/api/v1/media/upload",
            data={"board_id": self.board_id, "pos_x": "10", "pos_y": "20"},
            files={"file": ("test_art.png", png_data, "image/png")},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        item = resp.json()["item"]
        file_path = item["media"]["file_path"]
        media_id = item["media"]["id"]
        self.assertTrue(file_path.startswith("/uploads/"))
        object_key = f"uploads/{Path(file_path).name}"
        self.assertIn(object_key, self.fake_r2.buckets["reflens-io"])
        self.assertFalse((self.upload_dir / Path(file_path).name).exists())

        # 2. /uploads/{filename} の GET / HEAD / ETag 304 配信
        get_resp = self.client.get(file_path)
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.content, png_data)
        self.assertEqual(get_resp.headers["content-type"], "image/png")
        etag = get_resp.headers.get("etag")
        self.assertIsNotNone(etag)

        head_resp = self.client.head(file_path)
        self.assertEqual(head_resp.status_code, 200)
        self.assertEqual(head_resp.content, b"")
        self.assertEqual(head_resp.headers.get("content-length"), str(len(png_data)))

        not_mod = self.client.get(file_path, headers={"If-None-Match": etag})
        self.assertEqual(not_mod.status_code, 304)

        # パストラバーサルと 404 チェック
        self.assertEqual(self.client.get("/uploads/missing.jpg").status_code, 404)
        self.assertEqual(self.client.get("/uploads/%2e%2e/secret.txt").status_code, 400)

        # 3. R2 上の画像を使って AI 再解析 & 視覚検索が動くこと
        reanalyze_resp = self.client.post(f"/api/v1/media/{media_id}/reanalyze")
        self.assertEqual(reanalyze_resp.status_code, 200, reanalyze_resp.text)
        self.assertIn("palette", reanalyze_resp.json())

        vs_resp = self.client.post("/api/v1/media/visual-search", json={"media_item_id": media_id})
        self.assertEqual(vs_resp.status_code, 200, vs_resp.text)
        self.assertGreaterEqual(vs_resp.json()["total_matches"], 1)

        # 4. 同じ file_path を別レコードも参照している間は削除しても R2 に残り、最後の1件削除で R2 からも消えること
        db = self.TestingSession()
        dup = MediaItem(
            user_id=self.user_id,
            board_id=self.board_id,
            source_type="local_upload",
            file_path=file_path,
            width=64,
            height=48,
        )
        db.add(dup)
        db.commit()
        db.refresh(dup)
        dup_id = dup.id
        db.close()

        del1 = self.client.delete(f"/api/v1/bookmarks/{dup_id}")
        self.assertEqual(del1.status_code, 200)
        self.assertIn(object_key, self.fake_r2.buckets["reflens-io"])

        del2 = self.client.delete(f"/api/v1/bookmarks/{media_id}")
        self.assertEqual(del2.status_code, 200)
        self.assertNotIn(object_key, self.fake_r2.buckets["reflens-io"])

    def test_storage_status_endpoint(self):
        resp = self.client.get("/api/v1/media/storage/status?verify=true")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["backend"], "r2")
        self.assertEqual(body["bucket"], "reflens-io")
        self.assertTrue(body["r2_configured"])
        self.assertTrue(body["r2_reachable"])
        self.assertNotIn("secret", str(body).lower())

    def test_other_users_cannot_read_or_mutate_board(self):
        db = self.TestingSession()
        owner = User(email="other@example.com", username="Other")
        db.add(owner)
        db.flush()
        board = Board(user_id=owner.id, title="Private")
        db.add(board)
        db.flush()
        media = MediaItem(user_id=owner.id, board_id=board.id, file_path="/uploads/private.png", source_type="local_upload")
        db.add(media)
        db.flush()
        item = CanvasItem(board_id=board.id, media_item_id=media.id, pos_x=17, pos_y=23)
        db.add(item)
        db.commit()
        board_id, item_id = board.id, item.id
        base = f"/api/v1/boards/{board_id}"
        requests = [
            ("GET", base, None),
            ("PUT", base, {"title": "Changed"}),
            ("POST", base + "/items/batch", {"items": []}),
            ("POST", base + "/arrange", None),
            ("POST", base + "/save-to-folder", {"folder_name": "Stolen"}),
            ("POST", base + "/items/duplicate", {"item_ids": [item_id]}),
            ("DELETE", base + f"/items/{item_id}", None),
            ("DELETE", base, None),
            ("POST", "/api/v1/bookmarks/add", {"url": "https://example.com/image.png", "board_id": board_id}),
            ("POST", "/api/v1/media/import-url", {"image_url": "https://example.com/image.png", "board_id": board_id}),
        ]
        with patch.object(storage, "save_bytes") as save:
            for method, url, payload in requests:
                with self.subTest(method=method, url=url):
                    response = self.client.request(method, url, **({"json": payload} if payload is not None else {}))
                    self.assertEqual(response.status_code, 404, response.text)
            response = self.client.post("/api/v1/media/upload", data={"board_id": board_id}, files={"file": ("x.png", _make_png_bytes(), "image/png")})
            self.assertEqual(response.status_code, 404)
            save.assert_not_called()
        db.expire_all()
        self.assertEqual(db.get(Board, board_id).title, "Private")
        self.assertEqual(db.get(CanvasItem, item_id).pos_x, 17)
        db.close()

    def test_board_delete_cleans_storage_but_keeps_sibling_database_references(self):
        filename = "shared-across-environments.png"
        stored = storage.save_bytes_sync(filename, _make_png_bytes())
        db = self.TestingSession()
        db.add(MediaItem(user_id=self.user_id, board_id=self.board_id, source_type="local_upload", file_path=stored))
        db.commit()
        db.close()
        sibling = Path(self.tmp_dir.name) / "reflens-public.db"
        with sqlite3.connect(sibling) as conn:
            conn.execute("CREATE TABLE media_items (file_path TEXT)")
            conn.execute("INSERT INTO media_items VALUES (?)", (stored,))
        with patch.object(settings, "BASE_DIR", Path(self.tmp_dir.name)):
            response = self.client.delete(f"/api/v1/boards/{self.board_id}")
            self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(f"uploads/{filename}", self.fake_r2.buckets["reflens-io"])

    def test_board_delete_removes_unreferenced_r2_image(self):
        stored = storage.save_bytes_sync("board-only.png", _make_png_bytes())
        db = self.TestingSession()
        db.add(MediaItem(user_id=self.user_id, board_id=self.board_id, source_type="local_upload", file_path=stored))
        db.commit()
        db.close()
        with patch.object(settings, "BASE_DIR", Path(self.tmp_dir.name)):
            response = self.client.delete(f"/api/v1/boards/{self.board_id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("uploads/board-only.png", self.fake_r2.buckets["reflens-io"])

    def test_bookmark_add_saves_to_r2_and_batch_delete_cleans_up(self):
        img_bytes = _make_png_bytes(40, 30, (90, 200, 140))

        class _FakeResp:
            status_code = 200
            content = img_bytes
            headers = {"content-type": "image/png"}

        class _FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                return _FakeResp()

        with patch("app.routers.bookmarks.httpx.AsyncClient", _FakeAsyncClient):
            res = self.client.post(
                "/api/v1/bookmarks/add",
                json={
                    "url": "https://example.com/art/sample.png",
                    "title": "Sample R2 Bookmark",
                    "board_id": self.board_id,
                    "auto_tag": False,
                },
            )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        bm_id = body["bookmark_id"]
        fp = body["media_item"]["file_path"]
        self.assertTrue(fp.startswith("/uploads/"))
        object_key = f"uploads/{Path(fp).name}"
        self.assertIn(object_key, self.fake_r2.buckets["reflens-io"])
        self.assertFalse((self.upload_dir / Path(fp).name).exists())

        # GET /bookmarks/ のパレット抽出も R2 上の画像から問題なく取得できること
        list_res = self.client.get("/api/v1/bookmarks/")
        self.assertEqual(list_res.status_code, 200)
        found = [b for b in list_res.json() if b["id"] == bm_id]
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["ai_analysis"]["palette"])

        # batch delete で R2 からも削除されること
        del_res = self.client.post("/api/v1/bookmarks/batch/delete", json={"bookmark_ids": [bm_id]})
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["count"], 1)
        self.assertNotIn(object_key, self.fake_r2.buckets["reflens-io"])


class MigrationScriptTests(unittest.TestCase):
    def test_same_size_different_content_is_not_deleted_or_overwritten(self):
        from scripts import migrate_to_r2
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "same.png"
            source.write_bytes(b"local")
            fake = FakeR2Client()
            fake.put_object(Bucket="reflens-io", Key="uploads/same.png", Body=b"other")
            with patch.multiple(settings, R2_ACCOUNT_ID="acc", R2_BUCKET_NAME="reflens-io", R2_ACCESS_KEY_ID="key", R2_SECRET_ACCESS_KEY="secret"), patch.object(storage, "_get_client", return_value=fake), patch.object(migrate_to_r2, "DEFAULT_DBS", []), patch("sys.argv", ["migrate_to_r2.py", "--dir", tmp, "--delete-local"]):
                self.assertEqual(migrate_to_r2.main(), 1)
            self.assertEqual(source.read_bytes(), b"local")
            self.assertEqual(fake.buckets["reflens-io"]["uploads/same.png"]["body"], b"other")

    def test_local_conflicts_abort_before_contacting_r2(self):
        from scripts import migrate_to_r2
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            a.mkdir()
            b.mkdir()
            (a / "same.png").write_bytes(b"first")
            (b / "same.png").write_bytes(b"other")
            with patch.object(storage.__class__, "is_r2_configured", new_callable=PropertyMock, return_value=True), patch.object(storage, "_get_client") as client, patch("sys.argv", ["migrate_to_r2.py", "--dir", str(a), "--dir", str(b)]):
                self.assertEqual(migrate_to_r2.main(), 1)
                client.assert_not_called()

    def test_migrate_to_r2_uploads_deduplicates_and_respects_seed_protection(self):
        from scripts import migrate_to_r2

        with tempfile.TemporaryDirectory() as tmp:
            dir_a = Path(tmp) / "uploads"
            dir_b = Path(tmp) / "public-uploads"
            dir_a.mkdir()
            dir_b.mkdir()

            data1 = _make_png_bytes(16, 16, (10, 20, 30))
            data_seed = _make_png_bytes(16, 16, (40, 50, 60))
            (dir_a / "art1.png").write_bytes(data1)
            (dir_b / "art1.png").write_bytes(data1)
            (dir_a / "seed_ref_1.jpg").write_bytes(data_seed)

            fake_r2 = FakeR2Client()
            fake_r2.ensure_bucket("reflens-io")

            with patch.multiple(
                settings,
                R2_ACCOUNT_ID="acc123",
                R2_BUCKET_NAME="reflens-io",
                R2_ACCESS_KEY_ID="key123",
                R2_SECRET_ACCESS_KEY="secret123",
                R2_KEY_PREFIX="uploads",
            ), patch.object(storage, "_get_client", return_value=fake_r2), patch.object(
                migrate_to_r2, "DEFAULT_DBS", []
            ):
                # 1回目: アップロード実行（シードは残し art1 のみローカル削除テスト）
                with patch("sys.argv", ["migrate_to_r2.py", "--dir", str(dir_a), "--dir", str(dir_b), "--delete-local"]):
                    rc = migrate_to_r2.main()
                self.assertEqual(rc, 0)

            self.assertIn("uploads/art1.png", fake_r2.buckets["reflens-io"])
            self.assertIn("uploads/seed_ref_1.jpg", fake_r2.buckets["reflens-io"])
            self.assertEqual(fake_r2.buckets["reflens-io"]["uploads/art1.png"]["body"], data1)
            self.assertFalse((dir_a / "art1.png").exists())
            self.assertFalse((dir_b / "art1.png").exists())
            self.assertTrue((dir_a / "seed_ref_1.jpg").exists())


if __name__ == "__main__":
    unittest.main()
