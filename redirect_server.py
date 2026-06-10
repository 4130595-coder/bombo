from flask import Flask, redirect, request, jsonify
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
            <td><a href="{v}" target="_blank">{v}</a></td>
            <td><button onclick="del('{k}')">🗑 Delete</button></td>
        </tr>
    """ for k, v in redirects.items())

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirector</title>
        <style>
            body {{ font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; background: #0f0f0f; color: #eee; }}
            h1 {{ color: #7c6aff; }}
            input {{ padding: 8px; border-radius: 6px; border: 1px solid #444; background: #1e1e1e; color: #eee; width: 200px; }}
            button {{ padding: 8px 14px; border-radius: 6px; border: none; background: #7c6aff; color: white; cursor: pointer; margin-left: 6px; }}
            button:hover {{ background: #5a49cc; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
            th, td {{ padding: 10px 12px; border-bottom: 1px solid #2a2a2a; text-align: left; }}
            th {{ color: #aaa; font-size: 0.85em; text-transform: uppercase; }}
            code {{ background: #1e1e1e; padding: 2px 6px; border-radius: 4px; color: #7c6aff; }}
            .add-row {{ display: flex; gap: 8px; margin-top: 20px; }}
            .msg {{ margin-top: 10px; color: #4caf50; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>🔀 Redirector</h1>
        <p>Your base URL: <code>{request.host_url}</code></p>

        <div class="add-row">
            <input id="slug" placeholder="slug (e.g. yt)" />
            <input id="url" placeholder="https://youtube.com" style="width:280px" />
            <button onclick="add()">+ Add</button>
        </div>
        <div class="msg" id="msg"></div>

        <table>
            <tr><th>Slug</th><th>Destination</th><th>Action</th></tr>
            {rows}
        </table>

        <script>
            async function add() {{
                const slug = document.getElementById('slug').value.trim();
                const url = document.getElementById('url').value.trim();
                if (!slug || !url) return alert('Fill both fields');
                const res = await fetch('/api/add', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug, url}})
                }});
                const data = await res.json();
                document.getElementById('msg').textContent = data.message;
                setTimeout(() => location.reload(), 800);
            }}

            async function del(slug) {{
                if (!confirm('Delete /' + slug + '?')) return;
                const res = await fetch('/api/delete', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug}})
                }});
                const data = await res.json();
                document.getElementById('msg').textContent = data.message;
                setTimeout(() => location.reload(), 800);
            }}
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
    if not slug or not url:
        return jsonify({"message": "Missing slug or URL"}), 400
    if not url.startswith("http"):
        url = "https://" + url
    data[slug] = url
    save(data)
    return jsonify({"message": f"✅ Added /{slug}"})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = load()
    slug = request.json.get("slug", "")
    if slug in data:
        del data[slug]
        save(data)
        return jsonify({"message": f"🗑 Deleted /{slug}"})
    return jsonify({"message": "Not found"}), 404

@app.route("/<slug>")
def redirecter(slug):
    data = load()
    target = data.get(slug)
    if target:
        return redirect(target, code=302)
    return f"No redirect found for '{slug}'", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
