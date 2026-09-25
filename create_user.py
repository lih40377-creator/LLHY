"""Create or promote an admin account without embedding credentials in source."""
from getpass import getpass

from werkzeug.security import generate_password_hash

from app import app
from models import User, db


def main():
    username = input("管理员用户名: ").strip()
    password = getpass("密码（至少 8 个字符）: ")
    if not 3 <= len(username) <= 50 or len(password) < 8:
        raise SystemExit("用户名需 3–50 字，密码至少 8 字。")
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username)
            db.session.add(user)
        user.password = generate_password_hash(password)
        user.role = "admin"
        db.session.commit()
    print("管理员账号已保存。")


if __name__ == "__main__":
    main()
