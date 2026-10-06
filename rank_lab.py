"""
rank_lab.py  -  Member 3: Rank / Pivots Lab screen (Pygame)

Run on its own :   python rank_lab.py
Math comes from data_rank_analysis.py and rank_analysis.py (do not edit those).

Controls
  Mouse click / Arrow keys : choose a case (or FULL dataset)
  Esc                      : back (returns "back" to the caller)
"""
import pygame

from data_rank_analysis import (
    FEATURE_NAMES,
    load_evidence,
    build_matrix,
    split_matrix_by_case,
    calculate_rref_rank_pivots,
    get_pivot_features,
)
from rank_analysis import calculate_rank_from_rref, find_pivot_columns

BG = (22, 20, 18)
PANEL = (34, 31, 28)
PAPER = (226, 214, 188)
INK = (40, 32, 24)
MUTED = (150, 140, 124)
AMBER = (212, 160, 64)
STAMP = (170, 58, 48)
CELL_OFF = (45, 40, 36)
CELL_ON = (176, 52, 44)

DISPLAY_ALIASES = {
    "FULL": "Full dataset",
    "C01": "BTK",
    "C02": "GSK",
    "C03": "Unabomber",
    "C04": "OKC",
    "C05": "Madoff",
}

DISCLAIMER = (
    "Rank measures independent evidence-flag directions in the encoded matrix. "
    "It does not reconstruct a crime and it does not prove anyone's guilt."
)


def wrap_text(text, font, max_w):
    lines, line = [], ""
    for word in str(text).split():
        test = (line + " " + word).strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _cell(value):
    try:
        v = float(value)
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.2f}"
    except Exception:
        return str(value)


def _rref_numeric(rref_matrix):
    try:
        raw = rref_matrix.tolist()
    except Exception:
        raw = list(rref_matrix)
    numeric = []
    for row in raw:
        nums = []
        for v in row:
            try:
                nums.append(float(v))
            except Exception:
                nums.append(0.0)
        numeric.append(nums)
    return numeric


def interpret_rank(rank, rows, cols, pivot_features):
    max_rank = min(rows, cols)
    free = [f for f in FEATURE_NAMES if f not in pivot_features]
    lines = [
        f"Rank {rank} means there are {rank} linearly independent columns "
        f"(independent evidence-flag directions).",
        f"Maximum possible rank is min({rows} rows, {cols} columns) = {max_rank}.",
    ]
    if rank == max_rank:
        lines.append("This matrix is full rank: the pivot columns are independent.")
    else:
        lines.append(
            f"Rank is {max_rank - rank} below the maximum, so some feature columns "
            "are linear combinations of others."
        )
    if pivot_features:
        lines.append("Pivot (independent) features: " + ", ".join(pivot_features) + ".")
    if free:
        lines.append("Dependent / free features: " + ", ".join(free) + ".")
    else:
        lines.append("Every feature column is a pivot in this matrix.")
    return lines


class RankLab:
    def __init__(self, evidence_path="evidence.csv"):
        self.evidence_path = evidence_path
        self.error = None
        self.results = []
        self.sel = 0
        self.row_rects = {}
        self._fonts = None
        self.reload()

    def reload(self):
        try:
            evidence = load_evidence(self.evidence_path)
            full = build_matrix(evidence)
            cases = split_matrix_by_case(evidence)
            self.results = [self._analyse("FULL", full)]
            for cid in sorted(cases):
                self.results.append(self._analyse(cid, cases[cid]))
            if self.results:
                self.sel = min(self.sel, len(self.results) - 1)
            self.error = None
        except Exception as exc:
            self.error = str(exc)
            self.results = []

    def _analyse(self, case_id, matrix):
        rref, rank, pivot_columns = calculate_rref_rank_pivots(matrix)
        numeric = _rref_numeric(rref)
        pivot_list = [int(p) for p in pivot_columns]
        features = get_pivot_features(pivot_list)
        rows = len(matrix)
        cols = len(matrix[0]) if matrix else 0
        return {
            "case_id": case_id,
            "rows": rows,
            "columns": cols,
            "rank": int(rank),
            "rank_from_rref": calculate_rank_from_rref(numeric),
            "pivot_columns": pivot_list,
            "pivot_features": features,
            "free_features": [f for f in FEATURE_NAMES if f not in features],
            "rref": [[_cell(v) for v in row] for row in numeric],
        }

    def select_case(self, cid):
        for i, row in enumerate(self.results):
            if row["case_id"] == cid:
                self.sel = i
                return

    def current(self):
        if not self.results:
            return None
        return self.results[self.sel]

    def handle_event(self, event):
        if self.error:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reload()
                elif event.key == pygame.K_ESCAPE:
                    return "back"
            return None
        n = len(self.results)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key in (pygame.K_DOWN, pygame.K_RIGHT) and n:
                self.sel = (self.sel + 1) % n
            elif event.key in (pygame.K_UP, pygame.K_LEFT) and n:
                self.sel = (self.sel - 1) % n
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = i
        return None

    def _load_fonts(self):
        def pick(names, size, bold=False):
            return pygame.font.SysFont(names, size, bold=bold)
        serif = "georgia,palatinolinotype,timesnewroman,serif"
        mono = "consolas,couriernew,monospace"
        self._fonts = {
            "title": pick(serif, 30, True),
            "h": pick(serif, 20, True),
            "h2": pick(serif, 42, True),
            "body": pick(serif, 16),
            "small": pick(serif, 13),
            "mono": pick(mono, 15),
            "monob": pick(mono, 16, True),
        }

    def draw(self, surf):
        if self._fonts is None:
            self._load_fonts()
        f = self._fonts
        W, H = surf.get_size()
        surf.fill(BG)
        surf.blit(f["title"].render("FORENSICS LAB  /  RANK AND PIVOTS", True, PAPER), (40, 22))
        if self.error:
            self._draw_error(surf, f)
            return
        surf.blit(f["body"].render(
            "Rank = number of independent feature columns after RREF.", True, AMBER), (40, 62))
        surf.blit(f["small"].render(
            "Arrows / click = choose case    |    Esc = back", True, MUTED), (40, 88))
        self._draw_list(surf, f, 40, 118, 280, H - 148)
        self._draw_detail(surf, f, 340, 118, W - 370, H - 148)

    def _draw_error(self, surf, f):
        pygame.draw.rect(surf, PAPER, (40, 110, 720, 210), border_radius=4)
        surf.blit(f["h"].render("Could not load rank analysis", True, STAMP), (60, 130))
        for i, line in enumerate(wrap_text(self.error, f["body"], 680)):
            surf.blit(f["body"].render(line, True, INK), (60, 170 + i * 22))
        surf.blit(f["small"].render(
            "Need sympy installed. Press R to retry, Esc to go back.", True, INK), (60, 280))

    def _draw_list(self, surf, f, x, y, w, h):
        pygame.draw.rect(surf, PANEL, (x, y, w, h), border_radius=6)
        pygame.draw.rect(surf, (74, 68, 56), (x, y, w, h), 1, border_radius=6)
        surf.blit(f["monob"].render("CASES", True, AMBER), (x + 14, y + 12))
        self.row_rects = {}
        row_h = min(52, max(36, (h - 48) // max(1, len(self.results))))
        mouse = pygame.mouse.get_pos()
        for i, row in enumerate(self.results):
            rr = pygame.Rect(x + 10, y + 42 + i * row_h, w - 20, row_h - 6)
            self.row_rects[i] = rr
            sel = i == self.sel
            hover = rr.collidepoint(mouse)
            fill = STAMP if sel else ((50, 46, 42) if hover else (40, 37, 34))
            pygame.draw.rect(surf, fill, rr, border_radius=4)
            pygame.draw.rect(surf, AMBER if sel else (70, 64, 56), rr, 1, border_radius=4)
            cid = row["case_id"]
            name = DISPLAY_ALIASES.get(cid, cid)
            surf.blit(f["monob"].render(cid, True, PAPER), (rr.x + 10, rr.y + 6))
            surf.blit(f["small"].render(
                f"{name}   rank {row['rank']}", True, PAPER if sel else MUTED),
                (rr.x + 10, rr.y + 24))

    def _draw_detail(self, surf, f, x, y, w, h):
        pygame.draw.rect(surf, PAPER, (x, y, w, h), border_radius=4)
        pygame.draw.rect(surf, (124, 100, 66), (x, y, w, h), 2, border_radius=4)
        row = self.current()
        if not row:
            return
        px, py = x + 22, y + 16
        cid = row["case_id"]
        title = DISPLAY_ALIASES.get(cid, cid)
        surf.blit(f["h"].render(f"{cid}  -  {title}", True, STAMP), (px, py))
        py += 36
        surf.blit(f["h2"].render(str(row["rank"]), True, STAMP), (px, py))
        surf.blit(f["body"].render("RANK", True, INK), (px + 90, py + 14))
        surf.blit(f["mono"].render(
            f"{row['rows']} x {row['columns']} matrix    max rank {min(row['rows'], row['columns'])}",
            True, INK), (px + 90, py + 38))
        py += 88
        surf.blit(f["monob"].render("PIVOT FEATURES (independent columns)", True, STAMP), (px, py))
        py += 26
        cx = px
        for name in row["pivot_features"] or ["(none)"]:
            label = name.upper()
            tw = f["small"].size(label)[0] + 16
            chip = pygame.Rect(cx, py, tw, 24)
            if chip.right > x + w - 24:
                cx = px
                py += 30
                chip = pygame.Rect(cx, py, tw, 24)
            pygame.draw.rect(surf, STAMP, chip, border_radius=4)
            surf.blit(f["small"].render(label, True, PAPER), (chip.x + 8, chip.y + 5))
            cx += tw + 8
        py += 36
        if row["free_features"]:
            surf.blit(f["monob"].render("DEPENDENT / FREE FEATURES", True, STAMP), (px, py))
            py += 22
            surf.blit(f["body"].render(", ".join(row["free_features"]), True, INK), (px, py))
            py += 28
        surf.blit(f["mono"].render(
            "pivot columns: " + (", ".join(str(c) for c in row["pivot_columns"]) or "(none)"),
            True, INK), (px, py))
        py += 26
        surf.blit(f["monob"].render("INTERPRETATION", True, STAMP), (px, py))
        py += 22
        for line in interpret_rank(row["rank"], row["rows"], row["columns"], row["pivot_features"]):
            for ln in wrap_text(line, f["body"], w - 48):
                surf.blit(f["body"].render(ln, True, INK), (px, py))
                py += 20
            py += 4
        py += 6
        surf.blit(f["monob"].render("RREF (preview)", True, STAMP), (px, py))
        py += 24
        rref = row["rref"][:8]
        if rref:
            cols = len(rref[0])
            cell = min(36, max(18, (w - 50) // max(1, cols)))
            for c, name in enumerate(FEATURE_NAMES[:cols]):
                t = f["small"].render(name[:4].upper(), True, MUTED)
                surf.blit(t, (px + c * cell + 2, py))
            py += 16
            for r in rref:
                for c, val in enumerate(r):
                    rr = pygame.Rect(px + c * cell, py, cell - 3, 22)
                    on = val not in ("0",)
                    pygame.draw.rect(surf, CELL_ON if on else CELL_OFF, rr, border_radius=2)
                    col = PAPER if on else MUTED
                    img = f["small"].render(val, True, col)
                    surf.blit(img, (rr.centerx - img.get_width() // 2, rr.y + 4))
                py += 24
        dl = wrap_text("NOTE: " + DISCLAIMER, f["small"], w - 48)
        by = y + h - 12 - len(dl) * 16
        for i, ln in enumerate(dl):
            surf.blit(f["small"].render(ln, True, STAMP), (px, by + i * 16))


def main():
    pygame.init()
    screen = pygame.display.set_mode((1180, 760), pygame.SCALED)
    pygame.display.set_caption("Mystery Matrix - Rank Lab")
    clock = pygame.time.Clock()
    lab = RankLab()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif lab.handle_event(event) == "back":
                running = False
        lab.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()