import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

import requests as http_requests
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from ldap3 import Server, Connection, ALL, SUBTREE
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False

try:
    import oidc as oidc_helper
    OIDC_AVAILABLE = True
except ImportError:
    OIDC_AVAILABLE = False

from bookshelf import BookshelfClient
from readarr import ReadarrClient, _name_match, _norm_name
from lazylibrarian import LazyLibrarianClient

app = Flask(__name__)

# Honor X-Forwarded-* headers from a reverse proxy (haproxy, nginx, traefik, etc.)
# so url_for(..., _external=True) generates correct https URLs. Required for the
# OIDC redirect_uri to match what's registered at the IdP when the app sits
# behind a proxy. No-op when no proxy is in front (headers absent).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


def _load_or_create_secret_key():
    """Load secret key from env, or persist one to data/secret_key."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(os.path.dirname(__file__), "data", "secret_key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    key = os.urandom(32).hex()
    with open(key_file, "w") as f:
        f.write(key)
    return key


app.secret_key = _load_or_create_secret_key()

# Configure logging to stdout so it shows in docker logs
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
app.logger.setLevel(logging.DEBUG)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "config.json")
REQUESTS_FILE = os.path.join(os.path.dirname(__file__), "data", "requests.json")
USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "users.json")

# In-memory state
config = {"ebook": {}, "audiobook": {}, "ldap": {}, "oidc": {}}
requests_history = []
users = []
lock = threading.Lock()

# ─── Flask-Login Setup ───

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User:
    """Flask-Login user wrapper."""

    def __init__(self, data):
        self._data = data

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def username(self):
        return self._data["username"]

    @property
    def role(self):
        return self._data.get("role", "user")

    def get_id(self):
        return self.username


@login_manager.user_loader
def load_user(username):
    for u in users:
        if u["username"] == username:
            return User(u)
    return None


@login_manager.unauthorized_handler
def handle_unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required"}), 401
    return redirect(url_for("login"))


def admin_required(f):
    """Decorator: require admin role."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ─── Data Persistence ───

def ensure_data_dir():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)


def save_config():
    ensure_data_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass


def save_requests():
    ensure_data_dir()
    with open(REQUESTS_FILE, "w") as f:
        json.dump(requests_history, f, indent=2, default=str)


def load_requests():
    global requests_history
    if os.path.exists(REQUESTS_FILE):
        try:
            with open(REQUESTS_FILE) as f:
                requests_history = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass


def save_users():
    ensure_data_dir()
    # Strip password_hash before logging
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_users():
    global users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                users = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass


def init_default_admin():
    """Create a default admin account if no users exist."""
    if not users:
        users.append({
            "username": "admin",
            "password_hash": generate_password_hash("admin"),
            "role": "admin",
            "created_at": datetime.utcnow().isoformat(),
        })
        save_users()
        app.logger.warning(
            "Default admin account created (username: admin, password: admin). "
            "Please change the password immediately!"
        )


load_config()
load_requests()
load_users()
init_default_admin()

# ─── Background request reconciler (M36) ───
# Statuses used to update only when the UI POSTed /api/requests/refresh, so the
# dashboard silently rotted whenever nobody had the page open. One worker (the
# fcntl-lock winner — gunicorn runs several) reconciles every RECONCILE_INTERVAL
# seconds; other workers see the result via the on-request reload_state().

RECONCILE_INTERVAL = int(os.environ.get("RECONCILE_INTERVAL", "900"))
_reconciler_lock_fd = None  # keeps the fcntl lock alive for the process lifetime


def _reconciler_loop():
    while True:
        time.sleep(RECONCILE_INTERVAL)
        try:
            with lock:
                load_requests()
                _reconcile_requests()
            app.logger.info("Background reconcile pass complete")
        except Exception:
            app.logger.exception("Background reconcile pass failed")


def _start_reconciler():
    global _reconciler_lock_fd
    if RECONCILE_INTERVAL <= 0:
        return
    import fcntl
    lock_path = os.path.join(os.path.dirname(REQUESTS_FILE), ".reconciler.lock")
    try:
        fd = open(lock_path, "w")
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker owns the reconciler
    _reconciler_lock_fd = fd
    threading.Thread(target=_reconciler_loop, daemon=True, name="reconciler").start()
    app.logger.info("Background request reconciler started (interval %ss)", RECONCILE_INTERVAL)


_start_reconciler()

if OIDC_AVAILABLE:
    oidc_helper.init_oidc(app, config)


@app.before_request
def reload_state():
    """Reload shared state from disk so multiple Gunicorn workers stay in sync."""
    load_config()
    load_requests()
    load_users()
    # Re-init the OIDC client if config changed in another worker. init_oidc
    # is idempotent — registers/unregisters the client based on enabled flag.
    if OIDC_AVAILABLE and not app.extensions.get("oidc_client") and config.get("oidc", {}).get("enabled"):
        oidc_helper.init_oidc(app, config)


# ─── LDAP Auth ───

def _get_ldap_defaults():
    return {
        "enabled": False,
        "server_url": "",
        "bind_dn": "",
        "bind_password": "",
        "base_dn": "",
        "user_search_filter": "(sAMAccountName={username})",
        "default_role": "user",
    }


def try_ldap_auth(username, password):
    """Attempt LDAP bind authentication.

    Returns (success: bool, user_dn: str, error: str).
    """
    if not LDAP3_AVAILABLE:
        return False, "", "ldap3 library is not installed"

    ldap = config.get("ldap", {})
    if not ldap.get("enabled"):
        return False, "", "LDAP is not enabled"

    server_url = ldap.get("server_url", "")
    bind_dn = ldap.get("bind_dn", "")
    bind_password = ldap.get("bind_password", "")
    base_dn = ldap.get("base_dn", "")
    search_filter = ldap.get("user_search_filter", "(sAMAccountName={username})")

    if not server_url or not base_dn:
        return False, "", "LDAP server_url or base_dn not configured"

    search_filter = search_filter.replace("{username}", username)

    try:
        server = Server(server_url, get_info=ALL)
        conn = Connection(server, bind_dn, bind_password, auto_bind=True)
        conn.search(base_dn, search_filter, search_scope=SUBTREE)
        if not conn.entries:
            conn.unbind()
            return False, "", "User not found in LDAP directory"
        user_dn = conn.entries[0].entry_dn
        conn.unbind()

        # Attempt to bind as the user to verify their password
        user_conn = Connection(server, user_dn, password, auto_bind=True)
        user_conn.unbind()
        return True, user_dn, ""
    except Exception as e:
        return False, "", str(e)


def get_client(server_type: str) -> ReadarrClient | BookshelfClient | LazyLibrarianClient | None:
    """Get a client for the given server type based on server_software setting."""
    server = config.get(server_type, {})
    if server.get("url") and server.get("api_key"):
        if server.get("server_software") == "bookshelf":
            return BookshelfClient(server["url"], server["api_key"])
        if server.get("server_software") == "lazylibrarian":
            return LazyLibrarianClient(server["url"], server["api_key"])
        return ReadarrClient(server["url"], server["api_key"])
    return None


# ─── Pages ───

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("login.html")


# ─── Auth API ───

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    for u in users:
        if u["username"] == username and check_password_hash(u["password_hash"], password):
            login_user(User(u))
            return jsonify({"success": True, "username": u["username"], "role": u.get("role", "user")})

    # Fall through to LDAP if configured
    ldap = config.get("ldap", {})
    if ldap.get("enabled"):
        app.logger.info("LDAP enabled, attempting auth for '%s'", username)
        success, _user_dn, error = try_ldap_auth(username, password)
        app.logger.info("LDAP result: success=%s, dn=%s, error=%s", success, _user_dn, error)
        if success:
            existing = next((u for u in users if u["username"] == username), None)
            if not existing:
                existing = {
                    "username": username,
                    "password_hash": "ldap",
                    "role": ldap.get("default_role", "user"),
                    "created_at": datetime.utcnow().isoformat(),
                }
                users.append(existing)
                save_users()
            app.logger.info("About to call login_user for '%s'", username)
            ok = login_user(User(existing))
            app.logger.info("login_user returned %s for '%s'", ok, username)
            return jsonify({"success": True, "username": existing["username"], "role": existing.get("role", "user")})
        app.logger.info("LDAP auth failed for '%s': %s", username, error)

    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
@login_required
def api_me():
    return jsonify({
        "username": current_user.username,
        "role": current_user.role,
    })


# ─── User Management API ───

@app.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    safe_users = []
    for u in users:
        safe_users.append({
            "username": u["username"],
            "role": u.get("role", "user"),
            "created_at": u.get("created_at", ""),
        })
    return jsonify(safe_users)


@app.route("/api/users", methods=["POST"])
@admin_required
def create_user():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if role not in ("admin", "user"):
        return jsonify({"error": "Role must be 'admin' or 'user'"}), 400

    for u in users:
        if u["username"] == username:
            return jsonify({"error": "Username already exists"}), 400

    new_user = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
    }
    users.append(new_user)
    save_users()
    return jsonify({"success": True, "username": username, "role": role}), 201


@app.route("/api/users/<username>", methods=["PUT"])
@admin_required
def update_user(username):
    data = request.json

    target = None
    for u in users:
        if u["username"] == username:
            target = u
            break

    if not target:
        return jsonify({"error": "User not found"}), 404

    if "password" in data and data["password"]:
        target["password_hash"] = generate_password_hash(data["password"])

    if "role" in data:
        if data["role"] not in ("admin", "user"):
            return jsonify({"error": "Role must be 'admin' or 'user'"}), 400
        target["role"] = data["role"]

    save_users()
    return jsonify({"success": True, "username": target["username"], "role": target.get("role", "user")})


@app.route("/api/users/<username>", methods=["DELETE"])
@admin_required
def delete_user(username):
    if username == current_user.username:
        return jsonify({"error": "Cannot delete your own account"}), 400

    global users
    original_len = len(users)
    users = [u for u in users if u["username"] != username]

    if len(users) == original_len:
        return jsonify({"error": "User not found"}), 404

    save_users()
    return jsonify({"success": True})


# ─── LDAP Config API ───

@app.route("/api/ldap", methods=["GET"])
@admin_required
def get_ldap():
    ldap = config.get("ldap", _get_ldap_defaults())
    return jsonify({
        "enabled": ldap.get("enabled", False),
        "server_url": ldap.get("server_url", ""),
        "bind_dn": ldap.get("bind_dn", ""),
        "bind_password": ldap.get("bind_password", ""),
        "base_dn": ldap.get("base_dn", ""),
        "user_search_filter": ldap.get("user_search_filter", "(sAMAccountName={username})"),
        "default_role": ldap.get("default_role", "user"),
    })


@app.route("/api/ldap", methods=["POST"])
@admin_required
def update_ldap():
    data = request.json
    if data.get("default_role") not in ("admin", "user"):
        return jsonify({"error": "Role must be 'admin' or 'user'"}), 400
    config["ldap"] = {
        "enabled": bool(data.get("enabled")),
        "server_url": data.get("server_url", "").strip(),
        "bind_dn": data.get("bind_dn", "").strip(),
        "bind_password": data.get("bind_password", ""),
        "base_dn": data.get("base_dn", "").strip(),
        "user_search_filter": data.get("user_search_filter", "").strip() or "(sAMAccountName={username})",
        "default_role": data.get("default_role", "user"),
    }
    save_config()
    return jsonify({"success": True})


@app.route("/api/ldap/test", methods=["POST"])
@admin_required
def test_ldap():
    if not LDAP3_AVAILABLE:
        return jsonify({"error": "ldap3 library is not installed"}), 400
    data = request.json
    server_url = data.get("server_url", "").strip()
    bind_dn = data.get("bind_dn", "").strip()
    bind_password = data.get("bind_password", "")
    base_dn = data.get("base_dn", "").strip()
    search_filter = data.get("user_search_filter", "").strip() or "(sAMAccountName={username})"

    if not server_url or not base_dn:
        return jsonify({"error": "server_url and base_dn are required"}), 400

    try:
        server = Server(server_url, get_info=ALL)
        conn = Connection(server, bind_dn, bind_password, auto_bind=True)
        test_filter = search_filter.replace("{username}", "test")
        conn.search(base_dn, test_filter, search_scope=SUBTREE, size_limit=1)
        conn.unbind()
        return jsonify({"success": True, "message": "Connected to LDAP server successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─── OIDC Config API ───

@app.route("/api/oidc", methods=["GET"])
@admin_required
def get_oidc():
    if not OIDC_AVAILABLE:
        return jsonify({
            "available": False,
            "enabled": False, "display_name": "OIDC", "issuer_url": "",
            "client_id": "", "client_secret": "", "scope": "openid profile email",
            "username_claim": "preferred_username", "default_role": "user",
            "auto_create_users": False, "auto_redirect": False,
        })
    defaults = oidc_helper.get_oidc_defaults()
    oidc = config.get("oidc", defaults)
    return jsonify({
        "available": True,
        "enabled": oidc.get("enabled", False),
        "display_name": oidc.get("display_name", defaults["display_name"]),
        "issuer_url": oidc.get("issuer_url", ""),
        "client_id": oidc.get("client_id", ""),
        "client_secret": oidc.get("client_secret", ""),
        "scope": oidc.get("scope", defaults["scope"]),
        "username_claim": oidc.get("username_claim", defaults["username_claim"]),
        "default_role": oidc.get("default_role", "user"),
        "auto_create_users": oidc.get("auto_create_users", False),
        "auto_redirect": oidc.get("auto_redirect", False),
    })


@app.route("/api/oidc", methods=["POST"])
@admin_required
def update_oidc():
    if not OIDC_AVAILABLE:
        return jsonify({"error": "authlib library is not installed"}), 400
    data = request.json
    if data.get("default_role") not in ("admin", "user"):
        return jsonify({"error": "Role must be 'admin' or 'user'"}), 400
    config["oidc"] = {
        "enabled": bool(data.get("enabled")),
        "display_name": data.get("display_name", "").strip() or "OIDC",
        "issuer_url": data.get("issuer_url", "").strip(),
        "client_id": data.get("client_id", "").strip(),
        "client_secret": data.get("client_secret", ""),
        "scope": data.get("scope", "").strip() or "openid profile email",
        "username_claim": data.get("username_claim", "").strip() or "preferred_username",
        "default_role": data.get("default_role", "user"),
        "auto_create_users": bool(data.get("auto_create_users")),
        "auto_redirect": bool(data.get("auto_redirect")),
    }
    save_config()
    # Re-register the OAuth client so the new config takes effect immediately.
    oidc_helper.init_oidc(app, config)
    return jsonify({"success": True})


@app.route("/api/oidc/test", methods=["POST"])
@admin_required
def test_oidc():
    if not OIDC_AVAILABLE:
        return jsonify({"error": "authlib library is not installed"}), 400
    data = request.json
    issuer_url = data.get("issuer_url", "").strip()
    if not issuer_url:
        return jsonify({"error": "issuer_url is required"}), 400
    try:
        doc = oidc_helper.fetch_discovery(issuer_url)
        ok, msg = oidc_helper.validate_discovery(doc)
        if not ok:
            return jsonify({"error": msg}), 400
        return jsonify({
            "success": True,
            "message": f"Discovery OK. Issuer: {doc.get('issuer', '')}",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─── OIDC Auth Flow ───

@app.route("/api/auth/oidc/login")
def oidc_login():
    """Initiates the OIDC redirect to the IdP."""
    if not OIDC_AVAILABLE or not config.get("oidc", {}).get("enabled"):
        return redirect(url_for("login"))
    client = oidc_helper.get_client(app)
    if client is None:
        # Configured but client failed to init (bad issuer, etc.) — fall back.
        return redirect(url_for("login"))
    redirect_uri = url_for("oidc_callback", _external=True)
    return client.authorize_redirect(redirect_uri)


@app.route("/api/auth/oidc/callback")
def oidc_callback():
    """Handles the redirect back from the IdP, exchanges code for tokens,
    finds or provisions the user, logs them in."""
    oidc_cfg = config.get("oidc", {})
    if not OIDC_AVAILABLE or not oidc_cfg.get("enabled"):
        return redirect(url_for("login"))
    client = oidc_helper.get_client(app)
    if client is None:
        return redirect(url_for("login") + "?error=oidc_not_initialized")
    try:
        token = client.authorize_access_token()
    except Exception as e:
        app.logger.warning("OIDC token exchange failed: %s", e)
        return redirect(url_for("login") + "?error=oidc_token_exchange_failed")

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = client.userinfo(token=token)
        except Exception as e:
            app.logger.warning("OIDC userinfo fetch failed: %s", e)
            return redirect(url_for("login") + "?error=oidc_userinfo_failed")

    username = oidc_helper.extract_username(userinfo, oidc_cfg.get("username_claim", "preferred_username"))
    if not username:
        app.logger.warning("OIDC token contains no usable username claim: %s", userinfo)
        return redirect(url_for("login") + "?error=oidc_no_username")

    existing = next((u for u in users if u["username"] == username), None)
    if not existing:
        if not oidc_cfg.get("auto_create_users"):
            app.logger.info("OIDC login rejected for '%s' — user does not exist and auto_create_users is off", username)
            return redirect(url_for("login") + "?error=account_not_found")
        existing = {
            "username": username,
            "password_hash": "oidc",
            "role": oidc_cfg.get("default_role", "user"),
            "auth_source": "oidc",
            "created_at": datetime.utcnow().isoformat(),
        }
        users.append(existing)
        save_users()
        app.logger.info("Auto-provisioned OIDC user '%s'", username)

    login_user(User(existing))
    return redirect(url_for("index"))


# ─── Auth provider discovery (for login page UI) ───

@app.route("/api/auth/providers", methods=["GET"])
def auth_providers():
    """Tells the login page which alt providers (beyond local username/password)
    are enabled, so it can render the appropriate buttons. Public — no auth
    required, since the login page is itself public."""
    oidc_cfg = config.get("oidc") or {}
    return jsonify({
        "oidc": {
            "enabled": bool(OIDC_AVAILABLE and oidc_cfg.get("enabled")),
            "display_name": oidc_cfg.get("display_name") or "OIDC",
            "auto_redirect": bool(oidc_cfg.get("auto_redirect")),
        },
    })


# ─── Config API ───

@app.route("/api/config", methods=["GET"])
@login_required
def get_config():
    return jsonify({
        "ebook": {
            "url": config["ebook"].get("url", ""),
            "api_key": config["ebook"].get("api_key", ""),
            "server_software": config["ebook"].get("server_software", "readarr"),
            "configured": bool(config["ebook"].get("url") and config["ebook"].get("api_key")),
        },
        "audiobook": {
            "url": config["audiobook"].get("url", ""),
            "api_key": config["audiobook"].get("api_key", ""),
            "server_software": config["audiobook"].get("server_software", "readarr"),
            "configured": bool(config["audiobook"].get("url") and config["audiobook"].get("api_key")),
        },
    })


@app.route("/api/config", methods=["POST"])
@admin_required
def update_config():
    data = request.json
    server_type = data.get("server_type")
    if server_type not in ("ebook", "audiobook"):
        return jsonify({"error": "server_type must be 'ebook' or 'audiobook'"}), 400

    config[server_type] = {
        "url": data.get("url", "").strip(),
        "api_key": data.get("api_key", "").strip(),
        "server_software": data.get("server_software", "readarr"),
    }
    save_config()
    return jsonify({"success": True})


@app.route("/api/config/test", methods=["POST"])
@admin_required
def test_config():
    data = request.json
    url = data.get("url", "").strip()
    api_key = data.get("api_key", "").strip()
    if not url or not api_key:
        return jsonify({"error": "url and api_key are required"}), 400
    try:
        server_software = data.get("server_software", "readarr")
        if server_software == "bookshelf":
            client = BookshelfClient(url, api_key)
        elif server_software == "lazylibrarian":
            client = LazyLibrarianClient(url, api_key)
        else:
            client = ReadarrClient(url, api_key)
        status = client.test_connection()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─── Search & Discovery API (Open Library) ───

def _normalize_ol_doc(doc):
    """Normalize a single Open Library search.json doc to our book schema."""
    isbns = doc.get("isbn", [])
    isbn_13 = next((i for i in isbns if len(i) == 13), "")
    isbn_10 = next((i for i in isbns if len(i) == 10), "")
    if not isbn_13 and not isbn_10 and isbns:
        isbn_13 = isbns[0]

    cover_i = doc.get("cover_i")
    cover = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else ""

    ol_key = doc.get("key", "")
    ol_id = ol_key.split("/")[-1] if ol_key else ""

    year = doc.get("first_publish_year")
    published_date = str(year) if year else ""

    return {
        "id": ol_id,
        "title": doc.get("title", "Unknown"),
        "authors": doc.get("author_name", []),
        "publishedDate": published_date,
        "description": "",
        "pageCount": doc.get("number_of_pages_median", 0),
        "categories": doc.get("subject", [])[:5] if doc.get("subject") else [],
        "isbn_13": isbn_13,
        "isbn_10": isbn_10,
        "cover": cover,
        "language": (doc.get("language", ["en"])[0]
                     if doc.get("language") else "en"),
    }


def _normalize_ol_subject_work(work):
    """Normalize a single work from Open Library /subjects/{subject}.json."""
    authors = [a.get("name", "") for a in work.get("authors", []) if a.get("name")]

    cover_id = work.get("cover_id")
    cover = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""

    ol_key = work.get("key", "")
    ol_id = ol_key.split("/")[-1] if ol_key else ""

    year = work.get("first_publish_year")
    published_date = str(year) if year else ""

    return {
        "id": ol_id,
        "title": work.get("title", "Unknown"),
        "authors": authors,
        "publishedDate": published_date,
        "description": "",
        "pageCount": 0,
        "categories": [],
        "isbn_13": "",
        "isbn_10": "",
        "cover": cover,
        "language": "en",
    }


# Open Library search.json stopped including isbn in its DEFAULT field set —
# without an explicit fields list every doc arrives isbn-less and the
# ISBN-first backend lookup (bmig-04) can never fire. Request the fields
# _normalize_ol_doc actually reads.
_OL_SEARCH_FIELDS = ("key,title,author_name,cover_i,first_publish_year,"
                     "isbn,language,number_of_pages_median,subject")

# Category keys mapped to Open Library API details
_DISCOVER_CATEGORIES = {
    "new_releases":   ("search.json",  {"sort": "new", "limit": 20, "fields": _OL_SEARCH_FIELDS}),
    "trending":       ("search.json",  {"sort": "rating", "limit": 20, "fields": _OL_SEARCH_FIELDS}),
    "best_sellers":   ("search.json",  {"q": "subject:bestsellers", "sort": "rating", "limit": 20, "fields": _OL_SEARCH_FIELDS}),
    "classics":       ("search.json",  {"q": "subject:classics", "sort": "rating", "limit": 20, "fields": _OL_SEARCH_FIELDS}),
    "fiction":        ("subjects/fiction.json",          {"limit": 20}),
    "science_fiction":("subjects/science_fiction.json",  {"limit": 20}),
    "mystery":        ("subjects/mystery.json",          {"limit": 20}),
    "fantasy":        ("subjects/fantasy.json",          {"limit": 20}),
    "romance":        ("subjects/romance.json",          {"limit": 20}),
    "nonfiction":     ("subjects/non-fiction.json",      {"limit": 20}),
    "history":        ("subjects/history.json",          {"limit": 20}),
}


@app.route("/api/discover")
@login_required
def discover_books():
    category = request.args.get("category", "").strip()
    if not category or category not in _DISCOVER_CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400
    try:
        endpoint, params = _DISCOVER_CATEGORIES[category]
        resp = http_requests.get(
            f"https://openlibrary.org/{endpoint}",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if endpoint == "search.json":
            results = [_normalize_ol_doc(doc) for doc in data.get("docs", [])]
        else:
            # /subjects/ endpoint returns a "works" array
            results = [_normalize_ol_subject_work(w) for w in data.get("works", [])]

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search")
@login_required
def search_books():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    try:
        resp = http_requests.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "limit": 20, "fields": _OL_SEARCH_FIELDS},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [_normalize_ol_doc(doc) for doc in data.get("docs", [])]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/availability")
@login_required
def check_availability():
    """Check which books are already on the configured ebook/audiobook servers."""
    result = {"ebook": {"isbns": [], "titles": []}, "audiobook": {"isbns": [], "titles": []}}

    for server_type in ("ebook", "audiobook"):
        client = get_client(server_type)
        if not client:
            continue
        try:
            books = client.get_books()
            isbns = set()
            titles = set()
            for book in books:
                title = ""
                # Readarr/Bookshelf format: editions array with isbn fields
                if isinstance(book.get("editions"), list):
                    for edition in book["editions"]:
                        for key in ("isbn13", "isbn_13"):
                            val = edition.get(key, "")
                            if val:
                                isbns.add(val)
                        for key in ("isbn10", "isbn_10"):
                            val = edition.get(key, "")
                            if val:
                                isbns.add(val)
                    # Also check top-level isbn fields
                    for key in ("isbn13", "isbn_13", "isbn10", "isbn_10"):
                        val = book.get(key, "")
                        if val:
                            isbns.add(val)
                    title = book.get("title", "")
                # LazyLibrarian format: flat dicts with bookisbn, bookname
                else:
                    isbn = book.get("bookisbn", book.get("isbn", ""))
                    if isbn:
                        isbns.add(isbn)
                    title = book.get("bookname", book.get("title", ""))
                if title:
                    titles.add(title.lower())
            result[server_type] = {
                "isbns": list(isbns),
                "titles": list(titles),
            }
        except Exception as e:
            app.logger.warning("Failed to get books from %s: %s", server_type, e)

    # Also include books with active requests (pending/processing/downloading)
    active_statuses = {"pending", "processing", "retrying", "downloading"}
    requests_by_type = {"ebook": {"isbns": set(), "titles": set()}, "audiobook": {"isbns": set(), "titles": set()}}
    with lock:
        for req in requests_history:
            if req.get("status") not in active_statuses:
                continue
            server = req.get("server_type", "")
            if server not in requests_by_type:
                continue
            isbn = req.get("isbn", "")
            if isbn:
                requests_by_type[server]["isbns"].add(isbn)
            title = req.get("title", "")
            if title:
                requests_by_type[server]["titles"].add(title.lower())

    result["ebook_requests"] = {
        "isbns": list(requests_by_type["ebook"]["isbns"]),
        "titles": list(requests_by_type["ebook"]["titles"]),
    }
    result["audiobook_requests"] = {
        "isbns": list(requests_by_type["audiobook"]["isbns"]),
        "titles": list(requests_by_type["audiobook"]["titles"]),
    }

    return jsonify(result)


@app.route("/api/profiles/<server_type>")
@login_required
def get_profiles(server_type):
    client = get_client(server_type)
    if not client:
        return jsonify({"error": f"{server_type} server not configured"}), 400
    try:
        profiles = client.get_quality_profiles()
        return jsonify(profiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rootfolders/<server_type>")
@login_required
def get_root_folders(server_type):
    client = get_client(server_type)
    if not client:
        return jsonify({"error": f"{server_type} server not configured"}), 400
    try:
        folders = client.get_root_folders()
        return jsonify(folders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Failure handling: retry classification + ntfy (fix-48 B8/B9/B10/B12) ───
# The 2026-07-18 burst showed the one-shot request model failing 13/18 requests
# with errors that were stored silently: transient Readarr timeouts became
# permanent errors, metadata no-matches were papered over by POSTing Open
# Library ids Readarr can never accept, and nothing ever told the operator.
# Now: transient failures retry via the reconciler, permanent failures error
# once and push to ntfy, and every terminal transition notifies.

NTFY_URL = os.environ.get("NTFY_URL", "http://ntfy:80")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "books")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")
MAX_ADD_RETRIES = int(os.environ.get("MAX_ADD_RETRIES", "5"))
MAX_SEARCH_ATTEMPTS = int(os.environ.get("MAX_SEARCH_ATTEMPTS", "4"))
SEARCH_RETRY_HOURS = float(os.environ.get("SEARCH_RETRY_HOURS", "6"))


class PermanentRequestError(Exception):
    """The backend definitively rejected the request; retrying cannot help."""


def _notify_failure(req, reason):
    """Push a terminal request failure to ntfy (fix-48 B12). Never raises."""
    if not NTFY_TOKEN:
        return
    try:
        http_requests.post(
            f"{NTFY_URL}/{NTFY_TOPIC}",
            data=f"{req.get('title')} by {req.get('author')}: {reason}".encode(),
            headers={
                "Authorization": f"Bearer {NTFY_TOKEN}",
                "Title": "Book request failed",
                "Tags": "books,warning",
                "Priority": "high",
            },
            timeout=10,
        )
    except Exception:
        app.logger.exception("ntfy notification failed for '%s'", req.get("title"))


def _fail_request(req, reason):
    """Mark a request terminally failed, loudly: log + ntfy."""
    req["status"] = "error"
    req["error"] = reason
    app.logger.warning("Request '%s' failed terminally: %s", req.get("title"), reason)
    _notify_failure(req, reason)


def _is_transient(exc):
    """Timeouts, connection drops and backend 5xx are worth retrying (B9/B12)."""
    if isinstance(exc, (http_requests.exceptions.Timeout,
                        http_requests.exceptions.ConnectionError)):
        return True
    resp = getattr(exc, "response", None)
    return resp is not None and resp.status_code >= 500


def _candidate_author_name(cand):
    """A lookup candidate's OWN author name (bmig-04).

    Bookshelf's /book/lookup results carry author=None; the name is
    recoverable from authorTitle, which is '<lastname, firstname(s)> <title>'
    with the author part lowercased. Returns '' when nothing trustworthy is
    recoverable — the caller must then treat the candidate as ineligible,
    never substitute the requested author.
    """
    name = (cand.get("author") or {}).get("authorName", "")
    if name:
        return name
    at = cand.get("authorTitle") or ""
    t = cand.get("title") or ""
    if t and at.lower().endswith(t.lower()):
        at = at[: len(at) - len(t)]
    at = at.strip()
    if "," in at:
        last, _, first = at.partition(",")
        at = f"{first.strip()} {last.strip()}".strip()
    return at


def _attempt_add(client, req):
    """Look up the request in the backend's metadata and add it — but only a
    candidate that is verifiably the requested book (bmig-04, C1/C4 fix).
    Returns the backend book record.

    Eligibility gates, applied to every candidate:
      * title: normalized exact or prefix match — right-author-wrong-title
        ('Hex in the City' for 'Feed') is still a wrong book. This applies to
        ISBN hits too: hardcover works carry junk edition titles (an OL isbn
        for 'Wuthering Heights' resolved to the correct work but pinned its
        Vietnamese edition "TH'inh gio hu", which then made the record
        tracker-unsearchable — the bmig-03 junk-edition class). A mismatched
        isbn edition falls through to term search.
      * author: the candidate's OWN author must token-match the requested
        author, or be a provider-documented pen name (author_alias_match).
        The requested author is NEVER stamped onto an authorless candidate —
        that was the C4 behavior that silently bound 'Pride, Prejudice, and
        Peril' (Katie Oliver) to a Jane Austen request.
    Within the eligible set the ranked retry-until-accepted walk is kept
    (junk editions still 400 on add). No eligible candidate, or every
    eligible one permanently rejected => PermanentRequestError (=> ntfy
    'books'), never add-the-next-thing. Transient transport errors propagate
    for retry classification by the caller (fix-48 B9/B12).

    Also still raises PermanentRequestError when the provider has no match at
    all (fix-48 B8): an Open Library id must never reach POST /book.
    """
    title = req["title"]
    author_name = req.get("author") or "Unknown"
    isbn = req.get("isbn", "")

    # Library first: the canonical record may already exist (auto-added with
    # the author's bibliography) while the metadata lookup returns only junk
    # editions that 400 on add — The Return of the King failed exactly this
    # way. Adoption monitors + searches the existing record, no POST needed.
    # (Since bmig-04, adoption itself is author-gated in the client.)
    adopt = getattr(client, "adopt_library_book", None)
    if adopt:
        existing = adopt(title, author_name)
        if existing:
            return existing

    import re as _re
    _want = _re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    want_author = author_name if author_name and author_name != "Unknown" else ""

    # rreading-glasses frequently ranks junk user-uploaded editions above the
    # canonical work. Taking [0] blindly caused both 400s at request time and
    # stuck-forever books. Rank so the canonical edition wins, then try the
    # eligible candidates in order until the backend actually accepts one.
    #   -- local patch (libreseerr-diagnosis 2026-07-12); re-derive on
    #      image bump. Upstream selects readarr_books[0] unconditionally.
    def _cand_score(b):
        _t = b.get("title") or ""
        _norm = _re.sub(r"[^a-z0-9]+", " ", _t.lower()).strip()
        _votes = (b.get("ratings") or {}).get("votes") or 0
        _exact = 1 if _norm == _want else 0
        _prefix = 1 if (_want and (_norm.startswith(_want) or _want.startswith(_norm))) else 0
        _allcaps = 1 if (_t and _t.upper() == _t and any(c.isalpha() for c in _t)) else 0
        _byauthor = 1 if " by " in _t.lower() else 0
        return (_exact, _prefix, -_allcaps, -_byauthor, _votes)

    _alias_verdict = {}

    def _author_ok(cand_author):
        if not want_author:
            return True
        if _name_match(want_author, cand_author):
            return True
        key = _norm_name(cand_author)
        if key not in _alias_verdict:
            fn = getattr(client, "author_alias_match", None)
            _alias_verdict[key] = bool(fn and fn(want_author, cand_author))
        return _alias_verdict[key]

    def _phases():
        # ISBN-first (bmig-04): an isbn identifies one exact edition; when
        # the OL doc carries one it beats any term ranking. Term search stays
        # as the fallback — including when the isbn's candidates all fail the
        # gates or the backend rejects them.
        if isbn:
            try:
                hits = client.lookup_by_isbn(isbn)
            except Exception as e:
                if _is_transient(e):
                    raise
                app.logger.warning(
                    "ISBN lookup '%s' failed for '%s': %s — term fallback",
                    isbn, title, e,
                )
                hits = []
            for c in hits:
                c["_isbn_hit"] = True
            if hits:
                yield hits
        hits = client.search_books(f"{title} {author_name}")
        if not hits:
            # Broader net before giving up — author qualifiers sometimes sink
            # an otherwise-present work in the lookup.
            hits = client.search_books(title)
        if hits:
            yield hits

    rejected = []
    last_err = None
    saw_transient = False
    found_any = False
    tried_any = False
    for phase_hits in _phases():
        found_any = True
        for _cand in sorted(phase_hits, key=_cand_score, reverse=True):
            _ct = _cand.get("title") or ""
            _cn = _re.sub(r"[^a-z0-9]+", " ", _ct.lower()).strip()
            if not (_cn == _want or _cn.startswith(_want + " ")
                    or _want.startswith(_cn + " ")):
                rejected.append(f"'{_ct}': title mismatch")
                continue
            cand_author = _candidate_author_name(_cand)
            if not cand_author:
                rejected.append(f"'{_ct}': candidate has no author")
                continue
            if not _author_ok(cand_author):
                rejected.append(f"'{_ct}' by {cand_author}: author mismatch")
                continue
            if not (_cand.get("author") or {}).get("foreignAuthorId"):
                # Bind the candidate to its OWN full author record (POST
                # /book needs foreignAuthorId + the author object) — looked
                # up, never synthesized.
                resolver = getattr(client, "resolve_author", None)
                resolved = resolver(cand_author) if resolver else None
                if not resolved:
                    rejected.append(f"'{_ct}' by {cand_author}: author unresolvable")
                    continue
                _cand["author"] = resolved
            tried_any = True
            app.logger.info(
                "Trying candidate for '%s': title='%s', author='%s' (%s)",
                title, _ct, (_cand.get("author") or {}).get("authorName"),
                "isbn" if _cand.get("_isbn_hit") else "term",
            )
            try:
                return client.add_book(_cand, req["quality_profile_id"], req["root_folder"])
            except Exception as _e:
                last_err = _e
                saw_transient = saw_transient or _is_transient(_e)
                app.logger.warning(
                    "Backend rejected candidate for '%s' (title='%s'): %s; trying next",
                    title, _ct, str(_e)[:200],
                )
    if saw_transient:
        raise last_err  # retryable — let the caller classify
    if not found_any:
        raise PermanentRequestError(
            f"'{title}' by {author_name} was not found in the backend metadata "
            "provider (Hardcover) — it cannot be added automatically"
        )
    if not tried_any:
        detail = "; ".join(rejected[:6]) or "no candidates"
        raise PermanentRequestError(
            f"No eligible metadata candidate for '{title}' by {author_name} — "
            f"refusing to add a different book (author gate). Rejected: {detail}"
        )
    raise PermanentRequestError(
        f"Backend rejected every eligible candidate for '{title}': {last_err}"
    )


# ─── Download / Request API ───

@app.route("/api/request", methods=["POST"])
@login_required
def create_request():
    data = request.json
    server_type = data.get("server_type")
    book_data = data.get("book")
    quality_profile_id = data.get("quality_profile_id")
    root_folder = data.get("root_folder")

    if not all([server_type, book_data, quality_profile_id, root_folder]):
        return jsonify({"error": "Missing required fields"}), 400

    client = get_client(server_type)
    if not client:
        return jsonify({"error": f"{server_type} server not configured"}), 400

    title = book_data.get("title", "Unknown")
    authors = book_data.get("authors", [])
    author_name = authors[0] if authors else "Unknown"
    cover_url = book_data.get("cover", "")
    isbn = book_data.get("isbn_13") or book_data.get("isbn_10", "")

    request_entry = {
        "id": int(time.time() * 1000),
        "title": title,
        "author": author_name,
        "cover_url": cover_url,
        "server_type": server_type,
        "quality_profile_id": quality_profile_id,
        # Stored so the reconciler can re-attempt the add (fix-48 B12).
        "root_folder": root_folder,
        "isbn": isbn,
        "status": "processing",
        "progress": 0,
        "retry_count": 0,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        result = _attempt_add(client, request_entry)
        request_entry["readarr_book_id"] = result.get("id")
    except PermanentRequestError as e:
        _fail_request(request_entry, str(e))
    except Exception as e:
        # Never store an error silently (fix-48 B9 — 3 of 4 timeout failures
        # left no log line at all).
        app.logger.exception("Request '%s' add attempt failed", title)
        if _is_transient(e):
            request_entry["status"] = "retrying"
            request_entry["retry_count"] = 1
            request_entry["error"] = (
                f"{e} — transient, will retry automatically "
                f"(1/{MAX_ADD_RETRIES})"
            )
        else:
            _fail_request(request_entry, str(e))

    with lock:
        requests_history.insert(0, request_entry)
        save_requests()

    return jsonify(request_entry)


@app.route("/api/requests", methods=["GET"])
@login_required
def get_requests():
    with lock:
        return jsonify(requests_history)


def _reconcile_requests():
    """Reconcile stored request statuses against the backend. Caller holds lock.

    Beyond queue/import progress this detects two rot states the 2026-07-16
    audit found sitting silently for days (findings H15/M36): a request whose
    backend book record no longer exists (dangling), and a request whose book
    is unmonitored with no file (nothing will ever search for it — dead).
    """
    for req in requests_history:
        if req["status"] in ("completed", "error"):
            continue
        client = get_client(req["server_type"])
        if not client:
            continue

        # Transient add failures re-attempt here (fix-48 B12) instead of the
        # old one-shot model where a momentary Readarr timeout permanently
        # errored a request that would have succeeded seconds later.
        if req["status"] == "retrying":
            retries = req.get("retry_count", 0)
            if "root_folder" not in req:
                _fail_request(req, f"Cannot retry (pre-fix-48 request without stored payload): {req.get('error')}")
                continue
            try:
                result = _attempt_add(client, req)
                req["readarr_book_id"] = result.get("id")
                req["status"] = "processing"
                req["error"] = None
                app.logger.info("Retry succeeded for request '%s'", req.get("title"))
            except PermanentRequestError as e:
                _fail_request(req, str(e))
            except Exception as e:
                app.logger.exception("Retry failed for request '%s'", req.get("title"))
                if retries + 1 >= MAX_ADD_RETRIES:
                    _fail_request(req, f"Gave up after {MAX_ADD_RETRIES} attempts: {e}")
                else:
                    req["retry_count"] = retries + 1
                    req["error"] = (
                        f"{e} — transient, will retry automatically "
                        f"({retries + 1}/{MAX_ADD_RETRIES})"
                    )
            continue

        try:
            queue = client.get_queue()
            req_book_id = req.get("readarr_book_id")
            matching = [
                q for q in queue
                if q.get("title", "").lower() == req["title"].lower()
                or (req_book_id and str(q.get("bookId")) == str(req_book_id))
            ]
            if matching:
                q = matching[0]
                status = q.get("status", "").lower()
                size = q.get("size", 0)
                size_left = q.get("sizeleft", 0)
                # Book is in the download queue
                req["status"] = "downloading"
                if size > 0:
                    req["progress"] = round((1 - size_left / size) * 100)
                if status == "completed":
                    req["status"] = "completed"
                    req["progress"] = 100
                elif status in ("failed", "warning"):
                    req["status"] = "error"
                    req["error"] = q.get("errorMessage", "Download failed")
            elif req_book_id:
                book = client.get_book_status(req_book_id)
                if book is None:
                    # get_book_status returns None only on a definitive 404
                    _fail_request(req, (
                        "Backend book record no longer exists (dangling request) "
                        "— re-request the title"
                    ))
                elif (book.get("statistics") or {}).get("bookFileCount", 0) > 0:
                    req["status"] = "completed"
                    req["progress"] = 100
                elif not book.get("monitored"):
                    _fail_request(req, (
                        "Book is unmonitored in the backend with no file — "
                        "nothing will ever search for it. Monitor it or re-request."
                    ))
                else:
                    # Monitored, no file, not in the queue: the one-shot add-time
                    # search found nothing and NOTHING re-triggered it — requests
                    # sat "processing" forever (fix-48 B10: The Rotten Romans,
                    # 6 days). Re-search with spacing, then fail loudly.
                    attempts = req.get("search_attempts", 1)
                    last = req.get("last_search_at") or req.get("created_at") or ""
                    try:
                        due = (datetime.utcnow() - datetime.fromisoformat(last)
                               >= timedelta(hours=SEARCH_RETRY_HOURS))
                    except (TypeError, ValueError):
                        due = True
                    if not due:
                        pass
                    elif attempts >= MAX_SEARCH_ATTEMPTS:
                        _fail_request(req, (
                            f"No download source found after {attempts} searches "
                            f"over {SEARCH_RETRY_HOURS * (attempts - 1):.0f}+ hours — giving up"
                        ))
                    elif getattr(client, "trigger_search", None):
                        client.trigger_search(req_book_id)
                        req["search_attempts"] = attempts + 1
                        req["last_search_at"] = datetime.utcnow().isoformat()
                        app.logger.info(
                            "Request '%s': re-triggered search %d/%d for book id=%s",
                            req.get("title"), attempts + 1, MAX_SEARCH_ATTEMPTS, req_book_id,
                        )
        except Exception:
            # Keep current status, but never swallow silently (M36)
            app.logger.exception(
                "Reconcile failed for request '%s' — keeping stored status",
                req.get("title"),
            )
    save_requests()


@app.route("/api/requests/refresh", methods=["POST"])
@login_required
def refresh_requests():
    """Refresh the status of all processing/downloading requests."""
    with lock:
        _reconcile_requests()
    return jsonify(requests_history)


@app.route("/api/requests/<int:request_id>", methods=["DELETE"])
@login_required
def delete_request(request_id):
    with lock:
        global requests_history
        requests_history = [r for r in requests_history if r["id"] != request_id]
        save_requests()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
