from flask import Flask, request, jsonify, Response
import json, os, subprocess

app = Flask(__name__)
DATA_FILE = "redirects.json"

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def open_in_chromium(url):
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.Popen(
        ["chromium", "--no-sandbox", f"--display=:1", url],
        env={**os.environ, "DISPLAY": ":1"}
    )

@app.route("/")
def index():
    redirects = load()
    rows = "".join(f"""
        <tr>
            <td><code>/{k}</code></td>
            <td>{v}</td>
            <td>
                <button onclick="openLink('{v}')">▶ Open</button>
                <button onclick="del('{k}')" style="background:#e53935">🗑</button>
            </td>
        </tr>
    """ for k, v in redirects.items())

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MyBrowser</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family:sans-serif; background:#0f0f0f; color:#eee; height:100vh; display:flex; flex-direction:column; }}
            #toolbar {{ background:#1a1a2e; padding:10px 16px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
            input {{ padding:7px 10px; border-radius:6px; border:1px solid #444; background:#111; color:#eee; }}
            button {{ padding:7px 14px; border-radius:6px; border:none; background:#7c6aff; color:white; cursor:pointer; }}
            button:hover {{ background:#5a49cc; }}
            #browser-frame {{ flex:1; border:none; width:100%; }}
            #links-panel {{ background:#111; padding:10px 16px; max-height:200px; overflow-y:auto; }}
            table {{ width:100%; border-collapse:collapse; }}
            th, td {{ padding:8px 10px; border-bottom:1px solid #222; font-size:0.85em; }}
            code {{ background:#1e1e1e; padding:2px 6px; border-radius:4px; color:#7c6aff; }}
            #msg {{ color:#4caf50; font-size:0.85em; }}
        </style>
    </head>
    <body>
        <div id="toolbar">
            <strong style="color:#7c6aff">🌐 MyBrowser</strong>
            <input id="url-bar" placeholder="Enter URL..." style="width:340px" />
            <button onclick="goTo()">Go</button>
            <span id="msg"></span>
            <input id="slug" placeholder="slug (e.g. yt)" style="width:120px" />
            <input id="new-url" placeholder="https://youtube.com" style="width:240px" />
            <button onclick="addLink()">+ Save Link</button>
        </div>

        <!-- noVNC iframe — live view of the server's Chrome -->
        <iframe
            id="browser-frame"
            src="http://localhost:6080/vnc.html?autoconnect=true&resize=scale&show_dot=true"
        ></iframe>

        <div id="links-panel">
            <table>
                <tr><th>Slug</th><th>URL</th><th>Action</th></tr>
                {rows}
            </table>
        </div>

        <script>
            function goTo() {{
                let url = document.getElementById('url-bar').value.trim();
                if (!url) return;
                openLink(url);
            }}

            async function openLink(url) {{
                if (!url.startsWith('http')) url = 'https://' + url;
                document.getElementById('url-bar').value = url;
                await fetch('/api/open', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{url}})
                }});
                showMsg('Opening ' + url + ' in browser...');
            }}

            async function addLink() {{
                const slug = document.getElementById('slug').value.trim();
                const url = document.getElementById('new-url').value.trim();
                if (!slug || !url) return alert('Fill both fields');
                const res = await fetch('/api/add', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug, url}})
                }});
                const data = await res.json();
                showMsg(data.message);
                setTimeout(() => location.reload(), 800);
            }}

            async function del(slug) {{
                if (!confirm('Delete /' + slug + '?')) return;
                await fetch('/api/delete', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug}})
                }});
                location.reload();
            }}

            function showMsg(msg) {{
                const el = document.getElementById('msg');
                el.textContent = msg;
                setTimeout(() => el.textContent = '', 3000);
            }}

            document.getElementById('url-bar').addEventListener('keydown', e => {{
                if (e.key === 'Enter') goTo();
            }});
        </script>
    </body>
    </html>
    """

@app.route("/api/open", methods=["POST"])
def api_open():
    url = request.json.get("url", "")
    if not url.startswith("http"):
        url = "https://" + url
    open_in_chromium(url)
    return jsonify({"message": f"Opened {url}"})

@app.route("/api/add", methods=["POST"])
def api_add():
    data = load()
    body = request.json
    slug = body.get("slug", "").strip().lower()
    url = body.get("url", "").strip()
    if not url.startswith("http"):
        url = "https://" + url
    data[slug] = url
    save(data)
    return jsonify({"message": f"✅ Saved /{slug}"})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = load()
    slug = request.json.get("slug", "")
    if slug in data:
        del data[slug]
        save(data)
    return jsonify({"message": f"🗑 Deleted /{slug}"})

@app.route("/<slug>")
def open_slug(slug):
    data = load()
    target = data.get(slug)
    if target:
        open_in_chromium(target)
        return f"<script>window.location='/'</script>"
    return "Not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
