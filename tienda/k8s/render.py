#!/usr/bin/env python3
"""Regenerates the ConfigMap bodies of app.yaml from postgres/init.sql and load/generate.sh.
Run it after editing either file: python3 k8s/render.py   (from the repo root or anywhere)."""
import hashlib, pathlib, re
root = pathlib.Path(__file__).resolve().parent.parent
app = root / "k8s" / "app.yaml"
text = app.read_text()

def block(key, path):
    body = "".join("    " + line if line.strip() else "\n" for line in (root / path).read_text().splitlines(True))
    return f"  {key}: |\n{body}"

for key, path, marker in (("init.sql", "postgres/init.sql", "# --- end postgres-init ---"),
                          ("generate.sh", "load/generate.sh", "# --- end load-script ---")):
    pattern = re.compile(rf"  {re.escape(key)}: \|\n.*?(?=\n{re.escape(marker)})", re.S)
    assert pattern.search(text), f"marker {marker} not found"
    text = pattern.sub(lambda m: block(key, path).rstrip("\n"), text)
# A ConfigMap change alone does not roll a Deployment: stamp the script's checksum on the pod template
digest = hashlib.sha256((root / "load/generate.sh").read_bytes()).hexdigest()[:16]
text, n = re.subn(r"(checksum/generate-script: )\S+", rf"\g<1>{digest}", text)
assert n == 1, "checksum/generate-script annotation not found in the load Deployment"
app.write_text(text)
print("app.yaml ConfigMaps regenerated from postgres/init.sql and load/generate.sh; load checksum", digest)
