"""
Lane Guard — Neon Rats
Three-lane tower defense prototype. Balance knobs live in CONFIG.
Controls: 1/2/3 select lane · SPACE / click place turret · U upgrade menu after wave
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field

import pygame

# =====================================================================
# CONFIG — every balance / tuning number lives here (design playtest).
# =====================================================================
CONFIG = {
    "screen": {"w": 900, "h": 560},
    "lanes": 3,
    "base_hp": 20,
    "start_energy": 40,
    "energy_per_sec": 3.5,
    "turret_cost": 12,
    "turret_max_per_lane": 3,
    "turret": {
        "damage": 8,
        "range": 160,
        "cooldown": 0.55,
        "hp": 1,  # cosmetic; rats don't attack turrets in v1
    },
    "rat": {
        "hp": 18,
        "speed": 55,  # px/sec toward the base (left)
        "damage_to_base": 2,
        "reward": 5,
        "radius": 14,
    },
    "waves": {
        "count": 8,
        "base_rats": 5,
        "rats_per_wave": 2,
        "hp_scale": 0.15,
        "speed_scale": 0.04,
        "spawn_gap": 0.85,
        "spawn_gap_per_wave": -0.04,
        "min_spawn_gap": 0.35,
    },
    "upgrades": {
        # applied as multiplicative / additive when picked
        "damage_mult": 1.25,
        "range_mult": 1.15,
        "cooldown_mult": 0.85,
        "energy_mult": 1.2,
        "cost_reduce": 2,
    },
    "colors": {
        "bg": (8, 10, 18),
        "panel": (16, 20, 36),
        "lane": (20, 28, 52),
        "neon_cyan": (0, 245, 255),
        "neon_magenta": (255, 45, 149),
        "neon_lime": (57, 255, 20),
        "neon_orange": (255, 140, 0),
        "text": (230, 236, 255),
        "muted": (120, 130, 160),
        "base": (255, 60, 100),
    },
}


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


@dataclass
class Turret:
    lane: int
    x: float
    y: float
    cooldown: float = 0.0


@dataclass
class Rat:
    lane: int
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    phase: float = field(default_factory=lambda: random.random() * math.tau)


@dataclass
class Bullet:
    x: float
    y: float
    tx: float
    ty: float
    damage: float
    life: float = 0.35


@dataclass
class GameState:
    base_hp: float = CONFIG["base_hp"]
    energy: float = CONFIG["start_energy"]
    wave: int = 0
    phase: str = "idle"  # idle | spawn | clear | upgrade | win | lose
    spawn_left: int = 0
    spawn_timer: float = 0.0
    turrets: list[Turret] = field(default_factory=list)
    rats: list[Rat] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)
    selected_lane: int = 1
    message: str = "NEON RATS incoming. Place turrets (1/2/3 + SPACE)."
    damage_mult: float = 1.0
    range_mult: float = 1.0
    cooldown_mult: float = 1.0
    energy_mult: float = 1.0
    turret_cost: int = CONFIG["turret_cost"]
    upgrade_options: list[str] = field(default_factory=list)
    kills: int = 0


UPGRADE_LABELS = {
    "damage": "Overclock +25% damage",
    "range": "Long lens +15% range",
    "firerate": "Coolant −15% cooldown",
    "energy": "Solar drip +20% energy/s",
    "cheap": "Discount −2 turret cost",
}


def lane_y(i: int, h: int) -> float:
    # i in 0..lanes-1
    top = 90
    bottom = h - 70
    band = (bottom - top) / CONFIG["lanes"]
    return top + band * i + band * 0.5


def start_wave(gs: GameState) -> None:
    gs.wave += 1
    wcfg = CONFIG["waves"]
    gs.spawn_left = wcfg["base_rats"] + (gs.wave - 1) * wcfg["rats_per_wave"]
    gs.spawn_timer = 0.2
    gs.phase = "spawn"
    gs.message = f"WAVE {gs.wave} — neon rats in the pipes"


def rat_stats(wave: int) -> tuple[float, float]:
    r = CONFIG["rat"]
    w = CONFIG["waves"]
    hp = r["hp"] * (1 + (wave - 1) * w["hp_scale"])
    speed = r["speed"] * (1 + (wave - 1) * w["speed_scale"])
    return hp, speed


def spawn_gap(wave: int) -> float:
    w = CONFIG["waves"]
    return max(w["min_spawn_gap"], w["spawn_gap"] + (wave - 1) * w["spawn_gap_per_wave"])


def offer_upgrades(gs: GameState) -> None:
    keys = list(UPGRADE_LABELS.keys())
    random.shuffle(keys)
    gs.upgrade_options = keys[:3]
    gs.phase = "upgrade"
    gs.message = "Pick upgrade: press 1 / 2 / 3"


def apply_upgrade(gs: GameState, key: str) -> None:
    u = CONFIG["upgrades"]
    if key == "damage":
        gs.damage_mult *= u["damage_mult"]
    elif key == "range":
        gs.range_mult *= u["range_mult"]
    elif key == "firerate":
        gs.cooldown_mult *= u["cooldown_mult"]
    elif key == "energy":
        gs.energy_mult *= u["energy_mult"]
    elif key == "cheap":
        gs.turret_cost = max(6, gs.turret_cost - u["cost_reduce"])
    gs.upgrade_options.clear()
    if gs.wave >= CONFIG["waves"]["count"]:
        gs.phase = "win"
        gs.message = "CITY SECURE. Neon rats retreated."
    else:
        start_wave(gs)


def place_turret(gs: GameState, lane: int, w: int, h: int) -> None:
    if gs.phase in ("upgrade", "win", "lose", "idle"):
        if gs.phase == "idle":
            pass
        elif gs.phase != "spawn" and gs.phase != "clear":
            return
    if gs.energy < gs.turret_cost:
        gs.message = "Not enough energy"
        return
    count = sum(1 for t in gs.turrets if t.lane == lane)
    if count >= CONFIG["turret_max_per_lane"]:
        gs.message = "Lane full"
        return
    y = lane_y(lane, h)
    # place from left base toward the right, spaced
    x = 110 + count * 70
    gs.turrets.append(Turret(lane=lane, x=x, y=y))
    gs.energy -= gs.turret_cost
    gs.message = f"Turret online · lane {lane + 1}"


def draw_glow_circle(surf: pygame.Surface, pos: tuple[int, int], radius: int, color: tuple[int, int, int], layers: int = 3) -> None:
    for i in range(layers, 0, -1):
        a = 40 // i
        c = (*color, a) if False else color
        # fake glow: darker outer rings
        shade = tuple(max(0, int(ch * (0.25 + 0.25 * i))) for ch in color)
        pygame.draw.circle(surf, shade, pos, radius + i * 4, 2)
    pygame.draw.circle(surf, color, pos, radius)
    pygame.draw.circle(surf, (255, 255, 255), pos, max(2, radius // 3))


def draw_rat(surf: pygame.Surface, rat: Rat, color: tuple[int, int, int]) -> None:
    # neon rat silhouette: body + ears + glowing eyes + tail
    x, y = int(rat.x), int(rat.y)
    bob = math.sin(rat.phase) * 2
    yb = int(y + bob)
    r = CONFIG["rat"]["radius"]
    body = pygame.Rect(0, 0, r * 2 + 8, r + 6)
    body.center = (x, yb)
    pygame.draw.ellipse(surf, color, body, 2)
    # fill faint
    fill = tuple(max(0, c // 5) for c in color)
    pygame.draw.ellipse(surf, fill, body.inflate(-4, -4))
    # ears
    pygame.draw.circle(surf, color, (x - 6, yb - r + 2), 4, 1)
    pygame.draw.circle(surf, color, (x + 2, yb - r + 2), 4, 1)
    # eyes
    pygame.draw.circle(surf, CONFIG["colors"]["neon_lime"], (x - 2, yb - 2), 2)
    pygame.draw.circle(surf, CONFIG["colors"]["neon_lime"], (x + 5, yb - 2), 2)
    # tail
    pygame.draw.arc(
        surf,
        color,
        pygame.Rect(x + r - 2, yb - 6, 28, 18),
        0.2,
        2.6,
        2,
    )
    # hp pip
    ratio = clamp(rat.hp / rat.max_hp, 0, 1)
    pygame.draw.rect(surf, (40, 40, 50), (x - 12, yb - r - 10, 24, 3))
    pygame.draw.rect(surf, color, (x - 12, yb - r - 10, int(24 * ratio), 3))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Lane Guard — Neon Rats")
    w = CONFIG["screen"]["w"]
    h = CONFIG["screen"]["h"]
    screen = pygame.display.set_mode((w, h))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    font_big = pygame.font.SysFont("consolas", 28, bold=True)
    font_small = pygame.font.SysFont("consolas", 14)

    gs = GameState()
    C = CONFIG["colors"]

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    if gs.phase == "upgrade":
                        apply_upgrade(gs, gs.upgrade_options[0])
                    else:
                        gs.selected_lane = 0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    if gs.phase == "upgrade":
                        apply_upgrade(gs, gs.upgrade_options[1])
                    else:
                        gs.selected_lane = 1
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    if gs.phase == "upgrade":
                        apply_upgrade(gs, gs.upgrade_options[2])
                    else:
                        gs.selected_lane = 2
                elif event.key == pygame.K_SPACE:
                    if gs.phase in ("idle", "spawn", "clear"):
                        place_turret(gs, gs.selected_lane, w, h)
                        if gs.phase == "idle":
                            start_wave(gs)
                elif event.key == pygame.K_RETURN and gs.phase == "idle":
                    start_wave(gs)
                elif event.key == pygame.K_r and gs.phase in ("win", "lose"):
                    gs = GameState()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if gs.phase == "upgrade":
                    continue
                mx, my = event.pos
                # pick lane by Y
                best = min(range(CONFIG["lanes"]), key=lambda i: abs(lane_y(i, h) - my))
                gs.selected_lane = best
                place_turret(gs, best, w, h)
                if gs.phase == "idle":
                    start_wave(gs)

        # ---- update ----
        if gs.phase not in ("upgrade", "win", "lose", "idle"):
            gs.energy = min(99, gs.energy + CONFIG["energy_per_sec"] * gs.energy_mult * dt)

        if gs.phase == "spawn":
            gs.spawn_timer -= dt
            if gs.spawn_left > 0 and gs.spawn_timer <= 0:
                lane = random.randrange(CONFIG["lanes"])
                hp, speed = rat_stats(gs.wave)
                gs.rats.append(
                    Rat(
                        lane=lane,
                        x=w - 40,
                        y=lane_y(lane, h),
                        hp=hp,
                        max_hp=hp,
                        speed=speed,
                    )
                )
                gs.spawn_left -= 1
                gs.spawn_timer = spawn_gap(gs.wave)
            if gs.spawn_left <= 0 and not gs.rats:
                gs.phase = "clear"

        if gs.phase in ("spawn", "clear"):
            # move rats
            for rat in gs.rats:
                rat.phase += dt * 10
                rat.x -= rat.speed * dt
            # reach base
            survivors = []
            for rat in gs.rats:
                if rat.x < 70:
                    gs.base_hp -= CONFIG["rat"]["damage_to_base"]
                    gs.message = "Base chewed! (−HP)"
                    if gs.base_hp <= 0:
                        gs.phase = "lose"
                        gs.message = "RATS WON. Press R to retry."
                else:
                    survivors.append(rat)
            gs.rats = survivors

            # turrets shoot
            dmg = CONFIG["turret"]["damage"] * gs.damage_mult
            rng = CONFIG["turret"]["range"] * gs.range_mult
            cd = CONFIG["turret"]["cooldown"] * gs.cooldown_mult
            for t in gs.turrets:
                t.cooldown = max(0.0, t.cooldown - dt)
                if t.cooldown > 0:
                    continue
                # nearest rat on same lane in range
                candidates = [
                    r
                    for r in gs.rats
                    if r.lane == t.lane and abs(r.x - t.x) <= rng and r.x > t.x - 20
                ]
                if not candidates:
                    continue
                target = min(candidates, key=lambda r: r.x)
                gs.bullets.append(Bullet(t.x, t.y, target.x, target.y, dmg))
                t.cooldown = cd

            # bullets
            alive_b: list[Bullet] = []
            for b in gs.bullets:
                b.life -= dt
                # lerp toward target
                b.x += (b.tx - b.x) * min(1.0, dt * 18)
                b.y += (b.ty - b.y) * min(1.0, dt * 18)
                hit = None
                for r in gs.rats:
                    if math.hypot(r.x - b.x, r.y - b.y) < CONFIG["rat"]["radius"] + 6:
                        hit = r
                        break
                if hit:
                    hit.hp -= b.damage
                    if hit.hp <= 0:
                        gs.rats.remove(hit)
                        gs.energy = min(99, gs.energy + CONFIG["rat"]["reward"])
                        gs.kills += 1
                elif b.life > 0:
                    alive_b.append(b)
            gs.bullets = alive_b

            if gs.phase == "clear" and not gs.rats and gs.spawn_left <= 0:
                offer_upgrades(gs)

        # ---- draw ----
        screen.fill(C["bg"])
        # scanline vibe
        for y in range(0, h, 4):
            pygame.draw.line(screen, (12, 14, 24), (0, y), (w, y), 1)

        # title
        screen.blit(font_big.render("LANE GUARD", True, C["neon_cyan"]), (18, 14))
        screen.blit(font_small.render("NEON RATS", True, C["neon_magenta"]), (200, 24))

        # HUD
        hud = f"BASE {max(0, int(gs.base_hp))}  ENERGY {int(gs.energy)}  WAVE {gs.wave}/{CONFIG['waves']['count']}  KILLS {gs.kills}  COST {gs.turret_cost}"
        screen.blit(font.render(hud, True, C["text"]), (18, 50))
        screen.blit(font_small.render(gs.message, True, C["muted"]), (18, h - 28))

        # base pillar
        pygame.draw.rect(screen, C["base"], (40, 80, 18, h - 150), 2)
        pygame.draw.rect(screen, (40, 10, 20), (42, 82, 14, h - 154))

        # lanes
        for i in range(CONFIG["lanes"]):
            y = lane_y(i, h)
            col = C["neon_cyan"] if i == gs.selected_lane else C["lane"]
            pygame.draw.line(screen, col, (70, int(y)), (w - 30, int(y)), 2 if i == gs.selected_lane else 1)
            label = font_small.render(f"LANE {i + 1}", True, col)
            screen.blit(label, (74, int(y) - 22))

        for t in gs.turrets:
            draw_glow_circle(screen, (int(t.x), int(t.y)), 10, C["neon_orange"])
            # range hint when selected lane
            if t.lane == gs.selected_lane:
                pygame.draw.circle(
                    screen,
                    (80, 50, 0),
                    (int(t.x), int(t.y)),
                    int(CONFIG["turret"]["range"] * gs.range_mult),
                    1,
                )

        for rat in gs.rats:
            draw_rat(screen, rat, C["neon_magenta"])

        for b in gs.bullets:
            pygame.draw.circle(screen, C["neon_lime"], (int(b.x), int(b.y)), 3)

        if gs.phase == "idle":
            tip = font.render("ENTER or SPACE — start · 1/2/3 lane · click/SPACE place turret", True, C["neon_lime"])
            screen.blit(tip, (18, h - 52))

        if gs.phase == "upgrade":
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            screen.blit(font_big.render("UPGRADE CORE", True, C["neon_cyan"]), (w // 2 - 110, 140))
            for idx, key in enumerate(gs.upgrade_options):
                txt = f"[{idx + 1}] {UPGRADE_LABELS[key]}"
                screen.blit(font.render(txt, True, C["neon_orange"]), (w // 2 - 160, 200 + idx * 36))

        if gs.phase in ("win", "lose"):
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            col = C["neon_lime"] if gs.phase == "win" else C["neon_magenta"]
            screen.blit(font_big.render(gs.message, True, col), (80, h // 2 - 20))
            screen.blit(font.render("Press R to restart", True, C["text"]), (80, h // 2 + 24))

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
