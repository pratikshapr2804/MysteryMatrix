"""
data_manager.py - loads and validates cases.csv, evidence.csv, features.csv.
Everything the game shows about a case comes from these files.
"""
import csv
from pathlib import Path

FEATURES = ["physical", "biological", "digital", "documentary", "communication",
            "location", "forensic", "testimonial", "financial"]

FALLBACK_NAMES = {"C01": "BTK", "C02": "Golden State Killer", "C03": "Unabomber",
                  "C04": "Oklahoma City Bombing", "C05": "Bernie Madoff"}


def short_title(name):
    for sep in (" — ", " – ", " - "):
        if sep in name:
            return name.split(sep)[0].strip()
    return name.strip()


def _read(path):
    if not path.exists():
        return None, None, f"Missing file: {path.name}"
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader), (reader.fieldnames or []), None
    except Exception as exc:
        return None, None, f"Could not read {path.name}: {exc}"


class Dataset:
    def __init__(self, root):
        self.root = Path(root)
        self.cases = []            # list of dicts
        self.evidence = {}         # case_id -> list of evidence dicts
        self.feature_defs = {}
        self.status = []           # (filename, row_count, error or None)
        self.errors = []
        self._load()

    # ------------------------------------------------------------------
    def _load(self):
        cases_rows, c_head, c_err = _read(self.root / "cases.csv")
        ev_rows, e_head, e_err = _read(self.root / "evidence.csv")
        f_rows, f_head, f_err = _read(self.root / "features.csv")
        self.status = [("cases.csv", len(cases_rows or []), c_err),
                       ("evidence.csv", len(ev_rows or []), e_err),
                       ("features.csv", len(f_rows or []), f_err)]
        for _, _, err in self.status:
            if err:
                self.errors.append(err)

        for r in (f_rows or []):
            fid = (r.get("feature_id") or "").strip().lower()
            if fid:
                self.feature_defs[fid] = (r.get("definition") or "").strip()

        if ev_rows is not None:
            missing = [c for c in ["case_id", "evidence_id", "description"] + FEATURES
                       if c not in (e_head or [])]
            if missing:
                self.errors.append(f"evidence.csv is missing column(s): {', '.join(missing)}")
            else:
                self._load_evidence(ev_rows)

        meta = {}
        for r in (cases_rows or []):
            cid = (r.get("case_id") or "").strip()
            if cid:
                meta[cid] = r
        for cid in list(self.evidence):
            if cid not in meta:
                meta[cid] = {}
        for cid in sorted(meta):
            r = meta[cid]
            name = (r.get("case_name") or "").strip() or FALLBACK_NAMES.get(cid, "Case " + cid)
            self.cases.append({
                "id": cid, "name": name, "short": short_title(name),
                "subject": (r.get("primary_subject") or "").strip(),
                "category": (r.get("crime_category") or "").strip(),
                "period": (r.get("period") or "").strip(),
                "outcome": (r.get("legal_outcome") or "").strip(),
                "summary": (r.get("case_summary") or "").strip(),
            })

    def _load_evidence(self, rows):
        seen = set()
        for n, r in enumerate(rows, start=2):
            cid = (r.get("case_id") or "").strip()
            eid = (r.get("evidence_id") or "").strip()
            if not cid or not eid:
                self.errors.append(f"evidence.csv line {n}: blank case_id or evidence_id (row skipped)")
                continue
            if eid in seen:
                self.errors.append(f"evidence.csv line {n}: duplicate evidence_id {eid} (row skipped)")
                continue
            flags, bad = {}, False
            for f in FEATURES:
                v = (r.get(f) or "").strip()
                if v not in ("0", "1"):
                    self.errors.append(f"evidence.csv line {n} ({eid}): '{f}' must be 0/1, got '{v}' (row skipped)")
                    bad = True
                    break
                flags[f] = int(v)
            if bad:
                continue
            seen.add(eid)
            self.evidence.setdefault(cid, []).append({
                "id": eid, "case_id": cid,
                "description": (r.get("description") or "").strip(),
                "source_title": (r.get("source_title") or "").strip(),
                "source_url": (r.get("source_url") or "").strip(),
                "source_type": (r.get("source_type") or "").strip(),
                "status": (r.get("status") or "").strip(),
                "coding_note": (r.get("coding_note") or "").strip(),
                "flags": flags, "vector": [flags[f] for f in FEATURES],
            })

    # ------------------------------------------------------------------
    def playable_cases(self):
        return [c for c in self.cases if self.evidence.get(c["id"])]

    def case(self, cid):
        return next((c for c in self.cases if c["id"] == cid), None)