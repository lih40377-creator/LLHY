from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default="", nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, nullable=True)
    tags = db.Column(db.String(500), default="", nullable=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=True)
    is_draft = db.Column(db.Boolean, default=False, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    revisions = db.relationship("NoteRevision", back_populates="note", cascade="all, delete-orphan", order_by="NoteRevision.saved_at.desc()")
    attachments = db.relationship("NoteAttachment", back_populates="note", cascade="all, delete-orphan", order_by="NoteAttachment.created_at.desc()")

    @property
    def tag_list(self):
        return [tag.strip() for tag in (self.tags or "").split(",") if tag.strip()]


class NoteRevision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("note.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default="", nullable=False)
    tags = db.Column(db.String(500), default="", nullable=True)
    saved_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    note = db.relationship("Note", back_populates="revisions")


class NoteAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("note.id"), nullable=False, index=True)
    stored_name = db.Column(db.String(80), unique=True, nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(80), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    note = db.relationship("Note", back_populates="attachments")
