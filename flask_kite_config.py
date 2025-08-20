from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, flash
import configparser
import os
import glob

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this!
INI_FILE = r'kite_options_sell.ini'

# --- Simple Auth ---
USERNAME = 'xxxxx'
PASSWORD = 'xxxxxxxx'  # Change this!

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# --- Config helpers ---
def load_config():
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(INI_FILE)
    return config

def save_config(config):
    with open(INI_FILE, 'w') as configfile:
        config.write(configfile)

def get_user_sections(config):
    return [s for s in config.sections() if s.startswith('user-')]

# --- HTML Templates (Bootstrap styled, edit only) ---
TEMPLATE_INDEX = """
<!doctype html>
<html lang="en">
<head>
  <title>Kite Config Editor</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-4">
  <h2 class="mb-4">Kite Config Editor</h2>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert alert-warning">
        {% for msg in messages %}<div>{{msg}}</div>{% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  <p><a href="{{ url_for('logout') }}" class="btn btn-secondary btn-sm">Logout</a></p>
  <ul class="list-group">
    <li class="list-group-item"><a href="{{ url_for('show_info') }}">Edit [info]</a></li>
    <li class="list-group-item"><a href="{{ url_for('show_realtime') }}">Edit [realtime]</a></li>
    <li class="list-group-item"><a href="{{ url_for('list_users_html') }}">Edit Users</a></li>
  </ul>
  <form action="{{ url_for('show_log') }}" method="get" class="mt-3">
    <button type="submit" class="btn btn-info">Show Latest Log File</button>
  </form>
</div>
</body>
</html>
"""

TEMPLATE_SECTION = """
<!doctype html>
<html lang="en">
<head>
  <title>Edit Section</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-4">
  <h2>Edit Section [{{ section }}]</h2>
  <form method="post">
    <table class="table table-bordered bg-white">
      <thead>
        <tr><th>Key</th><th>Value</th></tr>
      </thead>
      <tbody>
      {% for k, v in data.items() %}
      <tr>
        <td><input type="text" class="form-control" name="key_{{loop.index0}}" value="{{k}}" readonly></td>
        <td><input type="text" class="form-control" name="val_{{loop.index0}}" value="{{v}}"></td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    <input type="hidden" name="total" value="{{data|length}}">
    <button type="submit" name="save" value="1" class="btn btn-primary">Save Changes</button>
    <a href="{{ url_for('index') }}" class="btn btn-secondary">Back</a>
  </form>
</div>
</body>
</html>
"""

TEMPLATE_USERS = """
<!doctype html>
<html lang="en">
<head>
  <title>Edit Users</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-4">
  <h2>User Sections</h2>
  <ul class="list-group mb-3">
    {% for section in users %}
      <li class="list-group-item d-flex justify-content-between align-items-center">
        <a href="{{ url_for('edit_user', username=section[5:]) }}">{{ section }}</a>
      </li>
    {% endfor %}
  </ul>
  <a href="{{ url_for('index') }}" class="btn btn-secondary">Back</a>
</div>
</body>
</html>
"""

TEMPLATE_EDIT_USER = """
<!doctype html>
<html lang="en">
<head>
  <title>Edit User</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-4">
  <h2>Edit User [user-{{ username }}]</h2>
  <form method="post">
    <table class="table table-bordered bg-white">
      <thead>
        <tr><th>Key</th><th>Value</th></tr>
      </thead>
      <tbody>
      {% for k, v in data.items() %}
      <tr>
        <td><input type="text" class="form-control" name="key_{{loop.index0}}" value="{{k}}" readonly></td>
        <td><input type="text" class="form-control" name="val_{{loop.index0}}" value="{{v}}"></td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    <input type="hidden" name="total" value="{{data|length}}">
    <button type="submit" name="save" value="1" class="btn btn-primary">Save Changes</button>
    <a href="{{ url_for('list_users_html') }}" class="btn btn-secondary">Back</a>
  </form>
</div>
</body>
</html>
"""

TEMPLATE_LOGIN = """
<!doctype html>
<html lang="en">
<head>
  <title>Login</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-5" style="max-width:400px;">
  <h2 class="mb-4">Login</h2>
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Username:</label>
      <input type="text" class="form-control" name="username">
    </div>
    <div class="mb-3">
      <label class="form-label">Password:</label>
      <input type="password" class="form-control" name="password">
    </div>
    <button type="submit" class="btn btn-primary">Login</button>
  </form>
</div>
</body>
</html>
"""

# --- Auth routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template_string(TEMPLATE_LOGIN)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- HTML Section routes ---
@app.route('/')
@login_required
def index():
    return render_template_string(TEMPLATE_INDEX)

@app.route('/info', methods=['GET', 'POST'])
@login_required
def show_info():
    config = load_config()
    section = 'info'
    if section not in config:
        config.add_section(section)
        save_config(config)
    data = dict(config.items(section))
    if request.method == 'POST':
        total = int(request.form['total'])
        for i in range(total):
            k = request.form.get(f'key_{i}')
            v = request.form.get(f'val_{i}')
            if k:
                config.set(section, k, v)
        save_config(config)
        flash('Saved!')
        return redirect(url_for('show_info'))
    return render_template_string(TEMPLATE_SECTION, section=section, data=data)

@app.route('/realtime', methods=['GET', 'POST'])
@login_required
def show_realtime():
    config = load_config()
    section = 'realtime'
    if section not in config:
        config.add_section(section)
        save_config(config)
    data = dict(config.items(section))
    if request.method == 'POST':
        total = int(request.form['total'])
        for i in range(total):
            k = request.form.get(f'key_{i}')
            v = request.form.get(f'val_{i}')
            if k:
                config.set(section, k, v)
        save_config(config)
        flash('Saved!')
        return redirect(url_for('show_realtime'))
    return render_template_string(TEMPLATE_SECTION, section=section, data=data)

@app.route('/users_html')
@login_required
def list_users_html():
    config = load_config()
    users = get_user_sections(config)
    return render_template_string(TEMPLATE_USERS, users=users)

@app.route('/users_html/<username>', methods=['GET', 'POST'])
@login_required
def edit_user(username):
    config = load_config()
    section = f'user-{username}'
    if section not in config:
        flash('User not found!')
        return redirect(url_for('list_users_html'))
    data = dict(config.items(section))
    if request.method == 'POST':
        total = int(request.form['total'])
        for i in range(total):
            k = request.form.get(f'key_{i}')
            v = request.form.get(f'val_{i}')
            if k:
                config.set(section, k, v)
        save_config(config)
        flash('Saved!')
        return redirect(url_for('edit_user', username=username))
    return render_template_string(TEMPLATE_EDIT_USER, username=username, data=data)

# --- JSON API endpoints (edit only) ---
@app.route('/users', methods=['GET'])
@login_required
def list_users():
    config = load_config()
    users = []
    for section in get_user_sections(config):
        users.append({
            "section": section,
            "data": dict(config.items(section))
        })
    return jsonify(users)

@app.route('/users/<username>', methods=['GET'])
@login_required
def get_user(username):
    config = load_config()
    section = f'user-{username}'
    if section not in config:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(config.items(section)))

@app.route('/users/<username>', methods=['PUT'])
@login_required
def update_user(username):
    config = load_config()
    section = f'user-{username}'
    if section not in config:
        return jsonify({"error": "User not found"}), 404
    data = request.json
    for k, v in data.items():
        config.set(section, k, str(v))
    save_config(config)
    return jsonify({"message": "User updated"})

@app.route('/info', methods=['GET'])
@login_required
def get_info_json():
    config = load_config()
    if 'info' not in config:
        return jsonify({"error": "info section not found"}), 404
    return jsonify(dict(config.items('info')))

@app.route('/info', methods=['PUT'])
@login_required
def update_info_json():
    config = load_config()
    if 'info' not in config:
        config.add_section('info')
    data = request.json
    for k, v in data.items():
        config.set('info', k, str(v))
    save_config(config)
    return jsonify({"message": "info section updated"})

@app.route('/realtime', methods=['GET'])
@login_required
def get_realtime_json():
    config = load_config()
    if 'realtime' not in config:
        return jsonify({"error": "realtime section not found"}), 404
    return jsonify(dict(config.items('realtime')))

@app.route('/realtime', methods=['PUT'])
@login_required
def update_realtime_json():
    config = load_config()
    if 'realtime' not in config:
        config.add_section('realtime')
    data = request.json
    for k, v in data.items():
        config.set('realtime', k, str(v))
    save_config(config)
    return jsonify({"message": "realtime section updated"})

@app.route('/show_log')
@login_required
def show_log():
    log_dir = "./log"
    log_files = sorted(glob.glob(os.path.join(log_dir, "*.log")), key=os.path.getmtime, reverse=True)
    log_content = ""
    log_file_name = ""
    if log_files:
        log_file_name = os.path.basename(log_files[0])
        try:
            with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()[-10000:]  # Show last 10,000 chars for performance
        except Exception as e:
            log_content = f"Error reading log file: {e}"
    else:
        log_content = "No log files found."

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <title>Latest Log File</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        pre { background: #f8f9fa; padding: 1em; border-radius: 5px; max-height: 70vh; overflow-y: auto; }
      </style>
    </head>
    <body class="bg-light">
    <div class="container mt-4">
      <h2>Latest Log File: {{ log_file_name }}</h2>
      <a href="{{ url_for('index') }}" class="btn btn-secondary mb-3">Back</a>
      <pre>{{ log_content }}</pre>
    </div>
    </body>
    </html>
    """, log_content=log_content, log_file_name=log_file_name)

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
    # For production, set debug=False and use_reloader=False
    # app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
