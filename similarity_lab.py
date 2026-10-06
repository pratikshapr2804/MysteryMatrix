"""
similarity_lab.py  -  Member 4: Similarity Lab screen (Pygame)

Run on its own :   python similarity_lab.py
Plug into game.py: see the integration snippet at the bottom of this file.

Controls
  Mouse click / Arrow keys : choose a cell of the heatmap (row case vs column case)
  Tab or B                 : switch Count <-> Binary representation
  Esc                      : back (returns "back" to the caller)
"""

import pygame
import similarity as sim

# ---- archival palette ---------------------------------------------------
BG = (22, 20, 18)
PANEL = (34, 31, 28)
PAPER = (226, 214, 188)
INK = (40, 32, 24)
MUTED = (150, 140, 124)
AMBER = (212, 160, 64)
STAMP = (170, 58, 48)
CELL_LOW = (45, 40, 36)


# display-only short labels for the heatmap (unknown ids fall back to cases.csv)
DISPLAY_ALIASES = {"C02": "GSK", "C03": "Unabomber", "C04": "OKC", "C05": "Madoff"}


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def wrap_text(text, font, max_w):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class SimilarityLab:
    def __init__(self, evidence_path="evidence.csv", cases_path="cases.csv"):
        self.evidence_path = evidence_path
        self.cases_path = cases_path
        self.representation = "count"
        self.row = 0
        self.col = 1
        self.error = None
        self.matrices = {}
        self.ids = []
        self.names = {}
        self.sim_matrix = []
        self.cell_rects = {}
        self._fonts = None
        self.reload()

    # ---- data -----------------------------------------------------------
    def reload(self):
        try:
            counts = sim.build_case_matrix(self.evidence_path)
            self.matrices = {"count": counts,
                             "binary": sim.to_binary_matrix(counts)}
            self.names = sim.load_case_names(self.cases_path)
            self._recompute()
            self.error = None
        except (OSError, ValueError) as exc:
            self.error = str(exc)

    def _recompute(self):
        self.ids, self.sim_matrix = sim.calculate_similarity_matrix(
            self.matrices[self.representation])
        n = len(self.ids)
        self.row = min(self.row, n - 1)
        self.col = min(self.col, n - 1)

    def label(self, cid):
        return DISPLAY_ALIASES.get(cid) or sim.short_name(self.names.get(cid, cid))

    def toggle_representation(self):
        self.representation = "binary" if self.representation == "count" else "count"
        self._recompute()

    # ---- events ---------------------------------------------------------
    def handle_event(self, event):
        """Returns "back" when the player leaves the lab, otherwise None."""
        if self.error:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reload()
                elif event.key == pygame.K_ESCAPE:
                    return "back"
            return None
        n = len(self.ids)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key in (pygame.K_TAB, pygame.K_b):
                self.toggle_representation()
            elif event.key == pygame.K_LEFT:
                self.col = (self.col - 1) % n
            elif event.key == pygame.K_RIGHT:
                self.col = (self.col + 1) % n
            elif event.key == pygame.K_UP:
                self.row = (self.row - 1) % n
            elif event.key == pygame.K_DOWN:
                self.row = (self.row + 1) % n
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for (r, c), rect in self.cell_rects.items():
                if rect.collidepoint(event.pos):
                    self.row, self.col = r, c
        return None

    # ---- drawing --------------------------------------------------------
    def _load_fonts(self):
        def pick(names, size, bold=False):
            return pygame.font.SysFont(names, size, bold=bold)
        serif = "georgia,palatinolinotype,timesnewroman,serif"
        mono = "consolas,couriernew,monospace"
        self._fonts = {
            "title": pick(serif, 30, True),
            "h": pick(serif, 20, True),
            "body": pick(serif, 16),
            "small": pick(serif, 13),
            "mono": pick(mono, 16),
            "monob": pick(mono, 17, True),
        }

    def draw(self, surf):
        if self._fonts is None:
            self._load_fonts()
        f = self._fonts
        W, H = surf.get_size()
        surf.fill(BG)
        surf.blit(f["title"].render("FORENSICS LAB  /  SIMILARITY ANALYSIS",
                                    True, PAPER), (40, 24))

        if self.error:
            self._draw_error(surf, f)
            return

        rep_txt = ("COUNT vectors: how many evidence rows carry each feature"
                   if self.representation == "count" else
                   "BINARY vectors: is each feature present at least once?")
        surf.blit(f["body"].render(rep_txt, True, AMBER), (40, 66))
        surf.blit(f["small"].render(
            "Tab = switch representation   |   Arrows / click = choose pair"
            "   |   Esc = back", True, MUTED), (40, 90))

        self._draw_heatmap(surf, f, 40, 130)
        self._draw_detail(surf, f, 640, 120, W - 640 - 30, H - 120 - 20)

    def _draw_error(self, surf, f):
        pygame.draw.rect(surf, PAPER, (40, 110, 700, 200), border_radius=4)
        surf.blit(f["h"].render("Could not load the dataset", True, STAMP), (60, 130))
        for i, line in enumerate(wrap_text(self.error, f["body"], 660)):
            surf.blit(f["body"].render(line, True, INK), (60, 170 + i * 22))
        surf.blit(f["small"].render("Press R to retry, Esc to go back.",
                                    True, INK), (60, 280))

    def _draw_heatmap(self, surf, f, x0, y0):
        n = len(self.ids)
        label_w, cell = 70, 100
        cell = min(cell, 480 // max(n, 1))
        self.cell_rects = {}
        surf.blit(f["h"].render("Pairwise cosine similarity", True, PAPER),
                  (x0, y0 - 6))
        top = y0 + 40
        for c, cid in enumerate(self.ids):
            t = f["small"].render(self.label(cid)[:9], True,
                                  AMBER if c == self.col else MUTED)
            surf.blit(t, (x0 + label_w + c * cell + (cell - t.get_width()) // 2,
                          top - 20))
        mouse = pygame.mouse.get_pos()
        for r, rid in enumerate(self.ids):
            t = f["small"].render(self.label(rid)[:9], True,
                                  AMBER if r == self.row else MUTED)
            surf.blit(t, (x0, top + r * cell + (cell - t.get_height()) // 2))
            for c in range(n):
                rect = pygame.Rect(x0 + label_w + c * cell, top + r * cell,
                                   cell - 3, cell - 3)
                self.cell_rects[(r, c)] = rect
                v = self.sim_matrix[r][c]
                color = CELL_LOW if v is None else lerp(CELL_LOW, AMBER, v ** 2)
                pygame.draw.rect(surf, color, rect, border_radius=3)
                if rect.collidepoint(mouse):
                    pygame.draw.rect(surf, PAPER, rect, 1, border_radius=3)
                if (r, c) == (self.row, self.col):
                    pygame.draw.rect(surf, STAMP, rect, 3, border_radius=3)
                txt = "n/a" if v is None else f"{v:.2f}"
                tc = INK if (v or 0) > 0.78 else PAPER
                ts = f["mono"].render(txt, True, tc)
                surf.blit(ts, ts.get_rect(center=rect.center))
        # colour key
        ky = top + n * cell + 12
        surf.blit(f["small"].render("0.0", True, MUTED), (x0 + label_w, ky))
        for i in range(200):
            pygame.draw.line(surf, lerp(CELL_LOW, AMBER, (i / 199) ** 2),
                             (x0 + label_w + 30 + i, ky + 2),
                             (x0 + label_w + 30 + i, ky + 14))
        surf.blit(f["small"].render("1.0", True, MUTED),
                  (x0 + label_w + 238, ky))

    def _draw_detail(self, surf, f, x, y, w, h):
        pygame.draw.rect(surf, PAPER, (x, y, w, h), border_radius=4)
        id_a, id_b = self.ids[self.row], self.ids[self.col]
        data = self.matrices[self.representation]
        r = sim.compare_cases(data, id_a, id_b)
        px, py = x + 20, y + 14
        head = f"{self.label(id_a)}  vs  {self.label(id_b)}"
        surf.blit(f["h"].render(head, True, INK), (px, py))
        py += 30

        # table
        cols = [px, px + 150, px + 215, px + 280]
        for cx, name in zip(cols, ["feature", "A", "B", "A x B"]):
            surf.blit(f["small"].render(name, True, STAMP), (cx, py))
        py += 20
        pygame.draw.line(surf, INK, (px, py), (x + w - 20, py), 1)
        py += 4
        for i, name in enumerate(sim.FEATURE_COLUMNS):
            a, b, p = r["vector_a"][i], r["vector_b"][i], r["products"][i]
            font = f["monob"] if p > 0 else f["mono"]
            col = INK if p > 0 else MUTED
            for cx, val in zip(cols, [name, a, b, p]):
                surf.blit(font.render(str(val), True, col), (cx, py))
            py += 21
        pygame.draw.line(surf, INK, (px, py), (x + w - 20, py), 1)
        py += 6

        def fmt(v):
            return f"{v:g}"
        lines = [
            f"dot product  A.B = {fmt(r['dot'])}",
            f"||A|| = {r['mag_a']:.4f}      ||B|| = {r['mag_b']:.4f}",
        ]
        for ln in lines:
            surf.blit(f["monob"].render(ln, True, INK), (px, py))
            py += 22
        if r["cosine"] is None:
            formula = "cos = A.B / (||A|| ||B||)  ->  undefined (zero vector)"
        else:
            formula = (f"cos = {fmt(r['dot'])} / ({r['mag_a']:.4f} x "
                       f"{r['mag_b']:.4f}) = {r['cosine']:.4f}")
        surf.blit(f["mono"].render(formula, True, STAMP), (px, py))
        py += 28

        for ln in wrap_text(sim.interpret_similarity(r["cosine"]),
                            f["body"], w - 40):
            surf.blit(f["body"].render(ln, True, INK), (px, py))
            py += 20
        py += 6
        shared = sim.shared_features(data, id_a, id_b)[:3]
        if shared and id_a != id_b:
            txt = "Biggest contributors to the dot product: " + ", ".join(
                f"{n} ({p})" for n, _, _, p in shared)
            for ln in wrap_text(txt, f["small"], w - 40):
                surf.blit(f["small"].render(ln, True, INK), (px, py))
                py += 17
        # disclaimer pinned to the bottom of the sheet
        dl = wrap_text("NOTE: " + sim.DISCLAIMER, f["small"], w - 40)
        by = y + h - 12 - len(dl) * 16
        for i, ln in enumerate(dl):
            surf.blit(f["small"].render(ln, True, STAMP), (px, by + i * 16))


# ---- standalone runner ------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((1100, 720))
    pygame.display.set_caption("Mystery Matrix - Similarity Lab")
    clock = pygame.time.Clock()
    lab = SimilarityLab()
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

# ---------------------------------------------------------------------------
# INTEGRATION SNIPPET for game.py  (add these few lines; nothing else changes)
#
#   try:
#       from similarity_lab import SimilarityLab
#   except Exception as e:                  # lab missing or broken -> game still runs
#       SimilarityLab = None
#       print("Similarity lab unavailable:", e)
#
#   # when the player opens the lab (e.g. from the Forensics screen):
#   lab = SimilarityLab() if SimilarityLab else None
#   state = "similarity"
#
#   # in the event loop:
#   if state == "similarity" and lab:
#       if lab.handle_event(event) == "back":
#           state = "forensics"             # or whatever your previous screen is
#
#   # in the draw section:
#   if state == "similarity" and lab:
#       lab.draw(screen)
# ---------------------------------------------------------------------------