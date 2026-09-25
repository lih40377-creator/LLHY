"""Personal notes workspace built with Flask."""
import hmac
import html
import io
import json
import os
import re
import secrets
import uuid
import zipfile
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from markupsafe import Markup
import markdown
import nh3
from werkzeug.datastructures import FileStorage
from sqlalchemy import inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash

from models import Note, NoteAttachment, NoteRevision, User, db

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.instance_path = str(ROOT / "instance")
Path(app.instance_path).mkdir(exist_ok=True)
secret_file = Path(app.instance_path) / "secret_key"
if not os.environ.get("SECRET_KEY") and not secret_file.exists():
    secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secret_file.read_text(encoding="utf-8"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL") or "sqlite:///notes.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=30 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PUBLIC_HTTPS") == "1",
)
db.init_app(app)
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or Path(app.instance_path) / "uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def migrate_database():
    """Preserve original SQLite notes while adding workspace fields."""
    with app.app_context():
        db.create_all()
        columns = {column["name"] for column in inspect(db.engine).get_columns("note")}
        additions = {"updated_at": "DATETIME", "tags": "VARCHAR(500) DEFAULT ''", "is_pinned": "BOOLEAN DEFAULT 0", "is_archived": "BOOLEAN DEFAULT 0", "is_draft": "BOOLEAN DEFAULT 0", "deleted_at": "DATETIME"}
        for name, definition in additions.items():
            if name not in columns:
                db.session.execute(text(f"ALTER TABLE note ADD COLUMN {name} {definition}"))
        db.session.commit()


migrate_database()


@app.get("/healthz")
def healthz():
    """A small public endpoint for hosting health checks."""
    db.session.execute(text("SELECT 1"))
    return jsonify(status="ok")


@app.before_request
def protect_forms():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, "表单已过期，请刷新页面后重试。")


@app.context_processor
def template_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"], "clear_draft_key": session.pop("clear_draft_key", "")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def own_note(note_id):
    note = db.session.get(Note, note_id)
    if note is None:
        abort(404)
    if note.user_id != session["user_id"] and session.get("role") != "admin":
        abort(403)
    return note


def normalize_tags(raw):
    parts = re.split(r"[,，、\n]+", raw or "")
    return ",".join(dict.fromkeys(part.strip().lstrip("#")[:30] for part in parts if part.strip()))[:500]


MARKDOWN_TAGS = {"p", "br", "strong", "em", "del", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote", "pre", "code", "a", "hr", "table", "thead", "tbody", "tr", "th", "td"}


def render_markdown(value):
    source = re.sub(r"(?m)^(\s*[-*+] )\[ \] ", r"\1☐ ", value or "")
    source = re.sub(r"(?mi)^(\s*[-*+] )\[x\] ", r"\1☑ ", source)
    html = markdown.markdown(source, extensions=["fenced_code", "tables", "sane_lists", "nl2br"])
    return Markup(nh3.clean(html, tags=MARKDOWN_TAGS, attributes={"a": {"href", "title"}}))


app.add_template_filter(render_markdown, "render_markdown")


def note_excerpt(value):
    plain = re.sub(r"<[^>]+>", " ", str(render_markdown(value)))
    return re.sub(r"\s+", " ", html.unescape(plain)).strip()[:150] or "这篇笔记还没有内容。"


app.add_template_filter(note_excerpt, "note_excerpt")


def snapshot(note, force=False):
    latest = NoteRevision.query.filter_by(note_id=note.id).order_by(NoteRevision.saved_at.desc(), NoteRevision.id.desc()).first()
    unchanged = latest and (latest.title, latest.content, latest.tags or "") == (note.title, note.content, note.tags or "")
    if unchanged or (not force and latest and (datetime.now() - latest.saved_at).total_seconds() < 180):
        return
    db.session.add(NoteRevision(note_id=note.id, title=note.title, content=note.content, tags=note.tags or ""))
    db.session.flush()
    old = NoteRevision.query.filter_by(note_id=note.id).order_by(NoteRevision.saved_at.desc(), NoteRevision.id.desc()).offset(100).all()
    for revision in old:
        db.session.delete(revision)


def prepared_uploads(files):
    files = [file for file in files if file and file.filename]
    if len(files) > 5:
        raise ValueError("一次最多上传 5 个附件。")
    prepared = []
    for file in files:
        name = file.filename.replace("\\", "/").split("/")[-1].strip()[:255]
        payload = file.read(5 * 1024 * 1024 + 1)
        if not name or not payload or len(payload) > 5 * 1024 * 1024:
            raise ValueError("每个附件需小于 5 MB。")
        suffix = Path(name).suffix.lower()
        signatures = {
            ".png": ("image/png", payload.startswith(b"\x89PNG\r\n\x1a\n")),
            ".jpg": ("image/jpeg", payload.startswith(b"\xff\xd8\xff")),
            ".jpeg": ("image/jpeg", payload.startswith(b"\xff\xd8\xff")),
            ".webp": ("image/webp", payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"),
            ".pdf": ("application/pdf", payload.startswith(b"%PDF-")),
        }
        if suffix not in signatures or not signatures[suffix][1]:
            raise ValueError("仅支持有效的 PNG、JPG、WebP 图片和 PDF 文件。")
        prepared.append((name, signatures[suffix][0], suffix, payload))
    return prepared


def save_attachments(note, uploads):
    for name, mime, suffix, payload in uploads:
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        (UPLOAD_DIR / stored_name).write_bytes(payload)
        db.session.add(NoteAttachment(note_id=note.id, stored_name=stored_name, original_name=name, mime_type=mime, size=len(payload)))


def cleanup_attachments(attachments):
    for attachment in attachments:
        (UPLOAD_DIR / attachment.stored_name).unlink(missing_ok=True)


def parse_day(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d") if value else None
    except ValueError:
        abort(400, "日期格式无效。")


def filtered_notes(all_users=False, values=None):
    values = values or request.args
    query = Note.query if all_users else Note.query.filter_by(user_id=session["user_id"])
    keyword = (values.get("keyword") or "").strip()[:100]
    if keyword:
        term = f"%{keyword}%"
        query = query.filter(or_(Note.title.ilike(term), Note.content.ilike(term), Note.tags.ilike(term)))
    tag = (values.get("tag") or "").strip()[:30]
    if tag:
        query = query.filter(or_(Note.tags == tag, Note.tags.like(f"{tag},%"), Note.tags.like(f"%,{tag}"), Note.tags.like(f"%,{tag},%")))
    start, end = parse_day(values.get("start_date")), parse_day(values.get("end_date"))
    if start:
        query = query.filter(Note.create_time >= start)
    if end:
        query = query.filter(Note.create_time < end + timedelta(days=1))
    view = values.get("view", "active")
    if view == "trash":
        return query.filter(Note.deleted_at.isnot(None)).order_by(Note.deleted_at.desc())
    query = query.filter(Note.deleted_at.is_(None))
    if view == "archived":
        query = query.filter(Note.is_archived.is_(True))
    elif view != "all":
        query = query.filter(or_(Note.is_archived.is_(False), Note.is_archived.is_(None)))
    if view == "pinned":
        query = query.filter(Note.is_pinned.is_(True))
    return query.order_by(Note.is_pinned.desc(), Note.updated_at.desc(), Note.create_time.desc())


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()
        hashed = user and user.password.startswith(("scrypt:", "pbkdf2:"))
        valid = user and (check_password_hash(user.password, password) if hashed else hmac.compare_digest(user.password, password))
        if valid:
            if not hashed:
                user.password = generate_password_hash(password)
                db.session.commit()
            session.clear()
            session.update(user_id=user.id, username=user.username, role=user.role)
            flash("欢迎回来。", "success")
            return redirect(url_for("admin") if user.role == "admin" else url_for("home"))
        flash("账号或密码错误。", "error")
    elif "user_id" in session:
        return redirect(url_for("admin") if session.get("role") == "admin" else url_for("home"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not 3 <= len(username) <= 50 or not 8 <= len(password) <= 128:
            flash("用户名需 3–50 字，密码需 8–128 字。", "error")
        elif User.query.filter_by(username=username).first():
            flash("用户名已存在。", "error")
        else:
            db.session.add(User(username=username, password=generate_password_hash(password), role="user"))
            db.session.commit()
            flash("注册成功，请登录。", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    if session.get("role") == "admin":
        return redirect(url_for("admin"))
    notes = filtered_notes().all()
    all_notes = Note.query.filter_by(user_id=session["user_id"]).all()
    current_notes = [note for note in all_notes if note.deleted_at is None]
    tags = sorted({tag for note in current_notes for tag in note.tag_list}, key=str.casefold)
    return render_template("home.html", notes=notes, tags=tags, total=len(current_notes), active=sum(not n.is_archived for n in current_notes), pinned=sum(bool(n.is_pinned and not n.is_archived) for n in current_notes), archived=sum(bool(n.is_archived) for n in current_notes), trash=len(all_notes) - len(current_notes), drafts=sum(bool(n.is_draft) for n in current_notes), view=request.args.get("view", "active"))


@app.route("/write", methods=["GET", "POST"])
@login_required
def write():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:200]
        if title:
            try:
                uploads = prepared_uploads(request.files.getlist("attachments"))
            except ValueError as error:
                flash(str(error), "error")
                return render_template("editor.html", note=None, heading="新建笔记"), 400
            draft_id = request.form.get("note_id", "")
            note = own_note(int(draft_id)) if draft_id.isdigit() else None
            if note and (note.deleted_at or not note.is_draft):
                abort(400)
            if note is None:
                note = Note(user_id=session["user_id"], title=title)
                db.session.add(note)
            if len(note.attachments) + len(uploads) > 30:
                flash("每篇笔记最多保存 30 个附件。", "error")
                return render_template("editor.html", note=note, heading="新建笔记"), 400
            db.session.flush()
            note.title = title
            note.content = (request.form.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
            note.tags = normalize_tags(request.form.get("tags"))
            note.is_pinned = bool(request.form.get("is_pinned"))
            note.is_draft = False
            note.updated_at = datetime.now()
            snapshot(note, force=True)
            save_attachments(note, uploads)
            db.session.commit()
            session["clear_draft_key"] = "new-note"
            flash("笔记已保存。", "success")
            return redirect(url_for("note_detail", id=note.id))
        flash("请填写标题。", "error")
    return render_template("editor.html", note=None, heading="新建笔记")


@app.route("/note/<int:id>")
@login_required
def note_detail(id):
    note = own_note(id)
    return render_template("note_detail.html", note=note, revisions=note.revisions[:20])


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    note = own_note(id)
    if note.deleted_at:
        abort(404)
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:200]
        if title:
            try:
                uploads = prepared_uploads(request.files.getlist("attachments"))
            except ValueError as error:
                flash(str(error), "error")
                return render_template("editor.html", note=note, heading="编辑笔记"), 400
            if len(note.attachments) + len(uploads) > 30:
                flash("每篇笔记最多保存 30 个附件。", "error")
                return render_template("editor.html", note=note, heading="编辑笔记"), 400
            snapshot(note, force=True)
            note.title = title
            note.content = (request.form.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
            note.tags = normalize_tags(request.form.get("tags"))
            note.is_pinned = bool(request.form.get("is_pinned"))
            note.is_draft = False
            note.updated_at = datetime.now()
            snapshot(note, force=True)
            save_attachments(note, uploads)
            db.session.commit()
            session["clear_draft_key"] = f"note-{id}"
            flash("修改已保存。", "success")
            return redirect(url_for("note_detail", id=id))
        flash("请填写标题。", "error")
    return render_template("editor.html", note=note, heading="编辑笔记")


@app.post("/delete/<int:id>")
@login_required
def delete(id):
    note = own_note(id)
    if note.deleted_at:
        abort(400)
    note.deleted_at = datetime.now()
    db.session.commit()
    flash("笔记已移入回收站，可以随时恢复。", "success")
    return redirect(url_for("admin_notes") if session.get("role") == "admin" else url_for("home"))


@app.post("/note/<int:id>/restore")
@login_required
def restore_note(id):
    note = own_note(id)
    if note.deleted_at is None:
        abort(400)
    note.deleted_at = None
    db.session.commit()
    flash("笔记已恢复。", "success")
    return redirect(url_for("note_detail", id=id))


@app.post("/note/<int:id>/purge")
@login_required
def purge_note(id):
    note = own_note(id)
    if note.deleted_at is None:
        abort(400)
    files = list(note.attachments)
    db.session.delete(note)
    db.session.commit()
    cleanup_attachments(files)
    flash("笔记已永久删除。", "success")
    return redirect(url_for("admin_notes", view="trash") if session.get("role") == "admin" else url_for("home", view="trash"))


@app.post("/note/<int:id>/toggle/<action>")
@login_required
def toggle_note(id, action):
    note = own_note(id)
    if note.deleted_at:
        abort(404)
    if action not in {"pin", "archive"}:
        abort(404)
    field = "is_pinned" if action == "pin" else "is_archived"
    setattr(note, field, not bool(getattr(note, field)))
    note.updated_at = datetime.now()
    db.session.commit()
    return redirect(request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for("home"))


@app.post("/markdown/preview")
@login_required
def markdown_preview():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not isinstance(content, str) or len(content) > 100000:
        abort(400)
    return jsonify(html=str(render_markdown(content)))


@app.post("/api/notes/autosave")
@login_required
def autosave_note():
    data = request.get_json(silent=True) or {}
    title, content, tags = data.get("title", ""), data.get("content", ""), data.get("tags", "")
    if not all(isinstance(value, str) for value in (title, content, tags)) or len(content) > 100000:
        abort(400)
    title = title.strip()[:200]
    if not title and not content.strip():
        return jsonify(saved=False)
    note_id = data.get("note_id")
    if note_id is None:
        note = Note(user_id=session["user_id"], title=title or "未命名笔记", is_draft=True)
        db.session.add(note)
        db.session.flush()
    elif isinstance(note_id, int):
        note = own_note(note_id)
        if note.deleted_at:
            abort(404)
    else:
        abort(400)
    note.title = title or "未命名笔记"
    note.content = content.replace("\r\n", "\n").replace("\r", "\n")
    note.tags = normalize_tags(tags)
    note.is_pinned = bool(data.get("is_pinned"))
    note.updated_at = datetime.now()
    snapshot(note)
    db.session.commit()
    return jsonify(saved=True, id=note.id, edit_url=url_for("edit", id=note.id), saved_at=note.updated_at.strftime("%H:%M:%S"))


@app.route("/note/<int:id>/versions")
@login_required
def note_versions(id):
    note = own_note(id)
    return render_template("versions.html", note=note, revisions=note.revisions)


@app.route("/note/<int:id>/versions/<int:revision_id>")
@login_required
def version_detail(id, revision_id):
    note = own_note(id)
    revision = NoteRevision.query.filter_by(id=revision_id, note_id=id).first_or_404()
    return render_template("version_detail.html", note=note, revision=revision)


@app.post("/note/<int:id>/versions/<int:revision_id>/restore")
@login_required
def restore_version(id, revision_id):
    note = own_note(id)
    if note.deleted_at:
        abort(400)
    revision = NoteRevision.query.filter_by(id=revision_id, note_id=id).first_or_404()
    snapshot(note, force=True)
    note.title, note.content, note.tags = revision.title, revision.content, revision.tags
    note.updated_at = datetime.now()
    note.is_draft = False
    snapshot(note, force=True)
    db.session.commit()
    flash("已恢复该历史版本。", "success")
    return redirect(url_for("note_detail", id=id))


@app.post("/note/<int:id>/attachments")
@login_required
def upload_attachments(id):
    note = own_note(id)
    if note.deleted_at:
        abort(400)
    try:
        uploads = prepared_uploads(request.files.getlist("attachments"))
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("note_detail", id=id))
    if not uploads:
        flash("请选择要上传的文件。", "error")
    elif len(note.attachments) + len(uploads) > 30:
        flash("每篇笔记最多保存 30 个附件。", "error")
    else:
        save_attachments(note, uploads)
        db.session.commit()
        flash(f"已添加 {len(uploads)} 个附件。", "success")
    return redirect(url_for("note_detail", id=id))


@app.get("/attachments/<int:attachment_id>")
@login_required
def get_attachment(attachment_id):
    attachment = db.session.get(NoteAttachment, attachment_id)
    if attachment is None:
        abort(404)
    own_note(attachment.note_id)
    path = UPLOAD_DIR / attachment.stored_name
    if not path.is_file():
        abort(404)
    response = send_file(path, mimetype=attachment.mime_type, as_attachment=attachment.mime_type == "application/pdf" or request.args.get("download") == "1", download_name=attachment.original_name)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, max-age=300"
    return response


@app.post("/attachments/<int:attachment_id>/delete")
@login_required
def delete_attachment(attachment_id):
    attachment = db.session.get(NoteAttachment, attachment_id)
    if attachment is None:
        abort(404)
    own_note(attachment.note_id)
    note_id = attachment.note_id
    db.session.delete(attachment)
    db.session.commit()
    cleanup_attachments([attachment])
    flash("附件已删除。", "success")
    return redirect(url_for("note_detail", id=note_id))


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        return redirect(url_for("search", **{key: value for key, value in request.form.items() if key != "csrf_token"}))
    return render_template("search.html", notes=filtered_notes(all_users=session.get("role") == "admin").all())


def note_record(note):
    return {"title": note.title, "content": note.content, "tags": note.tag_list, "created_at": note.create_time.isoformat(), "updated_at": note.updated_at.isoformat() if note.updated_at else None, "pinned": bool(note.is_pinned), "archived": bool(note.is_archived), "draft": bool(note.is_draft)}


def export_bytes(notes, kind):
    if kind == "json":
        data = [note_record(n) for n in notes]
        return json.dumps({"version": 2, "attachments_included": False, "notes": data}, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", "json"
    if kind == "zip":
        buffer = io.BytesIO()
        manifest = {"version": 3, "notes": []}
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for note_index, note in enumerate(notes):
                record = note_record(note)
                record["attachments"] = []
                record["revisions"] = [{"title": revision.title, "content": revision.content, "tags": revision.tags, "saved_at": revision.saved_at.isoformat()} for revision in note.revisions]
                for attachment_index, attachment in enumerate(note.attachments):
                    path = UPLOAD_DIR / attachment.stored_name
                    if not path.is_file():
                        abort(409, "附件文件缺失，备份未生成。")
                    archive_name = f"attachments/{note_index}/{attachment_index}{Path(attachment.stored_name).suffix}"
                    archive.write(path, archive_name)
                    record["attachments"].append({"archive_name": archive_name, "filename": attachment.original_name})
                manifest["notes"].append(record)
            archive.writestr("notes.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        return buffer.getvalue(), "application/zip", "zip"
    if kind in {"txt", "md"}:
        blocks = [f"{'# ' if kind == 'md' else ''}{n.title}\n{n.create_time:%Y-%m-%d %H:%M} · {', '.join(n.tag_list)}\n\n{n.content}" for n in notes]
        return ("\n\n---\n\n".join(blocks) + "\n").encode("utf-8-sig"), "text/plain; charset=utf-8", kind
    if kind == "word":
        from docx import Document
        document = Document()
        document.add_heading("我的学习笔记", 0)
        for n in notes:
            document.add_heading(n.title, 1)
            document.add_paragraph(n.content)
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
    if kind == "pdf":
        from xml.sax.saxutils import escape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        body = ParagraphStyle("body", fontName="STSong-Light", fontSize=11, leading=18, spaceAfter=14)
        title = ParagraphStyle("title", parent=body, fontSize=17, leading=24)
        story = []
        for n in notes:
            story.extend([Paragraph(escape(n.title), title), Paragraph(escape(n.content).replace("\n", "<br/>"), body), Spacer(1, 15)])
        buffer = io.BytesIO()
        SimpleDocTemplate(buffer).build(story)
        return buffer.getvalue(), "application/pdf", "pdf"
    abort(400, "不支持的导出格式。")


@app.route("/export", methods=["GET", "POST"])
@login_required
def export():
    all_users = session.get("role") == "admin"
    if request.method == "GET":
        return render_template("export.html", notes=filtered_notes(all_users=all_users, values={"view": "all"}).all())
    notes = filtered_notes(all_users=all_users, values={**request.form, "view": "all"})
    raw_ids = request.form.getlist("note_ids")
    if raw_ids:
        try:
            ids = [int(value) for value in raw_ids]
        except ValueError:
            abort(400)
        notes = notes.filter(Note.id.in_(ids))
    selected = notes.all()
    if not selected:
        flash("没有符合条件的笔记。", "error")
        return redirect(url_for("export"))
    payload, mime, extension = export_bytes(selected, request.form.get("format", "json"))
    return send_file(io.BytesIO(payload), mimetype=mime, as_attachment=True, download_name=f"notes-{datetime.now():%Y%m%d-%H%M}.{extension}")


@app.post("/import")
@login_required
def import_notes():
    upload = request.files.get("file")
    if not upload or not upload.filename.lower().endswith((".json", ".zip")):
        flash("请选择本应用导出的 JSON 或 ZIP 备份。", "error")
        return redirect(url_for("export"))
    archive = None
    try:
        is_zip = upload.filename.lower().endswith(".zip")
        archive = zipfile.ZipFile(upload.stream) if is_zip else None
        if archive:
            manifest_info = archive.getinfo("notes.json")
            if manifest_info.file_size > 3 * 1024 * 1024:
                raise ValueError
            data = json.loads(archive.read("notes.json"))
        else:
            data = json.load(upload)
        items = data["notes"]
        if not isinstance(items, list) or len(items) > 500:
            raise ValueError
        prepared = []
        total_attachment_bytes = 0
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip() or not isinstance(item.get("content", ""), str):
                raise ValueError
            if len(item["content"]) > 1000000:
                raise ValueError
            tags = item.get("tags", [])
            created_at = datetime.fromisoformat(item["created_at"]) if item.get("created_at") else datetime.now()
            updated_at = datetime.fromisoformat(item["updated_at"]) if item.get("updated_at") else created_at
            note = Note(title=item["title"].strip()[:200], content=item["content"], tags=normalize_tags(",".join(tags) if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags) else ""), is_pinned=bool(item.get("pinned")), is_archived=bool(item.get("archived")), is_draft=bool(item.get("draft")), user_id=session["user_id"], create_time=created_at, updated_at=updated_at)
            uploads = []
            revisions = []
            if archive:
                attachment_entries = item.get("attachments", [])
                revision_entries = item.get("revisions", [])
                if not isinstance(attachment_entries, list) or len(attachment_entries) > 30 or not isinstance(revision_entries, list) or len(revision_entries) > 100:
                    raise ValueError
                for entry in attachment_entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get("archive_name"), str) or not isinstance(entry.get("filename"), str):
                        raise ValueError
                    info = archive.getinfo(entry["archive_name"])
                    total_attachment_bytes += info.file_size
                    if info.file_size > 5 * 1024 * 1024 or total_attachment_bytes > 30 * 1024 * 1024:
                        raise ValueError
                    payload = archive.read(info)
                    uploads.extend(prepared_uploads([FileStorage(io.BytesIO(payload), filename=entry["filename"])]))
                for entry in revision_entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get("title"), str) or not isinstance(entry.get("content"), str) or not isinstance(entry.get("tags", ""), str):
                        raise ValueError
                    if len(entry["content"]) > 1000000:
                        raise ValueError
                    revisions.append(NoteRevision(title=entry["title"][:200], content=entry["content"], tags=entry.get("tags", "")[:500], saved_at=datetime.fromisoformat(entry["saved_at"])))
            prepared.append((note, uploads, revisions))
        if archive:
            archive.close()
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile, RuntimeError):
        if archive:
            archive.close()
        flash("备份文件格式无效。", "error")
        return redirect(url_for("export"))
    db.session.add_all(note for note, _, _ in prepared)
    db.session.flush()
    for note, uploads, revisions in prepared:
        for revision in revisions:
            revision.note_id = note.id
            db.session.add(revision)
        db.session.flush()
        snapshot(note, force=True)
        save_attachments(note, uploads)
    db.session.commit()
    flash(f"已导入 {len(prepared)} 篇笔记。", "success")
    return redirect(url_for("home") if session.get("role") != "admin" else url_for("admin_notes"))


@app.route("/admin")
@admin_required
def admin():
    current = Note.query.filter(Note.deleted_at.is_(None))
    return render_template("admin.html", count=current.count(), user_count=User.query.count(), notes=current.order_by(Note.create_time.desc()).limit(5).all())


@app.route("/admin/notes")
@admin_required
def admin_notes():
    return render_template("admin_notes.html", notes=filtered_notes(all_users=True).all())


@app.route("/admin/note/<int:id>")
@admin_required
def admin_note_detail(id):
    return redirect(url_for("note_detail", id=id))


@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def admin_edit(id):
    return edit(id)


@app.post("/admin/delete/<int:id>")
@admin_required
def admin_delete(id):
    return delete(id)


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(413)
def error_page(error):
    return render_template("error.html", code=error.code, message=error.description), error.code


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
