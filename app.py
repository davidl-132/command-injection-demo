import os
import subprocess

from flask import Flask, request, render_template_string

app = Flask(__name__)

PORT = 15001
DNS_CMD = "nslookup" if os.name == "nt" else "host"

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DNS Lookup Demo</title>
  <style>
    body { font-family: 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #222; margin: 0; }
    .container { max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
    .card { background: #fff; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.1); margin-bottom: 1.5rem; }
    input { width: 100%; padding: .6rem; border: 1px solid #ccc; border-radius: 5px; font-size: 1rem; margin-bottom: .8rem; box-sizing: border-box; }
    button { padding: .5rem 1.2rem; border-radius: 6px; border: none; background: #4361ee; color: #fff; font-weight: 600; cursor: pointer; }
    button:hover { background: #3a56d4; }
    pre { background: #1e1e2e; color: #cdd6f4; padding: 1rem; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
    h2 { margin-top: 0; }
    .hint { color: #888; font-size: .85rem; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h2>🔎 DNS Lookup Demo</h2>
      <p class="hint">Standalone demo app — command injection via DNS lookup (DNS_CMD = {{ dns_cmd }})</p>
      <form method="POST">
        <label>Domain</label>
        <input type="text" name="domain" placeholder="example.com" value="{{ domain or '' }}">
        <button type="submit">Lookup</button>
      </form>
    </div>
    {% if output %}
    <div class="card">
      <h3>Output</h3>
      <pre>{{ output }}</pre>
    </div>
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(PAGE, dns_cmd=DNS_CMD, domain=None, output=None)


@app.route("/dns", methods=["GET", "POST"])
def dns_lookup():
    output = None
    domain = None
    if request.method == "POST":
        domain = request.form.get("domain", "")
        # Error
        try:
            output = subprocess.check_output(
                f"{DNS_CMD} {domain}",
                shell=True,
                stderr=subprocess.STDOUT,
                timeout=10,
            ).decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as e:
            written = (e.output or b"").decode("utf-8", errors="replace").strip()
            output = written or f"Command failed with exit status {e.returncode}."
        except subprocess.TimeoutExpired as e:
            written = (e.output or b"").decode("utf-8", errors="replace").strip()
            output = ("Command timed out after 10s.\n" + written).rstrip()
        except Exception as e:
            output = str(e)
    return render_template_string(PAGE, dns_cmd=DNS_CMD, domain=domain, output=output)


if __name__ == "__main__":
    print("DNS Lookup Demo (VULNERABLE) listening on http://127.0.0.1:%d/dns" % PORT)
    app.run(host="127.0.0.1", port=PORT, debug=True)
