from flask import Flask, request, jsonify
import json, os

app = Flask(__name__)
DATA_FILE = "redirects.json"

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"yt": "https://youtube.com"}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

@app.route("/")
def index():
    redirects = load()
    rows = "".join(f"""
        <tr>
            <td><code>/{k}</code></td>
            <td>{v}</td>
            <td>
                <button onclick="openSite('{v}')">▶ Open</button>
                <button onclick="del('{k}')" style="background:#e53935">🗑</button>
            </td>
        </tr>
    """ for k, v in redirects.items())

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Browser</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: sans-serif; background: #0f0f0f; color: #eee; height: 100vh; display: flex; flex-direction: column; }}
            #toolbar {{ background: #1a1a2e; padding: 10px 16px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
            #toolbar input {{ padding: 7px 10px; border-radius: 6px; border: 1px solid #444; background: #111; color: #eee; width: 260px; }}
            #toolbar button {{ padding: 7px 14px; border-radius: 6px; border: none; background: #7c6aff; color: white; cursor: pointer; }}
            #toolbar button:hover {{ background: #5a49cc; }}
            #frame-container {{ flex: 1; position: relative; }}
            #site-frame {{ width: 100%; height: 100%; border: none; }}
            #placeholder {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #555; }}
            #links-panel {{ background: #111; padding: 10px 16px; max-height: 180px; overflow-y: auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 6px 10px; border-bottom: 1px solid #222; text-align: left; font-size: 0.85em; }}
            code {{ background: #1e1e1e; padding: 2px 6px; border-radius: 4px; color: #7c6aff; }}
            button {{ padding: 5px 10px; border-radius: 5px; border: none; background: #7c6aff; color: white; cursor: pointer; margin-right: 4px; }}
            #toggle-btn {{ background: #333; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div id="toolbar">
            <strong style="color:#7c6aff">🔀 MyBrowser</strong>
            <input id="url-bar" placeholder="Enter URL or pick from list below..." />
            <button onclick="goTo()">Go</button>
            <input id="slug" placeholder="slug (e.g. yt)" style="width:120px" />
            <input id="new-url" placeholder="https://youtube.com" style="width:220px" />
            <button onclick="addLink()">+ Save</button>
            <button id="toggle-btn" onclick="togglePanel()">▼ Saved Links</button>
        </div>

        <div id="frame-container">
            <div id="placeholder">
                <h2>Enter a URL above or pick a saved link</h2>
                <p style="margin-top:8px;color:#444">The site will load here</p>
            </div>
            <iframe id="site-frame" src="" style="display:none"></iframe>
        </div>

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
                if (!url.startsWith('http')) url = 'https://' + url;
                loadSite(url);
            }}

            function openSite(url) {{
                document.getElementById('url-bar').value = url;
                loadSite(url);
            }}

            function loadSite(url) {{
                const frame = document.getElementById('site-frame');
                const placeholder = document.getElementById('placeholder');
                frame.src = url;
                frame.style.display = 'block';
                placeholder.style.display = 'none';
            }}

            async function addLink() {{
                const slug = document.getElementById('slug').value.trim();
                const url = document.getElementById('new-url').value.trim();
                if (!slug || !url) return alert('Fill both fields');
                await fetch('/api/add', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug, url}})
                }});
                location.reload();
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

            function togglePanel() {{
                const panel = document.getElementById('links-panel');
                panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            }}

            document.getElementById('url-bar').addEventListener('keydown', e => {{
                if (e.key === 'Enter') goTo();
            }});
        </script>
    </body>
    </html>
    """

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
    return jsonify({"message": f"Added /{slug}"})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = load()
    slug = request.json.get("slug", "")
    if slug in data:
        del data[slug]
        save(data)
    return jsonify({"message": "Deleted"})

@app.route("/<slug>")
def open_slug(slug):
    data = load()
    target = data.get(slug)
    if target:
        return f"""
        <html><body style="margin:0">
        <iframe src="{target}" style="width:100%;height:100vh;border:none"></iframe>
        </body></html>
        """
    return f"No link found for '{slug}'", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
