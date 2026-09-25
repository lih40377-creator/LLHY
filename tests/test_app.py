import io
import json
import os
import unittest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret"

from app import app  # noqa: E402
from models import Note, User, db  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
