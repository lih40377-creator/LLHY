import io
import json
import os
import base64
import tempfile
import unittest
import zipfile

_uploads = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret"
os.environ["UPLOAD_DIR"] = _uploads.name

from app import app  # noqa: E402
from models import Note, NoteAttachment, NoteRevision, User, db  # noqa: E402


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
        self.client.get("/")

    def token(self):
        with self.client.session_transaction() as saved:
            return saved["csrf_token"]

    def register_and_login(self, username="alice", password="secure123"):
        self.client.post("/register", data={"csrf_token": self.token(), "username": username, "password": password})
        return self.client.post("/", data={"csrf_token": self.token(), "username": username, "password": password}, follow_redirects=True)

    def test_account_and_note_workflow(self):
        response = self.register_and_login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("我的笔记", response.get_data(as_text=True))
        with app.app_context():
            self.assertNotEqual(User.query.first().password, "secure123")
        response = self.client.post("/write", data={"csrf_token": self.token(), "title": "Flask 学习", "content": "今天学习路由", "tags": "Python, 学习", "is_pinned": "1"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("今天学习路由", response.get_data(as_text=True))
        self.assertIn("Flask 学习", self.client.get("/home?tag=Python").get_data(as_text=True))
        self.assertEqual(self.client.get("/delete/1").status_code, 405)
        self.assertEqual(self.client.post("/delete/1", data={}).status_code, 400)
        self.client.post("/note/1/toggle/archive", data={"csrf_token": self.token()})
        self.assertNotIn("Flask 学习", self.client.get("/home").get_data(as_text=True))
        self.assertIn("Flask 学习", self.client.get("/home?view=archived").get_data(as_text=True))

    def test_export_import_and_ownership(self):
        self.register_and_login()
        self.client.post("/write", data={"csrf_token": self.token(), "title": "第一篇", "content": "内容", "tags": "日记"})
        response = self.client.post("/export", data={"csrf_token": self.token(), "format": "json"})
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.data)
        self.assertEqual(payload["notes"][0]["title"], "第一篇")
        self.client.post("/import", data={"csrf_token": self.token(), "file": (io.BytesIO(response.data), "backup.json")}, content_type="multipart/form-data")
        with app.app_context():
            self.assertEqual(Note.query.count(), 2)
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.client.get("/")
        self.register_and_login("bob", "secure456")
        self.assertEqual(self.client.get("/note/1").status_code, 403)
        self.assertEqual(self.client.get("/home").status_code, 200)
        self.assertNotIn('href="/note/1"', self.client.get("/home").get_data(as_text=True))

    def test_legacy_login_and_document_exports(self):
        with app.app_context():
            db.session.add(User(username="legacy", password="old-password", role="user"))
            db.session.commit()
        response = self.client.post("/", data={"csrf_token": self.token(), "username": "legacy", "password": "old-password"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertTrue(User.query.filter_by(username="legacy").first().password.startswith("scrypt:"))
        self.client.post("/write", data={"csrf_token": self.token(), "title": "中文标题", "content": "第一行\n第二行"})
        for kind, magic in (("word", b"PK"), ("pdf", b"%PDF")):
            with self.subTest(kind=kind):
                result = self.client.post("/export", data={"csrf_token": self.token(), "format": kind})
                self.assertEqual(result.status_code, 200)
                self.assertTrue(result.data.startswith(magic))

    def test_autosave_markdown_history_and_trash(self):
        self.register_and_login()
        headers = {"X-CSRF-Token": self.token()}
        created = self.client.post("/api/notes/autosave", json={"title": "草稿", "content": "**起点**", "tags": "学习", "is_pinned": False}, headers=headers)
        self.assertEqual(created.status_code, 200)
        note_id = created.json["id"]
        home = self.client.get("/home").get_data(as_text=True)
        self.assertIn("草稿", home)
        self.assertNotIn("**起点**", home)
        detail = self.client.get(f"/note/{note_id}").get_data(as_text=True)
        self.assertIn("<strong>起点</strong>", detail)
        preview = self.client.post("/markdown/preview", json={"content": "**安全** <script>alert(1)</script> [坏链接](javascript:alert(1))"}, headers=headers)
        self.assertEqual(preview.status_code, 200)
        self.assertIn("<strong>安全</strong>", preview.json["html"])
        self.assertNotIn("<script", preview.json["html"])
        self.assertNotIn("javascript:", preview.json["html"])
        checklist = self.client.post("/markdown/preview", json={"content": "- [ ] 待完成\n- [x] 已完成"}, headers=headers)
        self.assertIn("☐", checklist.json["html"])
        self.assertIn("☑", checklist.json["html"])
        edited = self.client.post(f"/edit/{note_id}", data={"csrf_token": self.token(), "title": "完成的笔记", "content": "新内容", "tags": "学习"}, follow_redirects=True)
        self.assertEqual(edited.status_code, 200)
        with app.app_context():
            revisions = NoteRevision.query.filter_by(note_id=note_id).order_by(NoteRevision.id).all()
            self.assertGreaterEqual(len(revisions), 2)
            first_id = revisions[0].id
        self.assertEqual(self.client.get(f"/note/{note_id}/versions").status_code, 200)
        self.assertEqual(self.client.get(f"/note/{note_id}/versions/{first_id}").status_code, 200)
        restored = self.client.post(f"/note/{note_id}/versions/{first_id}/restore", data={"csrf_token": self.token()}, follow_redirects=True)
        self.assertIn("<strong>起点</strong>", restored.get_data(as_text=True))
        self.client.post(f"/delete/{note_id}", data={"csrf_token": self.token()})
        self.assertNotIn('href="/note/1"', self.client.get("/home").get_data(as_text=True))
        self.assertIn("草稿", self.client.get("/home?view=trash").get_data(as_text=True))
        self.client.post(f"/note/{note_id}/restore", data={"csrf_token": self.token()})
        self.assertIn("草稿", self.client.get("/home").get_data(as_text=True))
        self.client.post(f"/delete/{note_id}", data={"csrf_token": self.token()})
        self.client.post(f"/note/{note_id}/purge", data={"csrf_token": self.token()})
        self.assertEqual(self.client.get(f"/note/{note_id}").status_code, 404)

    def test_attachment_access_and_validation(self):
        self.register_and_login()
        self.client.post("/write", data={"csrf_token": self.token(), "title": "带附件", "content": "内容"})
        invalid = self.client.post("/note/1/attachments", data={"csrf_token": self.token(), "attachments": (io.BytesIO(b"not an image"), "fake.png")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("仅支持有效的", invalid.get_data(as_text=True))
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII=")
        uploaded = self.client.post("/note/1/attachments", data={"csrf_token": self.token(), "attachments": (io.BytesIO(png), "pixel.png")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(uploaded.status_code, 200)
        with app.app_context():
            attachment = NoteAttachment.query.first()
            attachment_id = attachment.id
        attachment_response = self.client.get(f"/attachments/{attachment_id}")
        self.assertEqual(attachment_response.data, png)
        attachment_response.close()
        backup = self.client.post("/export", data={"csrf_token": self.token(), "format": "zip"})
        self.assertEqual(backup.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(backup.data)) as archive:
            self.assertIn("notes.json", archive.namelist())
            self.assertEqual(len(json.loads(archive.read("notes.json"))["notes"][0]["attachments"]), 1)
        imported = self.client.post("/import", data={"csrf_token": self.token(), "file": (io.BytesIO(backup.data), "backup.zip")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(imported.status_code, 200)
        with app.app_context():
            self.assertEqual(NoteAttachment.query.count(), 2)
            self.assertEqual(Note.query.count(), 2)
            self.assertEqual(NoteRevision.query.count(), 2)
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.client.get("/")
        self.register_and_login("bob", "secure456")
        self.assertEqual(self.client.get(f"/attachments/{attachment_id}").status_code, 403)

    def test_admin_can_review_trash(self):
        with app.app_context():
            db.session.add(User(username="admin", password="admin-password", role="admin"))
            db.session.commit()
        self.client.post("/", data={"csrf_token": self.token(), "username": "admin", "password": "admin-password"}, follow_redirects=True)
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.get("/admin/notes?view=trash").status_code, 200)


if __name__ == "__main__":
    unittest.main()
