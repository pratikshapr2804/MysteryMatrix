"""
similarity.py  -  Member 4: Dot Product & Cosine Similarity
Mystery Matrix | PES University

Pure Python (standard library only), so it runs anywhere.

Representations
---------------
  "count"   : each case vector = number of evidence rows carrying each feature
              (Member 4's approach).
  "binary"  : each case vector = 1 if the feature appears at least once in the
              case, else 0  (same idea as Member 2's presence/absence profile).
These answer slightly different questions. Never mix them silently.

IMPORTANT: a similarity score compares encoded feature patterns only.
It does NOT show that two real cases are linked, or prove guilt.
"""

import csv
import math

FEATURE_COLUMNS = [
    "physical", "biological", "digital", "documentary", "communication",
    "location", "forensic", "testimonial", "financial",
]

DISCLAIMER = ("Similarity compares encoded evidence-feature patterns only. "
              "It does not show that two real cases are connected, "
              "and it does not prove guilt.")


# ----------------------------------------------------------------------
# 1. Core vector mathematics
# ----------------------------------------------------------------------
def dot_product(vector_a, vector_b):
    """Sum of products of corresponding entries."""
    if len(vector_a) != len(vector_b):
        raise ValueError(f"Vectors must have equal length "
                         f"({len(vector_a)} vs {len(vector_b)}).")
    return sum(a * b for a, b in zip(vector_a, vector_b))


def vector_magnitude(vector):
    """Euclidean norm  ||v|| = sqrt(v . v)."""
    return math.sqrt(dot_product(vector, vector))


def normalize_vector(vector):
    """Unit vector v/||v||.  Returns a zero vector if ||v|| == 0."""
    mag = vector_magnitude(vector)
    if mag == 0:
        return [0.0] * len(vector)
    return [x / mag for x in vector]


def cosine_similarity(vector_a, vector_b):
    """cos(theta) = (a . b) / (||a|| ||b||).
    Returns None if either vector is the zero vector (undefined).
    Clipped to [-1, 1] only to absorb floating-point drift."""
    mag_a = vector_magnitude(vector_a)
    mag_b = vector_magnitude(vector_b)
    if mag_a == 0 or mag_b == 0:
        return None
    value = dot_product(vector_a, vector_b) / (mag_a * mag_b)
    return max(-1.0, min(1.0, value))


# ----------------------------------------------------------------------
# 2. Building case vectors from evidence.csv
# ----------------------------------------------------------------------
def build_case_matrix(file_path="evidence.csv"):
    """Validate evidence.csv, group rows by case_id and sum each feature.
    Returns {case_id: [9 feature counts]} in FEATURE_COLUMNS order."""
    try:
        f = open(file_path, newline="", encoding="utf-8-sig")
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find '{file_path}'. Run from the "
                                f"MysteryMatrix folder.") from None
    with f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in ["case_id"] + FEATURE_COLUMNS if c not in header]
        if missing:
            raise ValueError(f"{file_path} is missing column(s): {missing}")
        matrix = {}
        for line_no, row in enumerate(reader, start=2):
            cid = (row["case_id"] or "").strip()
            if not cid:
                raise ValueError(f"{file_path} line {line_no}: blank case_id.")
            vec = matrix.setdefault(cid, [0] * len(FEATURE_COLUMNS))
            for i, col in enumerate(FEATURE_COLUMNS):
                raw = (row[col] or "").strip()
                if raw not in ("0", "1"):
                    raise ValueError(f"{file_path} line {line_no}: column "
                                     f"'{col}' must be 0 or 1, got '{raw}'.")
                vec[i] += int(raw)
    if not matrix:
        raise ValueError(f"{file_path} contains no evidence rows.")
    return matrix


def to_binary_matrix(case_matrix):
    """Presence/absence version of a count matrix (1 if count > 0)."""
    return {cid: [1 if x > 0 else 0 for x in vec]
            for cid, vec in _as_dict(case_matrix).items()}


def get_matrix(representation="count", file_path="evidence.csv"):
    """Convenience: case matrix in the chosen representation."""
    counts = build_case_matrix(file_path)
    if representation == "count":
        return counts
    if representation == "binary":
        return to_binary_matrix(counts)
    raise ValueError("representation must be 'count' or 'binary'")


def _as_dict(case_matrix):
    """Accept a dict {id: vector} or a pandas-like DataFrame (index + rows)."""
    if isinstance(case_matrix, dict):
        return case_matrix
    if hasattr(case_matrix, "index") and hasattr(case_matrix, "values"):
        return {str(i): [float(x) for x in row]
                for i, row in zip(case_matrix.index, case_matrix.values)}
    raise TypeError("case_matrix must be a dict or a DataFrame-like object.")


# ----------------------------------------------------------------------
# 3. Pairwise similarity
# ----------------------------------------------------------------------
def calculate_similarity_matrix(case_matrix):
    """All-pairs cosine similarity.
    Returns (case_ids, matrix) where matrix[i][j] = cos(case i, case j)
    (None where undefined)."""
    data = _as_dict(case_matrix)
    ids = sorted(data)
    matrix = [[cosine_similarity(data[a], data[b]) for b in ids] for a in ids]
    return ids, matrix


def compare_cases(case_matrix, id_a, id_b):
    """Every intermediate quantity for one pair (for the 'show calculation'
    panel). Nothing is hardcoded - all values are computed."""
    data = _as_dict(case_matrix)
    a, b = data[id_a], data[id_b]
    return {
        "case_a": id_a, "case_b": id_b,
        "vector_a": list(a), "vector_b": list(b),
        "products": [x * y for x, y in zip(a, b)],
        "dot": dot_product(a, b),
        "mag_a": vector_magnitude(a), "mag_b": vector_magnitude(b),
        "unit_a": normalize_vector(a), "unit_b": normalize_vector(b),
        "cosine": cosine_similarity(a, b),
    }


def most_similar(case_matrix, case_id):
    """Other cases ranked by cosine similarity to case_id (highest first)."""
    data = _as_dict(case_matrix)
    ranked = []
    for other in sorted(data):
        if other != case_id:
            ranked.append((other, cosine_similarity(data[case_id], data[other])))
    ranked.sort(key=lambda t: (t[1] is None, -(t[1] or 0)))
    return ranked


def shared_features(case_matrix, id_a, id_b):
    """Features with a non-zero entry in BOTH cases, and the features that
    contribute most to the dot product."""
    data = _as_dict(case_matrix)
    rows = []
    for i, name in enumerate(FEATURE_COLUMNS):
        p = data[id_a][i] * data[id_b][i]
        if p > 0:
            rows.append((name, data[id_a][i], data[id_b][i], p))
    rows.sort(key=lambda r: -r[3])
    return rows


# ----------------------------------------------------------------------
# 4. Plain-language interpretation
# ----------------------------------------------------------------------
def interpret_similarity(score):
    """Short, honest description of a cosine score."""
    if score is None:
        return "Undefined - one case has no features recorded (zero vector)."
    if score >= 0.90:
        band = "very similar feature mix"
    elif score >= 0.75:
        band = "fairly similar feature mix"
    elif score >= 0.50:
        band = "moderately similar feature mix"
    else:
        band = "quite different feature mix"
    return (f"{score:.3f}: {band}. (Feature counts are never negative, so "
            f"scores here sit between 0 and 1.)")


# ----------------------------------------------------------------------
# 5. Case labels and CSV export
# ----------------------------------------------------------------------
def load_case_names(file_path="cases.csv"):
    """{case_id: case_name}; returns {} if the file is unreadable."""
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            return {r["case_id"].strip(): r["case_name"].strip()
                    for r in csv.DictReader(f)}
    except (OSError, KeyError):
        return {}


def short_name(full_name):
    """'BTK — Dennis Rader' -> 'BTK'."""
    for sep in (" — ", " - ", " – "):
        if sep in full_name:
            return full_name.split(sep)[0]
    return full_name


def save_similarity_csv(ids, matrix, path="similarity_results.csv"):
    """WARNING: this overwrites the file. Member 2's file of that name uses
    the binary representation, so pass a different path unless you mean it."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([""] + ids)
        for cid, row in zip(ids, matrix):
            w.writerow([cid] + ["" if v is None else round(v, 4) for v in row])


if __name__ == "__main__":
    for rep in ("count", "binary"):
        m = get_matrix(rep)
        ids, sim = calculate_similarity_matrix(m)
        print(f"\n--- {rep} representation ---")
        print("      " + "".join(f"{i:>7}" for i in ids))
        for cid, row in zip(ids, sim):
            print(f"{cid:<6}" + "".join(
                f"{'n/a':>7}" if v is None else f"{v:7.3f}" for v in row))
    print("\n" + DISCLAIMER)