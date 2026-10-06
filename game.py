"""
MYSTERY MATRIX - Real Case Archive  (playable detective game)

Flow:  Title -> Case select -> Briefing -> Crime-scene search -> Forensics
       -> Lab report -> Case board (deduction puzzles) -> Verdict / ending

Run:   python game.py

All case text comes from cases.csv / evidence.csv / features.csv.
The scene is a stylised search room, NOT a reconstruction of the real location.
Similarity scores compare encoded feature patterns only; they never prove
a link between cases or anyone's guilt.
"""
import math
import random
import sys
import time
from pathlib import Path

import pygame

import ui
from ui import (W, H, F, BG, PANEL, PANEL_HI, LINE, PAPER, PAPER_D, INK, AMBER, RED, RED_L,
                TEAL, MUTED, WHITE, GREEN, txt, para, wrap, ellipsize, card, chip, lerp, draw_icon, icon_for)
from data_manager import Dataset, FEATURES
from scene import Scene
from deduction import build_questions

try:
    import similarity as sim
except Exception as _e:
    sim = None
try:
    from similarity_lab import SimilarityLab
except Exception as _e:
    SimilarityLab = None
    print("Similarity lab unavailable:", _e)

try:
    from rank_lab import RankLab
except Exception as _e:
    RankLab = None
    print("Rank lab unavailable:", _e)

ROOT = Path(__file__).resolve().parent
DISCLAIMER = ("Similarity compares encoded evidence-flag patterns only. It does not show that two real "
              "cases are connected and it does not prove anyone's guilt.")


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MYSTERY MATRIX  |  Real Case Archive")
        info = pygame.display.Info()
        flags = pygame.SCALED
        if info.current_h < H + 80 or info.current_w < W + 40:
            flags = pygame.SCALED | pygame.FULLSCREEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except Exception:
            try:
                self.screen = pygame.display.set_mode((W, H), pygame.SCALED)
            except Exception:
                self.screen = pygame.display.set_mode((W, H))
        ui.init_fonts()
        self.clock = pygame.time.Clock()
        self.ui = ui.UI(self.screen)
        self.data = Dataset(ROOT)
        self.state = "menu"
        self.t = 0.0
        self.progress = {}                # case_id -> result dict
        self.toast = ("", 0.0)
        self.case = None
        self.items = []
        self.scene = None
        self.modal = None
        self.paused = False
        self.sim_lab = None
        self.rank_lab = None
        rng = random.Random(3)
        self.rain = [[rng.randint(0, W), rng.randint(0, H), rng.randint(9, 18)] for _ in range(130)]
        self.skyline = self._make_skyline()
        self.sky = self._make_sky()
        self.running = True

    # ------------------------------------------------------------ helpers
    def say(self, msg, secs=2.4):
        self.toast = (msg, secs)

    def go(self, state):
        self.state = state
        self.modal = None
        self.paused = False

    def _make_sky(self):
        s = pygame.Surface((W, H))
        for y in range(H):
            s.fill(lerp((8, 11, 20), (34, 24, 32), y / H), (0, y, W, 1))
        pygame.draw.circle(s, (30, 36, 52), (940, 120), 70)
        pygame.draw.circle(s, (206, 204, 190), (940, 120), 38)
        pygame.draw.circle(s, (176, 176, 168), (928, 112), 8)
        return s

    def _make_skyline(self):
        rng = random.Random(8)
        blds, x = [], -10
        while x < W:
            w = rng.randint(50, 110)
            h = rng.randint(140, 380)
            wins = [(x + 8 + i * 16, H - h + 12 + j * 20, rng.random() * 6.3)
                    for i in range(max(1, (w - 14) // 16)) for j in range(max(1, (h - 24) // 20))
                    if rng.random() < .45]
            blds.append((x, w, h, wins))
            x += w + rng.randint(0, 8)
        return blds

    def start_case(self, cid):
        self.case = self.data.case(cid)
        self.items = list(self.data.evidence.get(cid, []))
        self.scene = Scene(cid, self.items)
        self.brief_t = 0.0
        self.brief_lines = self._brief_lines()
        self.start_time = time.time()
        self.go("briefing")

    # ------------------------------------------------------------ events
    def handle(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.on_escape()
            elif e.key == pygame.K_SPACE:
                if self.state == "briefing":
                    self.brief_t = 1e9
                elif self.state == "send":
                    self.send_t = 1e9
            elif self.state == "scene" and not self.modal and not self.paused:
                if e.key == pygame.K_h:
                    self.do_hint()
                elif e.key == pygame.K_l:
                    self.scene.lights = not self.scene.lights
            elif self.state == "sim" and self.sim_lab:
                if self.sim_lab.handle_event(e) == "back":
                    self.go("lab")
            elif self.state == "rank" and self.rank_lab:
                if self.rank_lab.handle_event(e) == "back":
                    self.go("lab")
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.ui.hit(e.pos):
                return
            if self.state == "scene" and not self.modal and not self.paused:
                msg = self.scene.click(e.pos)
                if msg:
                    self.say(msg)
            elif self.state == "send":
                self.send_t = 1e9
            elif self.state == "sim" and self.sim_lab:
                self.sim_lab.handle_event(e)
            elif self.state == "rank" and self.rank_lab:
                self.rank_lab.handle_event(e)

    def on_escape(self):
        s = self.state
        if s == "scene":
            if self.modal:
                self.close_modal()
            else:
                self.paused = not self.paused
        elif s == "cases":
            self.go("menu")
        elif s == "data":
            self.go("menu")
        elif s == "briefing":
            self.go("cases")
        elif s == "sim":
            self.go("lab")
        elif s == "rank":
            self.go("lab")
        elif s == "lab":
            self.go("lab")

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        if self.toast[1] > 0:
            self.toast = (self.toast[0], self.toast[1] - dt)
        if self.state == "briefing":
            self.brief_t += dt
        elif self.state == "scene" and not self.modal and not self.paused:
            ev = self.scene.update(dt)
            if ev:
                if ev[0] == "found":
                    self.modal = {"item": ev[1], "new": True}
                else:
                    self.say(f"Nothing here  -  {ev[1]['label']}.")
        elif self.state == "send":
            self.send_t += dt
            if self.send_t >= self.send_total:
                self.enter_lab()
        for d in self.rain:
            d[1] += d[2] * 60 * dt
            d[0] -= d[2] * 14 * dt
            if d[1] > H or d[0] < 0:
                d[0], d[1] = random.randint(0, W + 200), -20

    # ------------------------------------------------------------ actions
    def do_hint(self):
        if self.scene.use_hint():
            self.say("Hint: something is hidden near the highlighted spot.")
        elif self.scene.hints_left <= 0:
            self.say("No hints left.")

    def close_modal(self):
        self.modal = None

    def begin_forensics(self):
        self.send_t = 0.0
        self.send_total = min(8.0, 1.3 + 0.8 * len(self.scene.found))
        self.go("send")

    def enter_lab(self):
        self.lab_sel = 0
        self.go("lab")

    def begin_deduction(self):
        found = self.scene.found
        self.qs = build_questions(self.case, found, self.data.cases)
        self.qi, self.qpick, self.qright = 0, None, []
        self.go("deduce")

    def pick_answer(self, i):
        if self.qpick is None:
            self.qpick = i
            self.qright.append(i == self.qs[self.qi]["correct"])

    def next_question(self):
        if self.qi + 1 >= len(self.qs):
            self.finish_case()
        else:
            self.qi += 1
            self.qpick = None

    def finish_case(self):
        n = len(self.items)
        found_pts = n * 10
        pen = self.scene.hints_used * 5
        q_pts = 0
        final_ok = False
        max_pts = found_pts
        for q, ok in zip(self.qs, self.qright):
            if q.get("final"):
                max_pts += 40
                if ok:
                    q_pts += 40
                    final_ok = True
            else:
                max_pts += 15
                if ok:
                    q_pts += 15
        score = max(0, found_pts - pen + q_pts)
        pct = score / max_pts if max_pts else 0
        rank = ("CHIEF INSPECTOR" if pct >= .9 else "DETECTIVE" if pct >= .7
                else "INVESTIGATOR" if pct >= .5 else "ROOKIE")
        self.result = {"score": score, "max": max_pts, "rank": rank, "final_ok": final_ok,
                       "hints": self.scene.hints_used, "time": int(time.time() - self.start_time),
                       "correct": sum(self.qright), "asked": len(self.qs)}
        self.progress[self.case["id"]] = self.result
        self.go("ending")

    def open_similarity(self):
        if SimilarityLab is None:
            self.say("Similarity lab module not available.")
            return
        try:
            if self.sim_lab is None:
                self.sim_lab = SimilarityLab(str(ROOT / "evidence.csv"), str(ROOT / "cases.csv"))
            ids = self.sim_lab.ids
            if self.case and self.case["id"] in ids and len(ids) > 1:
                self.sim_lab.row = ids.index(self.case["id"])
                self.sim_lab.col = (self.sim_lab.row + 1) % len(ids)
            self.go("sim")
        except Exception as exc:
            self.say("Similarity lab error: " + str(exc)[:60])

    def open_rank(self):
        if RankLab is None:
            self.say("Rank lab module not available.")
            return
        try:
            if self.rank_lab is None:
                self.rank_lab = RankLab(str(ROOT / "evidence.csv"))
            if self.case:
                self.rank_lab.select_case(self.case["id"])
            self.go("rank")
        except Exception as exc:
            self.say("Rank lab error: " + str(exc)[:60])

    # ------------------------------------------------------------ drawing
    def draw(self):
        s = self.screen
        self.ui.clear()
        self.ui.locked = False
        fn = {"menu": self.draw_menu, "cases": self.draw_cases, "briefing": self.draw_briefing,
              "scene": self.draw_scene, "send": self.draw_send, "lab": self.draw_lab,
              "deduce": self.draw_deduce, "ending": self.draw_ending, "data": self.draw_data,
              "sim": self.draw_sim, "rank": self.draw_rank}[self.state]
        fn()
        if self.toast[1] > 0 and self.state not in ("sim", "rank"):
            msg = self.toast[0]
            w = F["body"].size(msg)[0] + 40
            r = pygame.Rect(W // 2 - w // 2, 70, w, 38)
            pygame.draw.rect(s, (20, 22, 28), r, border_radius=6)
            pygame.draw.rect(s, AMBER, r, 1, border_radius=6)
            txt(s, msg, r.center, F["body"], WHITE, "center")
        pygame.display.flip()

    def backdrop(self, rain=True, city=True):
        s = self.screen
        s.blit(self.sky, (0, 0))
        if city:
            for (x, w, h, wins) in self.skyline:
                pygame.draw.rect(s, (12, 14, 20), (x, H - h, w, h))
                pygame.draw.rect(s, (18, 20, 28), (x, H - h, w, 4))
                for (wx, wy, ph) in wins:
                    if math.sin(self.t * .4 + ph) > -.85:
                        pygame.draw.rect(s, (214, 168, 84) if ph < 4 else (120, 150, 170), (wx, wy, 8, 11))
        if rain:
            for x, y, l in self.rain:
                pygame.draw.line(s, (80, 96, 120), (x, y), (x - l * .5, y + l), 1)

    def title_bar(self, title, sub=None):
        s = self.screen
        pygame.draw.rect(s, (8, 10, 14), (0, 0, W, 64))
        pygame.draw.line(s, RED, (0, 64), (W, 64), 3)
        txt(s, "MYSTERY MATRIX", (24, 12), F["mono"], AMBER)
        txt(s, title, (24, 34), F["small"], MUTED)
        if sub:
            txt(s, sub, (W - 24, 24), F["mono"], PAPER, "topright")

    # ---- menu ---------------------------------------------------------
    def draw_menu(self):
        s = self.screen
        self.backdrop()
        pygame.draw.rect(s, (0, 0, 0), (0, 0, 560, H))
        shade = pygame.Surface((560, H), pygame.SRCALPHA)
        shade.fill((6, 8, 12, 150))
        s.blit(shade, (0, 0))
        txt(s, "MYSTERY", (64, 120), F["huge"], PAPER)
        glow = 0.65 + 0.35 * math.sin(self.t * 2.2)
        txt(s, "MATRIX", (64, 208), F["huge"], lerp((90, 30, 28), RED_L, glow))
        pygame.draw.line(s, RED, (68, 318), (480, 318), 3)
        txt(s, "A REAL-CASE DETECTIVE ARCHIVE", (68, 332), F["mono"], AMBER)
        para(s, "Search the scene. Find the evidence. Send it to forensics. Close the case.",
             68, 372, 440, F["body"], PAPER, 6)
        playable = self.data.playable_cases()
        self.ui.button("START INVESTIGATION", (68, 470, 330, 54), lambda: self.go("cases"),
                       "primary", disabled=not playable)
        self.ui.button("DATASET STATUS", (68, 536, 330, 44), lambda: self.go("data"), "ghost")
        self.ui.button("QUIT", (68, 590, 330, 44), lambda: setattr(self, "running", False), "ghost")
        if not playable:
            txt(s, "No playable cases found - see Dataset Status.", (68, 650), F["small"], RED_L)
        txt(s, "Cases and evidence are loaded from the project's CSV files.", (68, H - 54), F["small"], MUTED)
        txt(s, "Educational project - not a real investigative tool.", (68, H - 32), F["small"], MUTED)

    # ---- case select --------------------------------------------------
    def draw_cases(self):
        s = self.screen
        self.backdrop(rain=False, city=False)
        self.title_bar("CASE ARCHIVE", f"{len(self.data.playable_cases())} FILES")
        txt(s, "CHOOSE A CASE FILE", (W // 2, 98), F["h1"], PAPER, "center")
        txt(s, "Each file is a real documented case. Pick one to open the investigation.", (W // 2, 140), F["small"], MUTED, "center")
        cases = self.data.playable_cases()
        n = len(cases)
        cw, ch, gap = 204, 400, 16
        x0 = (W - (n * cw + (n - 1) * gap)) // 2
        mp = pygame.mouse.get_pos()
        for i, c in enumerate(cases):
            r = pygame.Rect(x0 + i * (cw + gap), 190, cw, ch)
            hov = r.collidepoint(mp)
            if hov:
                r = r.move(0, -10)
            pygame.draw.rect(s, (0, 0, 0), r.move(6, 8))
            pygame.draw.rect(s, (196, 160, 90), (r.x, r.y - 16, 80, 20), border_top_left_radius=6, border_top_right_radius=6)
            pygame.draw.rect(s, PAPER if not hov else (244, 232, 202), r)
            pygame.draw.rect(s, (124, 100, 66), r, 2)
            txt(s, "CASE " + c["id"], (r.x + 14, r.y + 14), F["mono"], RED)
            ty = r.y + 52
            for ln in wrap(c["short"], F["h2"], cw - 28)[:3]:
                txt(s, ln, (r.x + 14, ty), F["h2"], INK)
                ty += 30
            pygame.draw.line(s, (150, 120, 80), (r.x + 14, ty + 6), (r.right - 14, ty + 6), 1)
            ty += 18
            ty = para(s, c["category"] or "Category not recorded", r.x + 14, ty, cw - 28, F["small"], INK, 2, max_lines=2)
            txt(s, c["period"], (r.x + 14, ty + 6), F["smallb"], INK)
            n_ev = len(self.data.evidence.get(c["id"], []))
            txt(s, f"{n_ev} evidence items", (r.x + 14, r.bottom - 106), F["smallb"], INK)
            res = self.progress.get(c["id"])
            if res:
                st = pygame.Surface((150, 40), pygame.SRCALPHA)
                pygame.draw.rect(st, RED, (0, 0, 150, 40), 3, border_radius=4)
                txt(st, "CLOSED " + str(int(100 * res["score"] / max(1, res["max"]))) + "%", (75, 20), F["mono"], RED, "center")
                st = pygame.transform.rotate(st, 12)
                s.blit(st, (r.x + 22, r.bottom - 150))
            self.ui.button("OPEN FILE", (r.x + 14, r.bottom - 58, cw - 28, 42),
                           lambda cid=c["id"]: self.start_case(cid), "primary")
        self.ui.button("BACK", (24, H - 64, 140, 42), lambda: self.go("menu"), "ghost")

    # ---- briefing -----------------------------------------------------
    def _brief_lines(self):
        c = self.case
        items = self.items
        srcs = {e["source_title"] for e in items if e["source_title"]}
        L = [("h", f"CASE FILE {c['id']}  -  {c['short'].upper()}"),
             ("k", "CATEGORY", c["category"] or "not recorded"),
             ("k", "PERIOD COVERED", c["period"] or "not recorded"),
             ("gap",),
             ("t", "WHAT THE FILE RECORDS"),
             ("p", c["summary"] or "No summary recorded in cases.csv."),
             ("gap",),
             ("t", "THE EVIDENCE ON FILE"),
             ("p", f"{len(items)} items are logged for this case, drawn from {len(srcs)} cited source(s). "
                   "Every item is hidden somewhere in the search room. Find them all."),
             ("gap",),
             ("t", "YOUR ORDERS"),
             ("p", "1) Search the room.  2) Recover every item.  3) Send them to forensics.  "
                   "4) Work the case board and close the file."),
             ("gap",),
             ("n", "NOTE: the room is a stylised search scene, not a reconstruction of the real location. "
                   "The evidence text is quoted from the dataset. Read the cited sources for the full history.")]
        return L

    def draw_briefing(self):
        s = self.screen
        self.backdrop(rain=True, city=False)
        self.title_bar("CASE BRIEFING", "CONFIDENTIAL")
        r = pygame.Rect(60, 90, 760, 500)
        card(s, r)
        pygame.draw.rect(s, RED, (r.right - 190, r.y + 24, 150, 40), 3)
        txt(s, "CONFIDENTIAL", (r.right - 115, r.y + 44), F["mono"], RED, "center")
        budget = int(self.brief_t * 85)
        x, y = r.x + 36, r.y + 30
        done = True
        for ln in self.brief_lines:
            kind = ln[0]
            if kind == "gap":
                y += 10
                continue
            if kind == "h":
                text, font, col = ln[1], F["h2"], RED
                lines = wrap(text, font, r.w - 250)
            elif kind == "k":
                text, font, col = f"{ln[1]}:  {ln[2]}", F["type"], INK
                lines = wrap(text, font, r.w - 72)
            elif kind == "t":
                text, font, col = ln[1], F["mono"], RED
                lines = [text]
            elif kind == "n":
                text, font, col = ln[1], F["small"], (110, 40, 34)
                lines = wrap(text, font, r.w - 72)
            else:
                text, font, col = ln[1], F["body"], INK
                lines = wrap(text, font, r.w - 72)
            for l in lines:
                if budget <= 0:
                    done = False
                    break
                shown = l[:budget]
                budget -= len(l)
                txt(s, shown, (x, y), font, col)
                y += font.get_linesize() + 4
            if budget <= 0 and len(shown) < len(l):
                done = False
                break
        # side stat cards
        sx = 850
        stats = [("EVIDENCE ITEMS", str(len(self.items))), ("HINTS AVAILABLE", "3"),
                 ("PUZZLES AHEAD", "4-5")]
        for i, (k, v) in enumerate(stats):
            rr = pygame.Rect(sx, 110 + i * 110, 270, 92)
            pygame.draw.rect(s, PANEL, rr, border_radius=6)
            pygame.draw.rect(s, LINE, rr, 1, border_radius=6)
            txt(s, v, (rr.x + 20, rr.y + 12), F["title"], AMBER)
            txt(s, k, (rr.x + 20, rr.bottom - 26), F["mono_s"], MUTED)
        para(s, "Tip: in the dark room your flashlight follows the mouse. Press L for lights, H for a hint.",
             sx, 460, 270, F["small"], MUTED, 4)
        if not done:
            self.ui.button("SKIP  (SPACE)", (sx, 590, 270, 48), lambda: setattr(self, "brief_t", 1e9), "ghost")
        else:
            self.ui.button("GO TO THE SCENE", (sx, 590, 270, 48), lambda: self.go("scene"), "primary")
        self.ui.button("BACK", (24, H - 64, 120, 42), lambda: self.go("cases"), "ghost")

    # ---- scene --------------------------------------------------------
    def draw_scene(self):
        s = self.screen
        mouse = pygame.mouse.get_pos()
        sc = self.scene
        locked = bool(self.modal or self.paused)
        sc.draw(s, mouse if not locked else (-500, -500), self.t)
        if locked and not sc.lights:
            pass
        # HUD
        pygame.draw.rect(s, (8, 10, 14), (0, 0, W, 60))
        pygame.draw.line(s, RED, (0, 60), (W, 60), 3)
        txt(s, f"CASE {self.case['id']}  -  {self.case['short'].upper()}", (20, 10), F["mono"], AMBER)
        txt(s, "SEARCH THE ROOM  -  click furniture to look inside", (20, 34), F["small"], MUTED)
        txt(s, f"EVIDENCE  {len(sc.found)} / {sc.total}", (W // 2, 30), F["h2"], WHITE, "center")
        self.ui.locked = locked
        self.ui.button(f"HINT ({sc.hints_left})", (W - 380, 12, 110, 36), self.do_hint, "ghost",
                       disabled=sc.hints_left <= 0 or sc.complete, font=F["smallb"])
        self.ui.button("LIGHTS " + ("ON" if sc.lights else "OFF"), (W - 260, 12, 120, 36),
                       lambda: setattr(sc, "lights", not sc.lights), "ghost", font=F["smallb"])
        self.ui.button("PAUSE", (W - 130, 12, 110, 36), lambda: setattr(self, "paused", True), "ghost", font=F["smallb"])
        # evidence bag
        pygame.draw.rect(s, (8, 10, 14), (0, 676, W, 84))
        pygame.draw.line(s, LINE, (0, 676), (W, 676), 2)
        txt(s, "EVIDENCE BAG", (20, 690), F["mono"], AMBER)
        txt(s, f"{len(sc.found)} of {sc.total} recovered", (20, 714), F["small"], MUTED)
        n = max(1, sc.total)
        slot_w = min(86, (W - 420) // n)
        bx = 230
        for i in range(n):
            r = pygame.Rect(bx + i * (slot_w + 6), 686, slot_w, 64)
            if i < len(sc.found):
                it = sc.found[i]
                hov = r.collidepoint(mouse) and not locked
                pygame.draw.rect(s, (60, 70, 90) if hov else PANEL_HI, r, border_radius=5)
                pygame.draw.rect(s, GREEN, r, 2, border_radius=5)
                draw_icon(s, icon_for(it), r.centerx, r.y + 24, 14)
                txt(s, it["id"].split("-")[-1] if "-" in it["id"] else it["id"], (r.centerx, r.bottom - 12), F["mono_s"], PAPER, "center")
                self.ui.hotspot(r, lambda itm=it: setattr(self, "modal", {"item": itm, "new": False}))
            else:
                pygame.draw.rect(s, (16, 18, 24), r, border_radius=5)
                pygame.draw.rect(s, LINE, r, 1, border_radius=5)
                txt(s, "?", r.center, F["h2"], (70, 66, 56), "center")
        if sc.complete and not locked:
            pulse = 0.5 + 0.5 * math.sin(self.t * 5)
            self.ui.button("SEND TO FORENSICS  >", (W - 300, 688, 280, 60), self.begin_forensics, "primary")
            pygame.draw.rect(s, lerp((90, 40, 30), AMBER, pulse), (W - 304, 684, 288, 68), 2, border_radius=6)
        # modal: evidence card
        if self.modal:
            self.draw_evidence_modal()
        elif self.paused:
            self.draw_pause()

    def dim(self, a=170):
        d = pygame.Surface((W, H), pygame.SRCALPHA)
        d.fill((0, 0, 0, a))
        self.screen.blit(d, (0, 0))

    def draw_evidence_modal(self):
        s = self.screen
        self.dim()
        it = self.modal["item"]
        new = self.modal["new"]
        r = pygame.Rect(W // 2 - 360, 110, 720, 480)
        card(s, r)
        if new:
            pygame.draw.rect(s, RED, (r.x + 24, r.y + 22, 230, 34))
            txt(s, "EVIDENCE FOUND!", (r.x + 139, r.y + 39), F["mono"], WHITE, "center")
        else:
            txt(s, "EVIDENCE BAG - ITEM REVIEW", (r.x + 28, r.y + 28), F["mono"], RED)
        idx = (len(self.scene.found) if new else self.scene.found.index(it) + 1)
        txt(s, f"ITEM {idx} OF {self.scene.total}", (r.right - 28, r.y + 30), F["mono_s"], INK, "topright")
        # icon plate
        plate = pygame.Rect(r.x + 28, r.y + 78, 120, 120)
        pygame.draw.rect(s, (40, 36, 30), plate, border_radius=8)
        pygame.draw.rect(s, AMBER, plate, 2, border_radius=8)
        draw_icon(s, icon_for(it), plate.centerx, plate.centery, 36)
        txt(s, it["id"], (r.x + 170, r.y + 78), F["h2"], RED)
        y = para(s, it["description"], r.x + 170, r.y + 114, r.w - 200, F["body"], INK, 5, max_lines=7)
        y = max(y + 6, r.y + 240)
        txt(s, "CATEGORIES FLAGGED IN THE DATASET", (r.x + 28, y), F["mono_s"], RED)
        cx, cy = r.x + 28, y + 24
        for f in FEATURES:
            if it["flags"].get(f):
                rr = chip(s, f.upper(), (cx, cy))
                cx += rr.w + 8
                if cx > r.right - 120:
                    cx, cy = r.x + 28, cy + 30
        y = cy + 36
        meta = "  |  ".join(p for p in [it["source_title"], it["source_type"], it["status"]] if p)
        if meta:
            y = para(s, "SOURCE: " + meta, r.x + 28, y, r.w - 56, F["small"], (80, 66, 46), 2, max_lines=2)
        if it["coding_note"]:
            para(s, "CODING NOTE: " + it["coding_note"], r.x + 28, y + 2, r.w - 56, F["small"], (80, 66, 46), 2, max_lines=2)
        label = "ADD TO EVIDENCE BAG" if new else "CLOSE"
        self.ui.button(label, (r.centerx - 150, r.bottom - 62, 300, 46), self.close_modal, "primary", top=True)

    def draw_pause(self):
        s = self.screen
        self.dim(190)
        r = pygame.Rect(W // 2 - 220, 200, 440, 300)
        card(s, r, PANEL, LINE)
        txt(s, "PAUSED", (r.centerx, r.y + 44), F["h1"], PAPER, "center")
        self.ui.button("RESUME", (r.x + 60, r.y + 100, 320, 48), lambda: setattr(self, "paused", False), "primary", top=True)
        self.ui.button("BACK TO CASE ARCHIVE", (r.x + 60, r.y + 160, 320, 48), lambda: self.go("cases"), "ghost", top=True)
        self.ui.button("QUIT GAME", (r.x + 60, r.y + 220, 320, 48), lambda: setattr(self, "running", False), "ghost", top=True)

    # ---- forensics transit -------------------------------------------
    def draw_send(self):
        s = self.screen
        self.backdrop(rain=False, city=False)
        self.title_bar("FORENSICS  -  EVIDENCE INTAKE")
        found = self.scene.found
        n = len(found)
        txt(s, "SENDING EVIDENCE TO FORENSICS", (W // 2, 112), F["h1"], PAPER, "center")
        txt(s, f"{n} items sealed and logged", (W // 2, 156), F["small"], MUTED, "center")
        # conveyor
        pygame.draw.rect(s, (30, 34, 42), (60, 330, W - 120, 70))
        for x in range(60, W - 60, 40):
            off = int(self.t * 60) % 40
            pygame.draw.line(s, (50, 56, 68), (x + off, 332), (x + off, 398), 2)
        prog = min(1.0, self.send_t / self.send_total)
        for i, it in enumerate(found):
            u = (prog * (n + 2.0) - i) / (n + 2.0)
            u = max(0, min(1, u + 0.0))
            x = 90 + (W - 260) * (i / max(1, n - 1) * 0.0 + min(1, max(0, prog * 1.15 - i * 0.05)))
            x = 90 + (W - 280) * max(0.0, min(1.0, prog * 1.2 - i * 0.045))
            r = pygame.Rect(int(x), 300, 70, 64)
            pygame.draw.rect(s, PAPER_D, r, border_radius=5)
            pygame.draw.rect(s, (124, 100, 66), r, 2, border_radius=5)
            draw_icon(s, icon_for(it), r.centerx, r.centery - 6, 16, INK, RED)
            txt(s, it["id"].split("-")[-1], (r.centerx, r.bottom - 12), F["mono_s"], INK, "center")
        # lab door
        pygame.draw.rect(s, (60, 66, 80), (W - 130, 250, 90, 190))
        pygame.draw.rect(s, TEAL, (W - 130, 250, 90, 190), 3)
        txt(s, "LAB", (W - 85, 330), F["h2"], TEAL, "center")
        # progress
        bar = pygame.Rect(180, 500, W - 360, 26)
        pygame.draw.rect(s, (20, 24, 30), bar, border_radius=6)
        pygame.draw.rect(s, AMBER, (bar.x + 3, bar.y + 3, int((bar.w - 6) * prog), bar.h - 6), border_radius=4)
        cur = min(n - 1, int(prog * n))
        msg = f"Logging {found[cur]['id']} ..." if prog < 1 else "Transfer complete."
        txt(s, msg, (W // 2, 548), F["mono"], PAPER, "center")
        self.ui.button("SKIP", (W // 2 - 70, 600, 140, 44), lambda: setattr(self, "send_t", 1e9), "ghost")

    # ---- lab report ---------------------------------------------------
    def draw_lab(self):
        s = self.screen
        self.backdrop(rain=False, city=False)
        self.title_bar("FORENSIC LAB REPORT", f"CASE {self.case['id']}")
        found = self.scene.found
        txt(s, "ANALYSIS COMPLETE", (24, 82), F["h2"], TEAL)
        txt(s, "Each item was logged and coded by the lab. Select an item to read its report.", (24, 114), F["small"], MUTED)
        # left list
        list_r = pygame.Rect(24, 146, 330, 520)
        pygame.draw.rect(s, PANEL, list_r, border_radius=6)
        pygame.draw.rect(s, LINE, list_r, 1, border_radius=6)
        row_h = min(48, (list_r.h - 12) // max(1, len(found)))
        for i, it in enumerate(found):
            rr = pygame.Rect(list_r.x + 8, list_r.y + 8 + i * row_h, list_r.w - 16, row_h - 4)
            sel = i == self.lab_sel
            pygame.draw.rect(s, RED if sel else PANEL_HI, rr, border_radius=4)
            pygame.draw.rect(s, AMBER if sel else LINE, rr, 1, border_radius=4)
            draw_icon(s, icon_for(it), rr.x + 22, rr.centery, 11)
            txt(s, it["id"], (rr.x + 46, rr.centery), F["smallb"], WHITE, "midleft")
            txt(s, "ANALYSED", (rr.right - 10, rr.centery), F["mono_s"], GREEN if not sel else WHITE, "midright")
            self.ui.hotspot(rr, lambda j=i: setattr(self, "lab_sel", j))
        # right: report
        it = found[self.lab_sel]
        rep = pygame.Rect(374, 146, 782, 380)
        card(s, rep)
        txt(s, f"REPORT  -  {it['id']}", (rep.x + 28, rep.y + 22), F["h2"], RED)
        plate = pygame.Rect(rep.x + 28, rep.y + 62, 96, 96)
        pygame.draw.rect(s, (40, 36, 30), plate, border_radius=8)
        pygame.draw.rect(s, AMBER, plate, 2, border_radius=8)
        draw_icon(s, icon_for(it), plate.centerx, plate.centery, 30)
        y = para(s, it["description"], rep.x + 144, rep.y + 62, rep.w - 172, F["body"], INK, 4, max_lines=5)
        y = max(y + 6, rep.y + 172)
        txt(s, "CATEGORIES FLAGGED", (rep.x + 28, y), F["mono_s"], RED)
        cx, cy = rep.x + 28, y + 22
        for f in FEATURES:
            on = bool(it["flags"].get(f))
            rr = chip(s, f.upper(), (cx, cy), on)
            cx += rr.w + 6
            if cx > rep.right - 150:
                cx, cy = rep.x + 28, cy + 30
        y = cy + 38
        meta = "  |  ".join(p for p in [it["source_title"], it["source_type"], it["status"]] if p)
        if meta:
            y = para(s, "SOURCE: " + meta, rep.x + 28, y, rep.w - 56, F["small"], (80, 66, 46), 2, max_lines=2)
        if it["coding_note"]:
            para(s, "CODING NOTE: " + it["coding_note"], rep.x + 28, y + 2, rep.w - 56, F["small"], (80, 66, 46), 2, max_lines=3)
        # bottom: pattern summary
        pr = pygame.Rect(374, 540, 782, 126)
        pygame.draw.rect(s, PANEL, pr, border_radius=6)
        pygame.draw.rect(s, LINE, pr, 1, border_radius=6)
        txt(s, "PATTERN ACROSS ALL RECOVERED ITEMS", (pr.x + 16, pr.y + 10), F["mono_s"], AMBER)
        counts = {f: sum(e["flags"][f] for e in found) for f in FEATURES}
        mx = max(1, max(counts.values()))
        bw = (pr.w - 32) // len(FEATURES)
        for i, f in enumerate(FEATURES):
            x = pr.x + 16 + i * bw
            h = int(52 * counts[f] / mx)
            pygame.draw.rect(s, (36, 40, 50), (x + 6, pr.y + 34, bw - 12, 52))
            pygame.draw.rect(s, RED_L if counts[f] else (60, 56, 50), (x + 6, pr.y + 86 - h, bw - 12, max(2, h)))
            txt(s, str(counts[f]), (x + bw // 2, pr.y + 30), F["mono_s"], WHITE, "center")
            txt(s, f[:5].upper(), (x + bw // 2, pr.y + 100), F["mono_s"], MUTED, "center")
        # bottom buttons
        txt(s, self._closest_text(), (24, 678), F["small"], MUTED)
        para(s, DISCLAIMER, 24, 700, 400, F["small"], (120, 114, 100), 1, max_lines=3)
        self.ui.button("RANK / PIVOTS", (W - 780, 690, 160, 48), self.open_rank, "ghost",
                       disabled=RankLab is None, font=F["smallb"])
        self.ui.button("COMPARE CASES (SIMILARITY LAB)", (W - 610, 690, 330, 48), self.open_similarity, "ghost",
                       disabled=SimilarityLab is None, font=F["smallb"])
        self.ui.button("TO THE CASE BOARD  >", (W - 260, 690, 240, 48), self.begin_deduction, "primary")

    def _closest_text(self):
        if sim is None:
            return ""
        try:
            m = sim.get_matrix("count", str(ROOT / "evidence.csv"))
            ranked = [r for r in sim.most_similar(m, self.case["id"]) if r[1] is not None]
            if not ranked:
                return ""
            oid, sc = ranked[0]
            name = next((c["short"] for c in self.data.cases if c["id"] == oid), oid)
            return f"Closest feature pattern among the case files: {name} (cosine {sc:.3f})."
        except Exception:
            return ""

    # ---- deduction ----------------------------------------------------
    def draw_deduce(self):
        s = self.screen
        self.backdrop(rain=False, city=False)
        self.title_bar("CASE BOARD", f"CASE {self.case['id']}")
        # corkboard with pinned evidence
        board = pygame.Rect(24, 84, 400, 600)
        pygame.draw.rect(s, (92, 64, 40), board)
        pygame.draw.rect(s, (160, 120, 78), board.inflate(-16, -16))
        rng = random.Random(self.case["id"])
        found = self.scene.found
        cols = 3
        for i, it in enumerate(found):
            col, row = i % cols, i // cols
            x = board.x + 28 + col * 118 + rng.randint(-4, 4)
            y = board.y + 36 + row * 128 + rng.randint(-4, 4)
            p = pygame.Rect(x, y, 104, 108)
            pygame.draw.rect(s, (0, 0, 0), p.move(3, 4))
            pygame.draw.rect(s, PAPER, p)
            pygame.draw.circle(s, RED, (p.centerx, p.y + 7), 5)
            draw_icon(s, icon_for(it), p.centerx, p.y + 46, 18, INK, RED)
            txt(s, it["id"], (p.centerx, p.bottom - 14), F["mono_s"], INK, "center")
        # question panel
        q = self.qs[self.qi]
        qr = pygame.Rect(444, 84, 712, 600)
        card(s, qr)
        final = q.get("final")
        tagcol = RED if final else (60, 100, 100)
        pygame.draw.rect(s, tagcol, (qr.x + 26, qr.y + 22, 230, 30), border_radius=4)
        txt(s, q["tag"], (qr.x + 141, qr.y + 37), F["mono_s"], WHITE, "center")
        txt(s, f"QUESTION {self.qi + 1} OF {len(self.qs)}", (qr.right - 26, qr.y + 30), F["mono_s"], INK, "topright")
        y = para(s, q["prompt"], qr.x + 26, qr.y + 68, qr.w - 52, F["bodyb"], INK, 5)
        if q.get("sub"):
            y = para(s, '"' + q["sub"] + '"', qr.x + 26, y + 2, qr.w - 52, F["small"], (90, 72, 50), 3, max_lines=3)
        y += 10
        done = self.qpick is not None
        for i, opt in enumerate(q["options"]):
            rr = pygame.Rect(qr.x + 26, y, qr.w - 52, 50)
            hov = rr.collidepoint(pygame.mouse.get_pos()) and not done
            if done and i == q["correct"]:
                fill, bd = (150, 196, 150), GREEN
            elif done and i == self.qpick:
                fill, bd = (214, 140, 130), RED
            else:
                fill, bd = ((222, 206, 168) if hov else PAPER_D), (124, 100, 66)
            pygame.draw.rect(s, fill, rr, border_radius=5)
            pygame.draw.rect(s, bd, rr, 2, border_radius=5)
            txt(s, "ABCD"[i], (rr.x + 22, rr.centery), F["mono"], RED, "center")
            line = ellipsize(opt, F["body"], rr.w - 70)
            txt(s, line, (rr.x + 44, rr.centery), F["body"], INK, "midleft")
            if not done:
                self.ui.hotspot(rr, lambda j=i: self.pick_answer(j))
            y += 58
        if done:
            ok = self.qright[-1]
            col = (40, 110, 60) if ok else (140, 40, 34)
            txt(s, "CORRECT" if ok else "NOT QUITE", (qr.x + 26, y + 2), F["mono"], col)
            y2 = para(s, q["explain"], qr.x + 26, y + 26, qr.w - 52, F["small"], INK, 3, max_lines=3)
            if q["math"]:
                mr = pygame.Rect(qr.x + 26, y2 + 4, qr.w - 52, min(qr.bottom - 80 - y2, 16 * len(q["math"]) + 12))
                pygame.draw.rect(s, (40, 36, 30), mr, border_radius=4)
                for k, line in enumerate(q["math"]):
                    if 14 + k * 16 < mr.h:
                        txt(s, ellipsize(line, F["mono_s"], mr.w - 20), (mr.x + 10, mr.y + 8 + k * 16), F["mono_s"], PAPER)
            last = self.qi + 1 >= len(self.qs)
            self.ui.button("CLOSE THE CASE  >" if last else "NEXT QUESTION  >", (qr.right - 270, qr.bottom - 62, 244, 46),
                           self.next_question, "primary")
        else:
            txt(s, "Choose an answer.", (qr.right - 26, qr.bottom - 48), F["small"], (90, 72, 50), "topright")
        self.ui.button("BACK TO LAB", (qr.x + 26, qr.bottom - 62, 150, 46), lambda: self.go("lab"), "ghost",
                       disabled=False, font=F["smallb"])

    # ---- ending -------------------------------------------------------
    def draw_ending(self):
        s = self.screen
        self.backdrop(rain=True, city=True)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        s.blit(shade, (0, 0))
        r = pygame.Rect(W // 2 - 420, 60, 840, 640)
        card(s, r)
        res = self.result
        c = self.case
        txt(s, "CASE CLOSED", (r.centerx, r.y + 56), F["title"], RED, "center")
        txt(s, f"CASE {c['id']}  -  {c['short'].upper()}", (r.centerx, r.y + 104), F["mono"], INK, "center")
        pygame.draw.line(s, (150, 120, 80), (r.x + 40, r.y + 130), (r.right - 40, r.y + 130), 1)
        txt(s, res["rank"], (r.centerx, r.y + 170), F["h1"], (40, 100, 80) if res["final_ok"] else (120, 70, 40), "center")
        txt(s, f"SCORE  {res['score']} / {res['max']}", (r.centerx, r.y + 212), F["h2"], INK, "center")
        txt(s, f"Puzzles solved {res['correct']}/{res['asked']}   |   Hints used {res['hints']}   |   "
               f"Time {res['time'] // 60}m {res['time'] % 60:02d}s", (r.centerx, r.y + 246), F["small"], INK, "center")
        txt(s, "WHAT THE CASE FILE RECORDS", (r.x + 40, r.y + 286), F["mono"], RED)
        y = r.y + 316
        for k, v in [("Primary subject", c["subject"]), ("Category", c["category"]),
                     ("Period", c["period"]), ("Legal outcome", c["outcome"])]:
            if v:
                txt(s, k.upper() + ":", (r.x + 40, y), F["mono_s"], (90, 72, 50))
                y = para(s, v, r.x + 210, y - 3, r.w - 250, F["body"], INK, 2, max_lines=2) + 4
        para(s, "Your score measures how well you worked the game's puzzles on this dataset. "
                "It is not a verdict about any real person. " + DISCLAIMER,
             r.x + 40, r.bottom - 150, r.w - 80, F["small"], (90, 72, 50), 3)
        self.ui.button("NEXT CASE FILE", (r.x + 40, r.bottom - 66, 240, 46), lambda: self.go("cases"), "primary")
        self.ui.button("REPLAY THIS CASE", (r.x + 300, r.bottom - 66, 240, 46), lambda: self.start_case(c["id"]), "ghost")
        self.ui.button("MAIN MENU", (r.x + 560, r.bottom - 66, 240, 46), lambda: self.go("menu"), "ghost")

    # ---- dataset status ----------------------------------------------
    def draw_data(self):
        s = self.screen
        self.backdrop(rain=False, city=False)
        self.title_bar("DATASET STATUS")
        r = pygame.Rect(60, 90, W - 120, 580)
        card(s, r)
        y = r.y + 26
        txt(s, "CSV FILES", (r.x + 30, y), F["mono"], RED)
        y += 34
        for name, n, err in self.data.status:
            txt(s, name, (r.x + 30, y), F["mono"], INK)
            txt(s, f"{n} rows", (r.x + 250, y), F["body"], INK)
            txt(s, ("ERROR: " + err) if err else "LOADED", (r.x + 380, y), F["small"], RED if err else (40, 110, 60))
            y += 30
        y += 8
        txt(s, "CASES", (r.x + 30, y), F["mono"], RED)
        y += 32
        for c in self.data.cases:
            n = len(self.data.evidence.get(c["id"], []))
            txt(s, ellipsize(f"{c['id']}  {c['name']}  -  {n} evidence rows", F["small"], r.w - 80), (r.x + 30, y), F["small"], INK)
            y += 24
        y += 10
        txt(s, "MODULES", (r.x + 30, y), F["mono"], RED)
        y += 32
        txt(s, f"similarity.py: {'loaded' if sim else 'NOT loaded'}     similarity_lab.py: "
               f"{'loaded' if SimilarityLab else 'NOT loaded'}     rank_lab.py: "
               f"{'loaded' if RankLab else 'NOT loaded'}", (r.x + 30, y), F["small"], INK)
        y += 30
        if self.data.errors:
            txt(s, "PROBLEMS FOUND", (r.x + 30, y), F["mono"], RED)
            y += 28
            for e in self.data.errors[:5]:
                txt(s, ellipsize(e, F["small"], r.w - 80), (r.x + 30, y), F["small"], RED)
                y += 22
        self.ui.button("BACK", (24, H - 64, 140, 42), lambda: self.go("menu"), "ghost")

    # ---- similarity lab -----------------------------------------------
    def draw_sim(self):
        if self.sim_lab is None:
            self.go("lab")
            return
        self.sim_lab.draw(self.screen)
        self.ui.button("<- BACK TO LAB", (W - 220, 22, 190, 38), lambda: self.go("lab"), "ghost", font=F["smallb"])

    # ---- rank lab -----------------------------------------------------
    def draw_rank(self):
        if self.rank_lab is None:
            self.go("lab")
            return
        self.rank_lab.draw(self.screen)
        self.ui.button("<- BACK TO LAB", (W - 220, 22, 190, 38), lambda: self.go("lab"), "ghost", font=F["smallb"])

    # ------------------------------------------------------------ loop
    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
        pygame.quit()


def main():
    Game().run()
    sys.exit()


if __name__ == "__main__":
    main()