"""
deduction.py - builds the case-board questions from the REAL data.
Every answer is computed from the CSVs (and Member 4's similarity.py);
nothing is hardcoded. These are game puzzles about dataset labels,
not historical forensic findings.
"""
import random
from data_manager import FEATURES

try:
    import similarity as sim
except Exception:          # similarity.py optional
    sim = None


def _options(correct_text, distractors, rng):
    opts = [correct_text] + [d for d in distractors if d != correct_text][:3]
    rng.shuffle(opts)
    return opts, opts.index(correct_text)


def build_questions(case, found, all_cases):
    """found: evidence dicts the player recovered. Returns list of question dicts."""
    rng = random.Random("q-" + case["id"])
    qs = []

    # 1. Classify the case (cases.csv)
    cats = []
    for c in all_cases:
        if c["category"] and c["category"] not in cats:
            cats.append(c["category"])
    if case["category"]:
        others = [c for c in cats if c != case["category"]]
        rng.shuffle(others)
        opts, ci = _options(case["category"], others, rng)
        if len(opts) >= 2:
            qs.append({"tag": "CLASSIFY", "prompt": "Which crime category does this case file record?",
                       "options": opts, "correct": ci,
                       "explain": f"cases.csv records the category as: {case['category']}.", "math": []})

    # 2. Most common evidence category among the recovered items
    counts = {f: sum(e["flags"][f] for e in found) for f in FEATURES}
    top = max(counts.values()) if counts else 0
    if top > 0:
        best = [f for f in FEATURES if counts[f] == top]
        correct = best[0]
        lower = [f for f in FEATURES if counts[f] < top]
        rng.shuffle(lower)
        opts, ci = _options(correct.upper(), [f.upper() for f in lower], rng)
        tie = f" (tied with {', '.join(b.upper() for b in best[1:])})" if len(best) > 1 else ""
        qs.append({"tag": "PATTERN",
                   "prompt": f"Across the {len(found)} items you recovered, which evidence category appears most often?",
                   "options": opts, "correct": ci,
                   "explain": f"{correct.upper()} is flagged on {top} of {len(found)} items{tie}.",
                   "math": [f"{f.upper():<14}{counts[f]}" for f in FEATURES]})

    # 3. How many items carry the forensic flag
    n_for = counts.get("forensic", 0)
    cand = [n_for, n_for + 1, n_for - 1, n_for + 2, n_for - 2, n_for + 3]
    cand = [c for c in cand if 0 <= c <= len(found)]
    cand = list(dict.fromkeys(cand))
    if len(cand) >= 3:
        opts, ci = _options(str(n_for), [str(c) for c in cand if c != n_for], rng)
        qs.append({"tag": "COUNT", "prompt": "How many of your recovered items are flagged FORENSIC?",
                   "options": opts, "correct": ci,
                   "explain": f"{n_for} item(s) have forensic = 1 in evidence.csv.", "math": []})

    # 4. Vector maths: most similar item (cosine similarity)
    if sim is not None and len(found) >= 4:
        data = {e["id"]: [float(x) for x in e["vector"]] for e in found}
        for ref in found:
            scores = []
            for e in found:
                if e["id"] == ref["id"]:
                    continue
                cs = sim.cosine_similarity(data[ref["id"]], data[e["id"]])
                if cs is not None:
                    scores.append((cs, e))
            if len(scores) < 3:
                continue
            scores.sort(key=lambda t: -t[0])
            if scores[0][0] - scores[1][0] < 1e-9:
                continue                       # need a unique best match
            lower = [s for s in scores[1:] if s[0] < scores[0][0] - 1e-9]
            rng.shuffle(lower)
            picks = [scores[0]] + lower[:3]
            if len(picks) < 3:
                continue
            label = lambda e: f"{e['id']}  -  {e['description'][:46]}{'...' if len(e['description']) > 46 else ''}"
            opts_t = [label(p[1]) for p in picks]
            rng.shuffle(opts_t)
            ci = opts_t.index(label(picks[0][1]))
            math_lines = []
            for cs, e in sorted(picks, key=lambda t: -t[0]):
                a, b = data[ref["id"]], data[e["id"]]
                math_lines.append(f"{ref['id']} . {e['id']}: dot={sim.dot_product(a, b):g}  "
                                  f"|A|={sim.vector_magnitude(a):.3f}  |B|={sim.vector_magnitude(b):.3f}  cos={cs:.3f}")
            qs.append({"tag": "VECTOR MATHS",
                       "prompt": f"Compare feature patterns (0/1 vectors, cosine similarity). Which item is MOST similar to {ref['id']}?",
                       "sub": ref["description"], "options": opts_t, "correct": ci,
                       "explain": f"{picks[0][1]['id']} has the highest cosine similarity ({picks[0][0]:.3f}) to {ref['id']}. "
                                  "Similarity compares encoded flags only.",
                       "math": math_lines})
            break

    # 5. Final conclusion
    subjects = []
    for c in all_cases:
        if c["subject"] and c["subject"] not in subjects:
            subjects.append(c["subject"])
    if case["subject"] and len(subjects) >= 2:
        others = [s for s in subjects if s != case["subject"]]
        rng.shuffle(others)
        opts, ci = _options(case["subject"], others[:3], rng)
        qs.append({"tag": "FINAL CONCLUSION", "final": True,
                   "prompt": "Close the file. Based on the evidence you recovered, who is the primary subject of this investigation?",
                   "options": opts, "correct": ci,
                   "explain": f"The case file records the primary subject as {case['subject']}. "
                              f"Legal outcome (cases.csv): {case['outcome'] or 'not recorded'}.",
                   "math": []})
    return qs