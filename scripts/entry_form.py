"""Local-only web form for entering the pool's real bettors + picks.

Run it, open the printed URL in a browser, fill in each bettor's name and
their 1-4 order for all 8 divisions, click Save. It overwrites
data/bettors.json and data/picks.json directly on disk -- nothing here
talks to the network or any external host, it's just a friendlier way to
hand-edit those two files.

The number of bettors is read from data/bettors.json each time the page
loads (not hardcoded), so the pool can grow or shrink just by adding/
removing a name field before saving.

Usage:
    python scripts/entry_form.py
    (then open http://localhost:8765/ )
    Ctrl+C to stop once you're done saving.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
PORT = 8765


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_context() -> dict:
    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    picks_data = load_json(DATA_DIR / "picks.json")

    divisions = divisions_data["divisions"]
    division_ids = [d["id"] for d in divisions]

    bettor_names = [b["name"] for b in bettors_data["bettors"]]
    existing_bettor_ids = [b["id"] for b in bettors_data["bettors"]]

    pick_grid = []
    for i, bid in enumerate(existing_bettor_ids):
        row = {}
        for div_id in division_ids:
            if bid in picks_data.get("picks", {}) and div_id in picks_data["picks"][bid]:
                row[div_id] = picks_data["picks"][bid][div_id]
            else:
                row[div_id] = [None, None, None, None]
        pick_grid.append(row)

    return {
        "divisions": divisions,
        "division_ids": division_ids,
        "bettor_names": bettor_names,
        "num_bettors": len(bettor_names),
        "pick_grid": pick_grid,
    }


def validate_payload(names: list, picks: dict, divisions_data: dict) -> list:
    errors = []
    num_bettors = len(names)
    if num_bettors == 0 or any(not n.strip() for n in names):
        errors.append("Need at least 1 bettor, and every bettor needs a non-empty name.")

    expected_teams = {d["id"]: {t["id"] for t in d["teams"]} for d in divisions_data["divisions"]}

    for i in range(num_bettors):
        bettor_picks = picks.get(str(i))
        if bettor_picks is None:
            errors.append(f"Bettor {i + 1}: no picks submitted.")
            continue
        for div_id, expected in expected_teams.items():
            teams = bettor_picks.get(div_id)
            if not teams or len(teams) != 4:
                errors.append(f"Bettor {i + 1} / {div_id}: expected 4 teams.")
                continue
            if set(teams) != expected:
                errors.append(f"Bettor {i + 1} / {div_id}: teams don't match {sorted(expected)}.")
            if len(set(teams)) != 4:
                errors.append(f"Bettor {i + 1} / {div_id}: duplicate team picked.")
    return errors


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep console quiet; errors still surface via response bodies

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
        template = env.get_template("entry_form.html.j2")
        html = template.render(**build_context())
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            names = payload["names"]
            picks_in = payload["picks"]
        except (json.JSONDecodeError, KeyError) as e:
            self._send_json(400, {"ok": False, "errors": [f"Malformed request: {e}"]})
            return

        divisions_data = load_json(DATA_DIR / "divisions.json")
        errors = validate_payload(names, picks_in, divisions_data)
        if errors:
            self._send_json(400, {"ok": False, "errors": errors})
            return

        num_bettors = len(names)
        ids = [f"bettor-{i + 1}" for i in range(num_bettors)]
        bettors_out = {"bettors": [{"id": ids[i], "name": names[i].strip()} for i in range(num_bettors)]}
        picks_out = {
            "_sample_data": False,
            "_note": "Locked pool picks, entered via scripts/entry_form.py.",
            "picks": {ids[i]: picks_in[str(i)] for i in range(num_bettors)},
        }

        with open(DATA_DIR / "bettors.json", "w", encoding="utf-8") as f:
            json.dump(bettors_out, f, indent=2)
        with open(DATA_DIR / "picks.json", "w", encoding="utf-8") as f:
            json.dump(picks_out, f, indent=2)

        self._send_json(200, {"ok": True})


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"Pick entry form running at http://localhost:{PORT}/")
    print("Ctrl+C to stop once you're done saving.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
