"""ui.py - shared fonts, colours, drawing helpers, icons and buttons."""
import math
import pygame

W, H = 1180, 760

BG = (13, 16, 22)
PANEL = (26, 30, 38)
PANEL_HI = (40, 46, 58)
LINE = (74, 68, 56)
PAPER = (232, 220, 190)
PAPER_D = (206, 190, 154)
INK = (38, 32, 25)
AMBER = (236, 178, 74)
RED = (176, 52, 44)
RED_L = (219, 88, 70)
TEAL = (84, 160, 158)
MUTED = (146, 140, 124)
WHITE = (246, 240, 224)
GREEN = (98, 172, 112)

F = {}


def init_fonts():
    serif = "georgia,palatinolinotype,timesnewroman,serif"
    mono = "couriernew,consolas,monospace"
    mk = lambda n, s, b=False: pygame.font.SysFont(n, s, bold=b)
    F.update({
        "huge": mk(serif, 92, True), "title": mk(serif, 54, True),
        "h1": mk(serif, 34, True), "h2": mk(serif, 24, True),
        "body": mk(serif, 19), "bodyb": mk(serif, 19, True),
        "small": mk(serif, 15), "smallb": mk(serif, 15, True),
        "mono": mk(mono, 17, True), "mono_s": mk(mono, 13, True),
        "type": mk(mono, 19, True),
    })


def txt(surf, s, pos, font, color, anchor="topleft"):
    img = font.render(str(s), True, color)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def wrap(s, font, width):
    lines, line = [], ""
    for word in str(s).split():
        t = (line + " " + word).strip()
        if font.size(t)[0] <= width:
            line = t
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def ellipsize(s, font, width):
    s = str(s)
    if font.size(s)[0] <= width:
        return s
    while s and font.size(s + "...")[0] > width:
        s = s[:-1]
    return s.rstrip() + "..."


def para(surf, s, x, y, width, font, color, gap=4, max_lines=None):
    lines = wrap(s, font, width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = ellipsize(lines[-1] + " ...", font, width)
    for ln in lines:
        txt(surf, ln, (x, y), font, color)
        y += font.get_linesize() + gap
    return y


def lerp(a, b, t):
    t = max(0, min(1, t))
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def shadow(surf, rect, alpha=90, grow=0):
    r = pygame.Rect(rect).inflate(grow, 0)
    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
    surf.blit(s, r.topleft)


def card(surf, rect, fill=PAPER, border=(124, 100, 66)):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, (0, 0, 0), r.move(6, 6))
    pygame.draw.rect(surf, fill, r)
    pygame.draw.rect(surf, border, r, 2)
    pygame.draw.line(surf, AMBER, (r.x + 10, r.y + 10), (r.x + 30, r.y + 10), 2)
    pygame.draw.line(surf, AMBER, (r.x + 10, r.y + 10), (r.x + 10, r.y + 30), 2)
    return r


def chip(surf, label, pos, on=True, font=None):
    font = font or F["mono_s"]
    w = font.size(label)[0] + 18
    r = pygame.Rect(pos[0], pos[1], w, 24)
    pygame.draw.rect(surf, RED if on else (70, 64, 52), r, border_radius=4)
    pygame.draw.rect(surf, AMBER if on else LINE, r, 1, border_radius=4)
    txt(surf, label, r.center, font, WHITE if on else MUTED, "center")
    return r


class UI:
    """Immediate-mode buttons. Buttons are re-registered every frame."""
    def __init__(self, screen):
        self.screen = screen
        self.buttons = []
        self.locked = False

    def clear(self):
        self.buttons = []

    def button(self, label, rect, action, kind="normal", disabled=False, top=False, font=None):
        r = pygame.Rect(rect)
        hover = r.collidepoint(pygame.mouse.get_pos()) and not disabled and (top or not self.locked)
        if disabled:
            fill, fg, bd = (36, 38, 44), (100, 98, 92), (60, 58, 54)
        elif kind == "primary":
            fill, fg, bd = (RED_L if hover else RED), WHITE, AMBER
        elif kind == "ghost":
            fill, fg, bd = ((50, 56, 70) if hover else (30, 35, 45)), PAPER, (LINE if not hover else AMBER)
        else:
            fill, fg, bd = ((58, 66, 82) if hover else PANEL_HI), PAPER, (AMBER if hover else LINE)
        pygame.draw.rect(self.screen, fill, r, border_radius=5)
        pygame.draw.rect(self.screen, bd, r, 2 if kind == "primary" else 1, border_radius=5)
        font = font or F["bodyb"]
        label = ellipsize(label, font, r.w - 16)
        txt(self.screen, label, r.center, font, fg, "center")
        if not disabled and (top or not self.locked):
            self.buttons.append((r, action))
        return hover

    def hotspot(self, rect, action, top=False):
        """Clickable area that draws nothing (draw your own content first)."""
        if not self.locked or top:
            self.buttons.append((pygame.Rect(rect), action))

    def hit(self, pos):
        for r, action in reversed(self.buttons):
            if r.collidepoint(pos):
                action()
                return True
        return False


# ---------------------------------------------------------------- icons
ICON_ORDER = ["biological", "digital", "financial", "physical", "communication",
              "documentary", "location", "forensic", "testimonial"]


def icon_for(item):
    for k in ICON_ORDER:
        if item["flags"].get(k):
            return k
    return "documentary"


def draw_icon(surf, kind, cx, cy, s, fg=PAPER, accent=RED_L):
    """Simple vector icons. s = half-size in pixels."""
    d = pygame.draw
    if kind == "biological":                       # vial
        d.rect(surf, fg, (cx - s * .32, cy - s * .8, s * .64, s * 1.7), 2, border_radius=int(s * .3))
        d.rect(surf, accent, (cx - s * .26, cy + s * .1, s * .52, s * .7), border_radius=int(s * .2))
        d.rect(surf, fg, (cx - s * .42, cy - s * .95, s * .84, s * .2))
    elif kind == "digital":                        # floppy disk
        d.rect(surf, fg, (cx - s, cy - s, s * 2, s * 2), 2, border_radius=3)
        d.rect(surf, accent, (cx - s * .6, cy - s, s * 1.2, s * .6))
        d.rect(surf, fg, (cx - s * .6, cy + s * .1, s * 1.2, s * .9), 2)
    elif kind == "financial":                      # coin
        d.circle(surf, fg, (cx, cy), int(s), 2)
        d.circle(surf, accent, (cx, cy), int(s * .6), 2)
        txt(surf, "$", (cx, cy), F["bodyb"], fg, "center")
    elif kind == "physical":                       # box
        d.rect(surf, fg, (cx - s, cy - s * .7, s * 2, s * 1.5), 2)
        d.line(surf, accent, (cx, cy - s * .7), (cx, cy + s * .8), 3)
        d.line(surf, fg, (cx - s, cy - s * .2), (cx + s, cy - s * .2), 1)
    elif kind == "communication":                  # envelope
        d.rect(surf, fg, (cx - s, cy - s * .65, s * 2, s * 1.3), 2)
        d.lines(surf, accent, False, [(cx - s, cy - s * .65), (cx, cy + s * .15), (cx + s, cy - s * .65)], 2)
    elif kind == "location":                       # map pin
        d.circle(surf, accent, (cx, cy - s * .25), int(s * .6))
        d.polygon(surf, accent, [(cx - s * .5, cy), (cx + s * .5, cy), (cx, cy + s * .95)])
        d.circle(surf, BG, (cx, cy - s * .25), int(s * .22))
    elif kind == "forensic":                       # magnifier
        d.circle(surf, fg, (int(cx - s * .15), int(cy - s * .15)), int(s * .65), 3)
        d.line(surf, accent, (cx + s * .3, cy + s * .3), (cx + s * .9, cy + s * .9), 4)
    elif kind == "testimonial":                    # speech bubble
        d.rect(surf, fg, (cx - s, cy - s * .7, s * 2, s * 1.2), 2, border_radius=6)
        d.polygon(surf, fg, [(cx - s * .4, cy + s * .5), (cx - s * .7, cy + s * .95), (cx, cy + s * .5)])
        for i in (-.45, 0, .45):
            d.circle(surf, accent, (int(cx + s * i), int(cy - s * .1)), 3)
    else:                                          # documentary: paper
        d.rect(surf, fg, (cx - s * .75, cy - s, s * 1.5, s * 2), 2)
        for i in range(4):
            d.line(surf, accent if i == 0 else fg, (cx - s * .5, cy - s * .55 + i * s * .38),
                   (cx + s * .5, cy - s * .55 + i * s * .38), 2)