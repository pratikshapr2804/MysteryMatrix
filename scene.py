"""
scene.py - the searchable scene.

IMPORTANT (honesty): this is a stylised search room. The hiding places are
generic furniture and the placement of each item is random (seeded by case id).
It is NOT a reconstruction of any real crime scene. What the player finds
(the evidence descriptions) comes straight from evidence.csv.
"""
import math
import random
import pygame
from ui import W, H, shadow, txt, F, AMBER, WHITE, GREEN, MUTED, RED_L, PAPER, lerp

# key, label, rect  (rects are in the 1180x760 design space)
SPOTS = [
    ("cork",    "Behind the corkboard",   (210, 105, 220, 130)),
    ("paint",   "Behind the painting",    (740, 100, 110, 90)),
    ("shelf1",  "Bookshelf (upper row)",  (512, 150, 176, 55)),
    ("shelf2",  "Bookshelf (lower row)",  (512, 250, 176, 55)),
    ("safe",    "Wall safe",              (900, 140, 110, 90)),
    ("cab1",    "Filing cabinet (top)",   (770, 255, 90, 55)),
    ("cab2",    "Filing cabinet (middle)", (770, 318, 90, 52)),
    ("papers",  "Papers on the desk",     (180, 306, 150, 26)),
    ("drawer",  "Desk drawer",            (330, 365, 110, 45)),
    ("coat",    "Coat pocket",            (45, 190, 80, 150)),
    ("crate1",  "Top crate",              (930, 355, 160, 50)),
    ("crate2",  "Lower crate",            (930, 405, 160, 50)),
    ("table",   "Side table",             (55, 498, 110, 80)),
    ("rug",     "Under the rug",          (390, 520, 320, 100)),
    ("bin",     "Waste bin",              (1030, 500, 80, 100)),
]

SEARCH_TIME = 0.8
_room_cache = {}


def _planks(s):
    rng = random.Random(5)
    pygame.draw.rect(s, (74, 55, 40), (0, 440, W, 230))
    y = 440
    while y < 670:
        pygame.draw.line(s, (56, 41, 30), (0, y), (W, y), 2)
        x = rng.randint(0, 120)
        while x < W:
            pygame.draw.line(s, (60, 44, 32), (x, y), (x, min(y + 46, 670)), 1)
            x += rng.randint(140, 260)
        y += 46


def render_room():
    if "bg" in _room_cache:
        return _room_cache["bg"]
    s = pygame.Surface((W, H))
    s.fill((10, 12, 16))
    # wall
    pygame.draw.rect(s, (46, 52, 62), (0, 60, W, 380))
    for x in range(0, W, 44):
        pygame.draw.line(s, (42, 48, 57), (x, 60), (x, 330), 2)
    pygame.draw.rect(s, (35, 40, 48), (0, 330, W, 110))
    pygame.draw.line(s, (90, 80, 62), (0, 330), (W, 330), 3)
    for x in range(0, W, 110):
        pygame.draw.rect(s, (31, 35, 43), (x + 8, 346, 94, 82), 2)
    _planks(s)
    pygame.draw.rect(s, (30, 22, 17), (0, 436, W, 8))
    # rug
    pygame.draw.rect(s, (104, 40, 38), (390, 520, 320, 100))
    pygame.draw.rect(s, (160, 118, 64), (390, 520, 320, 100), 4)
    pygame.draw.rect(s, (160, 118, 64), (408, 536, 284, 68), 2)
    # coat rack + coat
    pygame.draw.rect(s, (52, 38, 28), (80, 130, 8, 335))
    pygame.draw.rect(s, (52, 38, 28), (55, 458, 60, 9))
    pygame.draw.polygon(s, (66, 58, 52), [(50, 200), (118, 200), (126, 335), (44, 335)])
    pygame.draw.polygon(s, (82, 72, 64), [(50, 200), (84, 218), (118, 200), (104, 190), (66, 190)])
    pygame.draw.rect(s, (48, 42, 38), (60, 280, 28, 22), 2)
    # side table
    shadow(s, (50, 568, 125, 18))
    pygame.draw.rect(s, (96, 70, 46), (55, 498, 110, 12))
    for x in (62, 148):
        pygame.draw.rect(s, (80, 58, 38), (x, 510, 8, 70))
    pygame.draw.rect(s, (70, 50, 34), (62, 540, 96, 6))
    pygame.draw.rect(s, (214, 196, 150), (80, 480, 28, 18))
    # corkboard
    pygame.draw.rect(s, (92, 64, 40), (204, 99, 232, 142))
    pygame.draw.rect(s, (168, 126, 84), (210, 105, 220, 130))
    for (x, y, w, h, c) in [(226, 120, 50, 38, (236, 230, 210)), (300, 124, 44, 52, (240, 214, 120)),
                            (360, 118, 52, 40, (230, 226, 208)), (240, 176, 56, 44, (210, 224, 230)),
                            (330, 188, 70, 34, (236, 230, 210))]:
        pygame.draw.rect(s, c, (x, y, w, h))
        pygame.draw.circle(s, (176, 52, 44), (x + w // 2, y + 5), 3)
    pygame.draw.lines(s, (150, 40, 36), False, [(252, 125), (322, 150), (386, 124), (358, 205)], 2)
    # painting
    pygame.draw.rect(s, (150, 118, 52), (734, 94, 122, 102))
    pygame.draw.rect(s, (30, 56, 66), (742, 102, 106, 86))
    pygame.draw.polygon(s, (60, 100, 104), [(742, 188), (790, 126), (848, 188)])
    pygame.draw.circle(s, (200, 180, 120), (820, 128), 12)
    # bookshelf
    pygame.draw.rect(s, (62, 42, 28), (494, 94, 212, 342))
    pygame.draw.rect(s, (36, 26, 20), (504, 104, 192, 322))
    rng = random.Random(11)
    for board in (205, 305, 405):
        pygame.draw.rect(s, (86, 60, 40), (498, board, 204, 8))
        x = 510
        while x < 686:
            bw = rng.randint(10, 22)
            bh = rng.randint(34, 62) if board != 405 else rng.randint(30, 50)
            col = rng.choice([(110, 48, 44), (52, 84, 100), (88, 96, 60), (120, 96, 56), (70, 60, 90)])
            pygame.draw.rect(s, col, (x, board - bh, bw, bh))
            pygame.draw.line(s, lerp(col, (0, 0, 0), .4), (x + 3, board - bh + 6), (x + 3, board - 6), 1)
            x += bw + 2
    # safe
    pygame.draw.rect(s, (28, 30, 34), (894, 134, 122, 102))
    pygame.draw.rect(s, (68, 72, 80), (900, 140, 110, 90))
    pygame.draw.circle(s, (40, 42, 48), (955, 185), 28)
    pygame.draw.circle(s, (120, 124, 132), (955, 185), 22, 3)
    pygame.draw.line(s, (200, 200, 200), (955, 185), (966, 172), 3)
    pygame.draw.rect(s, (130, 134, 140), (984, 175, 10, 30))
    # filing cabinet
    shadow(s, (752, 428, 130, 22))
    pygame.draw.rect(s, (60, 66, 72), (760, 240, 110, 200))
    for i, y in enumerate((248, 312, 376)):
        pygame.draw.rect(s, (96, 106, 114), (766, y, 98, 58))
        pygame.draw.rect(s, (60, 66, 72), (766, y, 98, 58), 2)
        pygame.draw.rect(s, (170, 174, 180), (800, y + 38, 30, 8), border_radius=3)
        pygame.draw.rect(s, (214, 196, 150), (806, y + 12, 18, 12))
    # crates
    shadow(s, (912, 448, 200, 22))
    for y in (355, 405):
        pygame.draw.rect(s, (112, 82, 50), (930, y, 160, 50))
        pygame.draw.rect(s, (70, 50, 30), (930, y, 160, 50), 3)
        pygame.draw.line(s, (80, 58, 36), (930, y), (1090, y + 50), 3)
        pygame.draw.line(s, (80, 58, 36), (1090, y), (930, y + 50), 3)
    # desk
    shadow(s, (140, 450, 350, 24))
    pygame.draw.rect(s, (74, 52, 34), (160, 352, 300, 110))
    pygame.draw.rect(s, (112, 80, 52), (150, 330, 320, 22))
    pygame.draw.rect(s, (84, 60, 40), (170, 362, 130, 40))
    pygame.draw.rect(s, (84, 60, 40), (330, 365, 110, 45))
    pygame.draw.rect(s, (60, 42, 28), (330, 365, 110, 45), 2)
    pygame.draw.circle(s, (190, 150, 80), (385, 388), 5)
    pygame.draw.circle(s, (190, 150, 80), (235, 382), 5)
    pygame.draw.rect(s, (214, 202, 168), (180, 314, 66, 16))
    pygame.draw.rect(s, (226, 214, 176), (196, 308, 60, 18))
    pygame.draw.rect(s, (188, 168, 128), (262, 310, 56, 20))
    pygame.draw.rect(s, (160, 160, 150), (420, 318, 18, 12))      # mug
    pygame.draw.rect(s, (40, 40, 44), (430, 322, 34, 8))          # lamp base
    pygame.draw.lines(s, (40, 40, 44), False, [(446, 322), (440, 292), (458, 270)], 3)
    pygame.draw.polygon(s, (30, 90, 70), [(448, 262), (480, 270), (462, 288)])
    # bin
    shadow(s, (1020, 590, 100, 14))
    pygame.draw.polygon(s, (88, 92, 98), [(1030, 500), (1110, 500), (1102, 600), (1038, 600)])
    for x in (1050, 1070, 1090):
        pygame.draw.line(s, (60, 64, 70), (x, 506), (x - 2 if x < 1070 else x + 2, 596), 2)
    pygame.draw.ellipse(s, (60, 64, 70), (1026, 494, 88, 14), 3)
    for (x, y) in ((1060, 492), (1082, 488), (1044, 490)):
        pygame.draw.circle(s, (210, 200, 176), (x, y), 7)
    _room_cache["bg"] = s
    return s


_light_cache = {}


def light_mask(radius=190, alpha=212):
    key = (radius, alpha)
    if key not in _light_cache:
        g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -3):
            a = int(alpha * (1 - r / radius) ** 0.65)
            pygame.draw.circle(g, (0, 0, 0, a), (radius, radius), r)
        _light_cache[key] = g
    return _light_cache[key]


class Scene:
    def __init__(self, case_id, items):
        rng = random.Random("scene-" + case_id)
        self.rng = rng
        self.spots = [{"key": k, "label": l, "rect": pygame.Rect(r), "items": [], "searched": False, "mark": None}
                      for k, l, r in SPOTS]
        order = list(range(len(self.spots)))
        rng.shuffle(order)
        for n, it in enumerate(items):
            self.spots[order[n % len(order)]]["items"].append(it)
        self.total = len(items)
        self.found = []
        self.search = None            # {"spot":..., "t":0}
        self.hints_left = 3
        self.hints_used = 0
        self.hint = None              # {"spot":..., "t":..}
        self.lights = False
        self.searches = 0
        self.dark = None

    @property
    def complete(self):
        return len(self.found) >= self.total

    def spot_at(self, pos):
        for sp in reversed(self.spots):
            if sp["rect"].collidepoint(pos):
                return sp
        return None

    def click(self, pos):
        """Returns a message string (or None)."""
        if self.search or self.complete:
            return None
        sp = self.spot_at(pos)
        if not sp:
            return None
        if sp["searched"]:
            return "You already searched here."
        self.search = {"spot": sp, "t": 0.0}
        self.searches += 1
        return None

    def use_hint(self):
        if self.hints_left <= 0 or self.complete or self.search:
            return False
        cands = [s for s in self.spots if s["items"] and not s["searched"]]
        if not cands:
            return False
        self.hint = {"spot": self.rng.choice(cands), "t": 5.0}
        self.hints_left -= 1
        self.hints_used += 1
        return True

    def update(self, dt):
        if self.hint:
            self.hint["t"] -= dt
            if self.hint["t"] <= 0:
                self.hint = None
        if self.search:
            self.search["t"] += dt
            if self.search["t"] >= SEARCH_TIME:
                sp = self.search["spot"]
                self.search = None
                if self.hint and self.hint["spot"] is sp:
                    self.hint = None
                if sp["items"]:
                    item = sp["items"].pop(0)
                    self.found.append(item)
                    sp["searched"] = not sp["items"]
                    sp["mark"] = "found"
                    return ("found", item)
                sp["searched"] = True
                sp["mark"] = "empty"
                return ("empty", sp)
        return None

    # ------------------------------------------------------------ drawing
    def draw(self, surf, mouse, t):
        surf.blit(render_room(), (0, 0))
        if not self.lights:
            if self.dark is None:
                self.dark = pygame.Surface((W, H), pygame.SRCALPHA)
            self.dark.fill((4, 6, 10, 192))
            m = light_mask()
            self.dark.blit(m, (mouse[0] - m.get_width() // 2, mouse[1] - m.get_height() // 2),
                           special_flags=pygame.BLEND_RGBA_SUB)
            surf.blit(self.dark, (0, 0))
        # markers
        for sp in self.spots:
            r = sp["rect"]
            if sp["mark"] == "found":
                pygame.draw.circle(surf, GREEN, (r.right - 14, r.y + 14), 11)
                pygame.draw.lines(surf, (10, 30, 14), False, [(r.right - 20, r.y + 14), (r.right - 15, r.y + 19), (r.right - 8, r.y + 9)], 3)
            elif sp["mark"] == "empty":
                pygame.draw.circle(surf, (60, 58, 56), (r.right - 14, r.y + 14), 11)
                pygame.draw.line(surf, MUTED, (r.right - 19, r.y + 9), (r.right - 9, r.y + 19), 2)
                pygame.draw.line(surf, MUTED, (r.right - 9, r.y + 9), (r.right - 19, r.y + 19), 2)
        # hint pulse
        if self.hint:
            r = self.hint["spot"]["rect"].inflate(14, 14)
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            pygame.draw.rect(surf, lerp((120, 80, 30), AMBER, pulse), r, 3, border_radius=6)
        # hover
        sp = self.spot_at(mouse) if not self.search else None
        if sp and not sp["searched"]:
            pygame.draw.rect(surf, AMBER, sp["rect"].inflate(6, 6), 2, border_radius=5)
            lab = F["smallb"].render(sp["label"], True, WHITE)
            bx = max(8, min(W - lab.get_width() - 24, mouse[0] + 16))
            by = max(70, mouse[1] - 40)
            pygame.draw.rect(surf, (20, 22, 28), (bx, by, lab.get_width() + 16, 26), border_radius=4)
            pygame.draw.rect(surf, AMBER, (bx, by, lab.get_width() + 16, 26), 1, border_radius=4)
            surf.blit(lab, (bx + 8, by + 4))
        elif sp and sp["searched"]:
            lab = F["small"].render("searched", True, MUTED)
            surf.blit(lab, (mouse[0] + 14, mouse[1] - 30))
        # search progress ring
        if self.search:
            r = self.search["spot"]["rect"]
            prog = self.search["t"] / SEARCH_TIME
            pygame.draw.rect(surf, (20, 22, 28), (r.centerx - 70, r.centery - 14, 140, 28), border_radius=6)
            pygame.draw.rect(surf, AMBER, (r.centerx - 66, r.centery - 10, int(132 * prog), 20), border_radius=4)
            txt(surf, "SEARCHING...", (r.centerx, r.centery - 30), F["mono_s"], WHITE, "center")
        # magnifier cursor
        mx, my = mouse
        pygame.draw.circle(surf, AMBER, (mx, my), 11, 2)
        pygame.draw.line(surf, AMBER, (mx + 8, my + 8), (mx + 17, my + 17), 3)