# SPDX-License-Identifier: AGPL-3.0-or-later
"""Copy the validated-method rule passages from docs/agent_protocol.md into mcp_server.py (Round 64).

docs/agent_protocol.md is the single source. Each paragraph that the MCP instructions repeat starts after a line
``<!-- mcp-rules:A -->`` (or ``:B``); the paragraphs of a group are joined in file order and written into the
``_RULES_A`` / ``_RULES_B`` literals between the ``# BEGIN GENERATED RULES`` and ``# END GENERATED RULES`` lines
of mcp_server.py. Edit the protocol, then run this script.

    scripts/sync_rule_text.py          # rewrite mcp_server.py
    scripts/sync_rule_text.py --check  # exit 1 if mcp_server.py is out of date (tests run this)
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/"docs/agent_protocol.md"
SERVER = ROOT/"mcp_server.py"
GROUPS = ("A", "B")


def passages(text, group):
    out = []
    for m in re.finditer(rf"^<!-- mcp-rules:{group} -->\n((?:[^\n]+\n?)+)", text, re.M):
        para = m.group(1).rstrip("\n")
        if '"""' in para or "\\" in para:
            raise SystemExit(f"rule paragraph cannot hold triple quotes or backslashes: {para[:60]!r}")
        out.append(para)
    if not out:
        raise SystemExit(f"no <!-- mcp-rules:{group} --> paragraphs in {PROTOCOL}")
    return "\n\n".join(out)


def render(server, protocol):
    for g in GROUPS:
        pat = re.compile(rf"(# BEGIN GENERATED RULES {g} [^\n]*\n_RULES_{g} = \"\"\"\n)[\s\S]*?(\"\"\"\n# END GENERATED RULES {g}\n)")
        if len(pat.findall(server)) != 1:
            raise SystemExit(f"mcp_server.py needs exactly one generated block {g}")
        body = passages(protocol, g)
        server = pat.sub(lambda m: m.group(1)+body+"\n"+m.group(2), server)
    return server


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    current = SERVER.read_text()
    new = render(current, PROTOCOL.read_text())
    if a.check:
        if new != current:
            print("mcp_server.py rule text differs from docs/agent_protocol.md; run scripts/sync_rule_text.py")
            sys.exit(1)
        return
    if new != current:
        SERVER.write_text(new)
        print("mcp_server.py updated")


if __name__ == "__main__":
    main()
