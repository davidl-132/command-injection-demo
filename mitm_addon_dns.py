import re
import urllib.parse

from mitmproxy import http, ctx

# Flag (True = Fix, False = UnFix)
DECODE_BEFORE_CHECK = True

CMD_INJECT_PATTERNS = [r"[;|&$`]", r"\$\(.*\)", r"`.*`"]


def request(flow: http.HTTPFlow) -> None:
    if flow.request.method != "POST" or "/dns" not in flow.request.path:
        return

    raw_body = flow.request.get_text() or ""

    if DECODE_BEFORE_CHECK:
        # FIX: encode URL-encoding before compare regex matching.
        body = urllib.parse.unquote(raw_body)
    else:
        # UNFIX: decode ';' to '%3B' so regex is useless
        body = raw_body

    for pat in CMD_INJECT_PATTERNS:
        if re.search(pat, body):
            tag = f"Command Injection (matched: {pat})"
            if tag not in (flow.comment or ""):
                flow.comment = (flow.comment or "") + f" [{tag}]"
                ctx.log.info(f"[DNS-DEMO] ⚠ {tag} (decode={DECODE_BEFORE_CHECK})")
            break
