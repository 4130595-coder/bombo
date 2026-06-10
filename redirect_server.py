from flask import Flask, request, jsonify, Response
import json, os, requests
from urllib.parse import urljoin, urlparse

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

@app.route("/proxy")
def proxy():
    url = request.args.get("url", "")
    if not url:
        return "No URL provided", 400
    if not url.startswith("http"):
        url = "https://" + url
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Rewrite links to go through proxy
        content = resp.text
        base = f"{request.host_url}proxy?url="
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Inject base rewriting script
        inject = f"""
        <base href="{base_url}">
        <script>
        // Rewrite all link clicks to go through proxy
        document.addEventListener('click', function(e) {{
            const a = e.target.closest('a');
            if (a && a.href && !a.href.startsWith('{request.host_url}')) {{
                e.preventDefault();
                window.parent.postMessage({{type:'navigate', url: a.href}}, '*');
            }}
        }});
        </script>
        """
        content = content.replace("</head>", inject + "</head>", 1)
        
        return Response(content, 
                       status=resp.status_code,
                       content_type=resp.headers.get('content-type', 'text/html'))
    except Exception as e:
        return f"<h2>Error loading page</h2><p>{str(e)}</p>", 500

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
        <title>MyBrowser</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: sans-serif; background: #0f0f0f; color: #eee; height: 100vh; display: flex; flex-direction: column; }}
            #toolbar {{ background: #1a1a2e; padding: 10px 16px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
            #toolbar input {{ padding: 7px 10px; border-radius: 6px; border: 1px solid #444; background: #111; color: #eee; }}
            #toolbar button {{ padding: 7px 14px; border-radius: 6px; border: none; background: #7c6aff; color: white; cursor: pointer; }}
            #frame-container {{ flex: 1; position: relative; }}
            #site-frame {{ width: 100%; height: 100%; border: none; }}
            #placeholder {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); text-align: center; color: #555; }}
            #links-panel {{ background: #111; padding: 10px 16px; max-height: 180px; overflow-y: auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 6px 10px; border-bottom: 1px solid #222; font-size: 0.85em; }}
            code {{ background: #1e1e1e; padding: 2px 6px; border-radius: 4px; color: #7c6aff; }}
            button {{ padding: 5px 10px; border-radius: 5px; border: none; background: #7c6aff; color: white; cursor: pointer; margin-right: 4px; }}
        </style>
    </head>
    <body>
        <div id="toolbar">
            <strong style="color:#7c6aff">🔀 MyBrowser</strong>
            <input id="url-bar" placeholder="Enter URL..." style="width:300px" />
            <button onclick="goTo()">Go</button>
            <input id="slug" placeholder="slug" style="width:100px" />
            <input id="new-url" placeholder="https://..." style="width:220px" />
            <button onclick="addLink()">+ Save</button>
        </div>

        <div id="frame-container">
            <div id="placeholder">
                <h2>Enter a URL above</h2>
                <p style="margin-top:8px;color:#444">Pages load through your server</p>
            </div>
            <iframe id="site-frame" src="" style="display:none"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups">
            </iframe>
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
                frame.src = '/proxy?url=' + encodeURIComponent(url);
                frame.style.display = 'block';
                document.getElementById('placeholder').style.display = 'none';
            }}

            // Listen for navigation messages from inside iframe
            window.addEventListener('message', function(e) {{
                if (e.data.type === 'navigate') {{
                    loadSite(e.data.url);
                }}
            }});

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
                if (!confirm('Delete?')) return;
                await fetch('/api/delete', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{slug}})
                }});
                location.reload();
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
    slug = body.get("slug","").strip().lower()
    url = body.get("url","").strip()
    if not url.startswith("http"):
        url = "https://" + url
    data[slug] = url
    save(data)
    return jsonify({"message": f"Added /{slug}"})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = load()
    slug = request.json.get("slug","")
    if slug in data:
        del data[slug]
        save(data)
    return jsonify({"message": "Deleted"})

@app.route("/<slug>")
def open_slug(slug):
    data = load()
    target = data.get(slug)
    if target:
        return f"""<html><body style="margin:0">
        <iframe src="/proxy?url={target}" style="width:100%;height:100vh;border:none"
            sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
        </body></html>"""
    return f"Not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
