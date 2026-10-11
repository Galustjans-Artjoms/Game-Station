"""
Lane Guard — Neon Rats
Three-lane tower defense. Q/W/E = weapon · 1/2/3 = lane · SPACE/click = place.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field

import pygame

# =====================================================================
# CONFIG
# =====================================================================
CONFIG = {
    "screen": {"w": 960, "h": 580},
    "lanes": 3,
    "base_hp": 20,
    "start_energy": 45,
    "energy_per_sec": 3.5,
    "turret_max_per_lane": 3,
    # Three weapons — different roles (design choice, not just skins)
    "weapons": {
        "pulse": {
            "label": "PULSE",
            "key": "Q",
            "cost": 12,
            "damage": 9,
            "range": 155,
            "cooldown": 0.55,
            "color": "neon_orange",
            "blurb": "balanced coil",
        },
        "needle": {
            "label": "NEEDLE",
            "key": "W",
            "cost": 8,
            "damage": 4,
            "range": 135,
            "cooldown": 0.26,
            "color": "neon_cyan",
            "blurb": "cheap rapid fire",
        },
        "rail": {
            "label": "RAIL",
            "key": "E",
            "cost": 18,
            "damage": 26,
            "range": 230,
            "cooldown": 1.15,
            "pierce": 2,
            "color": "neon_magenta",
            "blurb": "slow heavy pierce",
        },
    },
    "weapon_order": ["pulse", "needle", "rail"],
    "rat": {
        "hp": 18,
        "speed": 55,
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
        "damage_mult": 1.25,
        "range_mult": 1.15,
        "cooldown_mult": 0.85,
        "energy_mult": 1.2,
        "cost_reduce": 2,
    },
    "colors": {
        "bg": (6, 8, 16),
        "lane": (24, 34, 64),
        "neon_cyan": (0, 245, 255),
        "neon_magenta": (255, 45, 149),
        "neon_lime": (80, 255, 90),
        "neon_orange": (255, 150, 20),
        "text": (230, 236, 255),
        "muted": (120, 130, 160),
        "base": (255, 60, 100),
    },
}


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def weapon_def(kind: str) -> dict:
    return CONFIG["weapons"][kind]


def weapon_color(kind: str) -> tuple[int, int, int]:
    return CONFIG["colors"][weapon_def(kind)["color"]]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: float = 3.0
    gravity: float = 0.0


@dataclass
class Floater:
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    life: float = 0.7


@dataclass
class Turret:
    lane: int
    x: float
    y: float
    kind: str
    cooldown: float = 0.0
    flash: float = 0.0
    spawn_pop: float = 0.35


@dataclass
class Rat:
    lane: int
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    phase: float = field(default_factory=lambda: random.random() * math.tau)
    hit_flash: float = 0.0
    spawn_t: float = 0.25


@dataclass
class Bullet:
    x: float
    y: float
    tx: float
    ty: float
    damage: float
    kind: str
    pierce_left: int = 0
    life: float = 0.45
    trail: list[tuple[float, float]] = field(default_factory=list)
    hit_ids: set[int] = field(default_factory=set)


@dataclass
class GameState:
    base_hp: float = CONFIG["base_hp"]
    energy: float = CONFIG["start_energy"]
    wave: int = 0
    phase: str = "idle"
    spawn_left: int = 0
    spawn_timer: float = 0.0
    turrets: list[Turret] = field(default_factory=list)
    rats: list[Rat] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    floaters: list[Floater] = field(default_factory=list)
    selected_lane: int = 1
    selected_weapon: str = "pulse"
    message: str = "Q/W/E weapons · 1/2/3 lanes · SPACE place"
    damage_mult: float = 1.0
    range_mult: float = 1.0
    cooldown_mult: float = 1.0
    energy_mult: float = 1.0
    cost_off: int = 0
    upgrade_options: list[str] = field(default_factory=list)
    kills: int = 0
    shake: float = 0.0
    time: float = 0.0
    banner_t: float = 0.0
    banner_text: str = ""
    base_pulse: float = 0.0
    spawn_fx: float = 0.0


UPGRADE_LABELS = {
    "damage": "Overclock +25% damage",
    "range": "Long lens +15% range",
    "firerate": "Coolant −15% cooldown",
    "energy": "Solar drip +20% energy/s",
    "cheap": "Discount −2 all turret costs",
}


def lane_y(i: int, h: int) -> float:
    top = 100
    bottom = h - 70
    band = (bottom - top) / CONFIG["lanes"]
    return top + band * i + band * 0.5


def current_cost(gs: GameState, kind: str | None = None) -> int:
    kind = kind or gs.selected_weapon
    return max(4, weapon_def(kind)["cost"] - gs.cost_off)


def burst(
    gs: GameState,
    x: float,
    y: float,
    color: tuple[int, int, int],
    n: int = 12,
    speed: float = 120,
    life: float = 0.45,
    size: float = 3.0,
) -> None:
    for _ in range(n):
        ang = random.random() * math.tau
        sp = speed * (0.4 + random.random())
        gs.particles.append(
            Particle(
                x=x,
                y=y,
                vx=math.cos(ang) * sp,
                vy=math.sin(ang) * sp,
                life=life * (0.6 + random.random() * 0.5),
                max_life=life,
                color=color,
                size=size * (0.6 + random.random()),
                gravity=40,
            )
        )


def start_wave(gs: GameState) -> None:
    gs.wave += 1
    wcfg = CONFIG["waves"]
    gs.spawn_left = wcfg["base_rats"] + (gs.wave - 1) * wcfg["rats_per_wave"]
    gs.spawn_timer = 0.2
    gs.phase = "spawn"
    gs.message = f"WAVE {gs.wave} — neon rats in the pipes"
    gs.banner_text = f"WAVE {gs.wave}"
    gs.banner_t = 1.4
    gs.spawn_fx = 0.6


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
    gs.banner_text = "UPGRADE CORE"
    gs.banner_t = 0.9


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
        gs.cost_off += u["cost_reduce"]
    gs.upgrade_options.clear()
    burst(gs, CONFIG["screen"]["w"] / 2, CONFIG["screen"]["h"] / 2, CONFIG["colors"]["neon_cyan"], n=28, speed=220)
    if gs.wave >= CONFIG["waves"]["count"]:
        gs.phase = "win"
        gs.message = "CITY SECURE. Neon rats retreated."
        gs.banner_text = "VICTORY"
        gs.banner_t = 2.0
    else:
        start_wave(gs)


def place_turret(gs: GameState, lane: int, h: int) -> None:
    if gs.phase in ("upgrade", "win", "lose"):
        return
    if gs.phase not in ("idle", "spawn", "clear"):
        return
    cost = current_cost(gs)
    if gs.energy < cost:
        gs.message = "Not enough energy"
        return
    count = sum(1 for t in gs.turrets if t.lane == lane)
    if count >= CONFIG["turret_max_per_lane"]:
        gs.message = "Lane full"
        return
    y = lane_y(lane, h)
    x = 110 + count * 72
    kind = gs.selected_weapon
    gs.turrets.append(Turret(lane=lane, x=x, y=y, kind=kind))
    gs.energy -= cost
    label = weapon_def(kind)["label"]
    gs.message = f"{label} online · lane {lane + 1}"
    burst(gs, x, y, weapon_color(kind), n=16, speed=160, life=0.35)


def glow_circle(
    surf: pygame.Surface,
    pos: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    layers: int = 4,
    core: bool = True,
) -> None:
    for i in range(layers, 0, -1):
        shade = tuple(int(max(0, min(255, ch * (0.18 + 0.14 * i)))) for ch in color)
        pygame.draw.circle(surf, shade, pos, radius + i * 4, 2)
    pygame.draw.circle(surf, color, pos, radius)
    if core:
        pygame.draw.circle(surf, (255, 255, 255), pos, max(2, radius // 3))


def draw_pipes(surf: pygame.Surface, w: int, h: int, t: float, C: dict) -> None:
    for i in range(CONFIG["lanes"]):
        y = int(lane_y(i, h))
        for k in range(5):
            px = w - 30 - k * 18
            pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 3 + i + k))
            col = tuple(int(c * pulse) for c in C["neon_magenta"])
            pygame.draw.circle(surf, col, (px, y), 10, 1)
        offset = int((t * 80) % 28)
        for x in range(80 + offset, w - 40, 28):
            pygame.draw.line(surf, (30, 50, 90), (x, y), (x + 12, y), 1)


def draw_rat(surf: pygame.Surface, rat: Rat, color: tuple[int, int, int], t: float) -> None:
    run = math.sin(rat.phase * 2.2)
    bob = math.sin(rat.phase) * 3
    x, y = int(rat.x), int(rat.y + bob)
    r = CONFIG["rat"]["radius"]
    scale = clamp(1.0 - rat.spawn_t * 2.2, 0.55, 1.0)
    rr = max(6, int(r * scale))

    for i in range(4):
        tx = int(rat.x + 10 + i * 7)
        alpha_col = tuple(max(0, c // (3 + i)) for c in color)
        pygame.draw.ellipse(surf, alpha_col, (tx - 6, y - 4, 12 - i, 8), 1)

    body = pygame.Rect(0, 0, rr * 2 + 10, rr + 8)
    body.center = (x, y)
    fill = tuple(max(0, c // 4) for c in color)
    if rat.hit_flash > 0:
        fill = (255, 255, 255)
        color = (255, 255, 255)
    pygame.draw.ellipse(surf, fill, body.inflate(-2, -2))
    for g in range(3, 0, -1):
        shade = tuple(int(c * (0.25 + 0.2 * g)) for c in color)
        pygame.draw.ellipse(surf, shade, body.inflate(g * 3, g * 2), 1)
    pygame.draw.ellipse(surf, color, body, 2)

    ear_y = y - rr + 1 + int(run)
    pygame.draw.circle(surf, color, (x - 7, ear_y), 5, 2)
    pygame.draw.circle(surf, color, (x + 3, ear_y), 5, 2)
    eye = CONFIG["colors"]["neon_lime"] if (int(t * 8) % 17) else (40, 80, 40)
    pygame.draw.circle(surf, eye, (x - 1, y - 1), 2)
    pygame.draw.circle(surf, eye, (x + 6, y - 1), 2)
    leg = int(4 * run)
    pygame.draw.line(surf, color, (x - 4, y + rr // 2), (x - 8, y + rr // 2 + leg), 2)
    pygame.draw.line(surf, color, (x + 4, y + rr // 2), (x + 8, y + rr // 2 - leg), 2)
    pygame.draw.arc(surf, color, pygame.Rect(x + rr - 4, y - 8 + leg, 30, 20), 0.1, 2.8, 2)

    ratio = clamp(rat.hp / rat.max_hp, 0, 1)
    pygame.draw.rect(surf, (40, 40, 55), (x - 14, y - rr - 12, 28, 4))
    pygame.draw.rect(surf, color, (x - 14, y - rr - 12, int(28 * ratio), 4))


def draw_turret(surf: pygame.Surface, t: Turret, selected: bool, pulse: float, C: dict, range_mult: float) -> None:
    wd = weapon_def(t.kind)
    color = weapon_color(t.kind)
    lime = C["neon_lime"]
    pop = 1.0 + t.spawn_pop * 0.9
    x, y = int(t.x), int(t.y)
    hum = 0.65 + 0.35 * math.sin(pulse * 5 + t.x * 0.05)
    range_px = wd["range"] * range_mult

    if selected:
        pygame.draw.circle(surf, tuple(max(0, c // 5) for c in color), (x, y), int(range_px), 1)

    # pad
    pad_w, pad_h = int(36 * pop), int(12 * pop)
    pygame.draw.ellipse(surf, (20, 24, 40), (x - pad_w // 2, y + 7, pad_w, pad_h))

    if t.kind == "needle":
        # slim triangle needle gun
        body = [(x - 8, y + 8), (x - 8, y - 8), (x + 18, y)]
        pygame.draw.polygon(surf, tuple(int(c * 0.25) for c in color), body)
        pygame.draw.polygon(surf, color, body, 2)
        # twin barrels
        pygame.draw.line(surf, color, (x + 10, y - 3), (x + 28, y - 3), 2)
        pygame.draw.line(surf, color, (x + 10, y + 3), (x + 28, y + 3), 2)
        mx = x + 30
        pygame.draw.circle(surf, color, (mx, y - 3), 2)
        pygame.draw.circle(surf, color, (mx, y + 3), 2)
        # vent ticks
        for i in range(3):
            pygame.draw.line(surf, C["neon_cyan"], (x - 2 + i * 4, y - 10), (x - 2 + i * 4, y - 6), 1)
    elif t.kind == "rail":
        # chunky railgun slab + long barrel
        pygame.draw.rect(surf, tuple(int(c * 0.22) for c in color), (x - 14, y - 12, 28, 24), border_radius=4)
        pygame.draw.rect(surf, color, (x - 14, y - 12, 28, 24), 2, border_radius=4)
        # capacitor rings
        for i in range(3):
            pygame.draw.circle(surf, color, (x - 4 + i * 5, y), 5, 1)
        barrel = int(34 * pop + t.flash * 8)
        pygame.draw.rect(surf, tuple(int(c * 0.4) for c in color), (x + 10, y - 5, barrel, 10), border_radius=2)
        pygame.draw.rect(surf, color, (x + 10, y - 5, barrel, 10), 2, border_radius=2)
        pygame.draw.line(surf, lime, (x + 14, y), (x + 10 + barrel - 4, y), 1)
        mx = x + 12 + barrel
        pygame.draw.circle(surf, color, (mx, y), 5, 2)
        pygame.draw.circle(surf, (255, 200, 230), (mx, y), 2)
    else:
        # pulse: hex + coil barrel (default)
        hr = int(13 * pop)
        hex_pts = [
            (
                x + int(hr * math.cos(math.radians(a + pulse * 25))),
                y + int(hr * math.sin(math.radians(a + pulse * 25))),
            )
            for a in range(0, 360, 60)
        ]
        pygame.draw.polygon(surf, tuple(int(c * 0.2 * hum) for c in color), hex_pts)
        pygame.draw.polygon(surf, color, hex_pts, 2)
        for a in range(0, 360, 45):
            ang = math.radians(a + pulse * 140)
            pygame.draw.circle(
                surf,
                C["neon_cyan"],
                (x + int(math.cos(ang) * (hr + 5)), y + int(math.sin(ang) * (hr + 5))),
                2,
            )
        barrel = int(22 * pop + t.flash * 6)
        pygame.draw.rect(surf, tuple(int(c * 0.35) for c in color), (x + 6, y - 4, barrel, 8), border_radius=3)
        pygame.draw.rect(surf, color, (x + 6, y - 4, barrel, 8), 2, border_radius=3)
        mx = x + 8 + barrel
        pygame.draw.circle(surf, color, (mx, y), 4, 2)

    # shared core + LED + flash
    glow_circle(surf, (x, y - (2 if t.kind == "rail" else 0)), int(4 + 2 * hum + t.flash * 3), color, layers=3)
    led = lime if t.cooldown < 0.08 else ((255, 80, 80) if t.cooldown > weapon_def(t.kind)["cooldown"] * 0.6 else C["neon_cyan"])
    pygame.draw.circle(surf, led, (x - 10, y - 12), 3)

    if t.flash > 0:
        fl = t.flash
        tip_x = x + (36 if t.kind == "rail" else 28 if t.kind == "needle" else 30)
        pygame.draw.circle(surf, lime, (tip_x, y), int(5 + fl * 12))
        pygame.draw.circle(surf, (255, 255, 220), (tip_x + 2, y), int(2 + fl * 5))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Lane Guard — Neon Rats")
    w = CONFIG["screen"]["w"]
    h = CONFIG["screen"]["h"]
    screen = pygame.display.set_mode((w, h))
    canvas = pygame.Surface((w, h))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    font_big = pygame.font.SysFont("consolas", 32, bold=True)
    font_small = pygame.font.SysFont("consolas", 14)

    gs = GameState()
    C = CONFIG["colors"]
    weapon_keys = {"q": "pulse", "w": "needle", "e": "rail"}

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        gs.time += dt
        gs.shake = max(0.0, gs.shake - dt * 2.8)
        gs.banner_t = max(0.0, gs.banner_t - dt)
        gs.spawn_fx = max(0.0, gs.spawn_fx - dt)
        gs.base_pulse = max(0.0, gs.base_pulse - dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e):
                    name = weapon_keys[pygame.key.name(event.key)]
                    gs.selected_weapon = name
                    wd = weapon_def(name)
                    gs.message = f"{wd['label']} selected — {wd['blurb']} · cost {current_cost(gs)}"
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    if gs.phase == "upgrade" and gs.upgrade_options:
                        apply_upgrade(gs, gs.upgrade_options[0])
                    else:
                        gs.selected_lane = 0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    if gs.phase == "upgrade" and len(gs.upgrade_options) > 1:
                        apply_upgrade(gs, gs.upgrade_options[1])
                    else:
                        gs.selected_lane = 1
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    if gs.phase == "upgrade" and len(gs.upgrade_options) > 2:
                        apply_upgrade(gs, gs.upgrade_options[2])
                    else:
                        gs.selected_lane = 2
                elif event.key == pygame.K_SPACE:
                    if gs.phase in ("idle", "spawn", "clear"):
                        place_turret(gs, gs.selected_lane, h)
                        if gs.phase == "idle":
                            start_wave(gs)
                elif event.key == pygame.K_RETURN and gs.phase == "idle":
                    start_wave(gs)
                elif event.key == pygame.K_r and gs.phase in ("win", "lose"):
                    gs = GameState()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if gs.phase == "upgrade":
                    continue
                _, my = event.pos
                best = min(range(CONFIG["lanes"]), key=lambda i: abs(lane_y(i, h) - my))
                gs.selected_lane = best
                place_turret(gs, best, h)
                if gs.phase == "idle":
                    start_wave(gs)

        if gs.phase not in ("upgrade", "win", "lose", "idle"):
            gs.energy = min(99, gs.energy + CONFIG["energy_per_sec"] * gs.energy_mult * dt)

        if gs.phase == "spawn":
            gs.spawn_timer -= dt
            if gs.spawn_left > 0 and gs.spawn_timer <= 0:
                lane = random.randrange(CONFIG["lanes"])
                hp, speed = rat_stats(gs.wave)
                rx, ry = w - 40, lane_y(lane, h)
                gs.rats.append(Rat(lane=lane, x=rx, y=ry, hp=hp, max_hp=hp, speed=speed))
                burst(gs, rx, ry, C["neon_magenta"], n=8, speed=90, life=0.25, size=2)
                gs.spawn_left -= 1
                gs.spawn_timer = spawn_gap(gs.wave)
                gs.spawn_fx = 0.25
            if gs.spawn_left <= 0 and not gs.rats:
                gs.phase = "clear"

        if gs.phase in ("spawn", "clear"):
            for rat in gs.rats:
                rat.phase += dt * 12
                rat.x -= rat.speed * dt
                rat.hit_flash = max(0.0, rat.hit_flash - dt * 4)
                rat.spawn_t = max(0.0, rat.spawn_t - dt)
                if random.random() < dt * 8:
                    gs.particles.append(
                        Particle(rat.x + 8, rat.y, 30, random.uniform(-20, 20), 0.25, 0.25, C["neon_magenta"], 2)
                    )

            survivors: list[Rat] = []
            for rat in gs.rats:
                if rat.x < 70:
                    gs.base_hp -= CONFIG["rat"]["damage_to_base"]
                    gs.message = "Base chewed! (−HP)"
                    gs.shake = max(gs.shake, 0.45)
                    gs.base_pulse = 0.5
                    burst(gs, 55, rat.y, C["base"], n=18, speed=200)
                    if gs.base_hp <= 0:
                        gs.phase = "lose"
                        gs.message = "RATS WON. Press R to retry."
                        gs.banner_text = "DEFEAT"
                        gs.banner_t = 2.0
                        gs.shake = 0.8
                else:
                    survivors.append(rat)
            gs.rats = survivors

            for tur in gs.turrets:
                wd = weapon_def(tur.kind)
                dmg = wd["damage"] * gs.damage_mult
                rng = wd["range"] * gs.range_mult
                cd = wd["cooldown"] * gs.cooldown_mult
                tur.cooldown = max(0.0, tur.cooldown - dt)
                tur.flash = max(0.0, tur.flash - dt * 5)
                tur.spawn_pop = max(0.0, tur.spawn_pop - dt)
                if tur.cooldown > 0:
                    continue
                candidates = [
                    r for r in gs.rats if r.lane == tur.lane and abs(r.x - tur.x) <= rng and r.x > tur.x - 20
                ]
                if not candidates:
                    continue
                target = min(candidates, key=lambda r: r.x)
                pierce = int(wd.get("pierce", 0))
                tip = 34 if tur.kind == "rail" else 28 if tur.kind == "needle" else 30
                gs.bullets.append(
                    Bullet(
                        tur.x + tip,
                        tur.y,
                        target.x,
                        target.y,
                        dmg,
                        kind=tur.kind,
                        pierce_left=pierce,
                        life=0.55 if tur.kind == "rail" else 0.4,
                    )
                )
                tur.cooldown = cd
                tur.flash = 0.3
                burst(gs, tur.x + tip, tur.y, weapon_color(tur.kind), n=8, speed=110, life=0.2, size=2.5)

            alive_b: list[Bullet] = []
            for b in gs.bullets:
                b.life -= dt
                b.trail.append((b.x, b.y))
                if len(b.trail) > (14 if b.kind == "rail" else 8):
                    b.trail.pop(0)
                speed = 14 if b.kind == "needle" else 10 if b.kind == "pulse" else 8
                b.x += (b.tx - b.x) * min(1.0, dt * (speed + 6))
                # keep flying right for pierce rails
                if b.kind == "rail":
                    b.x += 420 * dt
                    b.tx = b.x + 40
                else:
                    b.y += (b.ty - b.y) * min(1.0, dt * 20)

                col = weapon_color(b.kind)
                hits_this_frame = []
                for r in gs.rats:
                    rid = id(r)
                    if rid in b.hit_ids:
                        continue
                    if math.hypot(r.x - b.x, r.y - b.y) < CONFIG["rat"]["radius"] + 7:
                        hits_this_frame.append(r)

                if hits_this_frame:
                    # nearest hit
                    hit = min(hits_this_frame, key=lambda r: abs(r.x - b.x))
                    b.hit_ids.add(id(hit))
                    hit.hp -= b.damage
                    hit.hit_flash = 0.15
                    burst(gs, b.x, b.y, col, n=10, speed=140, life=0.3)
                    gs.floaters.append(Floater(hit.x, hit.y - 18, f"-{int(b.damage)}", col))
                    if hit.hp <= 0:
                        if hit in gs.rats:
                            gs.rats.remove(hit)
                        gs.energy = min(99, gs.energy + CONFIG["rat"]["reward"])
                        gs.kills += 1
                        gs.shake = max(gs.shake, 0.18)
                        burst(gs, hit.x, hit.y, C["neon_magenta"], n=22, speed=220, life=0.5, size=3.5)
                        gs.floaters.append(Floater(hit.x, hit.y - 28, "+ENERGY", C["neon_cyan"]))
                    if b.pierce_left > 0:
                        b.pierce_left -= 1
                        alive_b.append(b)
                    # else bullet dies
                elif b.life > 0 and b.x < w + 40:
                    alive_b.append(b)
            gs.bullets = alive_b

            if gs.phase == "clear" and not gs.rats and gs.spawn_left <= 0:
                offer_upgrades(gs)

        alive_p: list[Particle] = []
        for p in gs.particles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.gravity * dt
            p.vx *= 0.98
            if p.life > 0:
                alive_p.append(p)
        gs.particles = alive_p

        alive_f: list[Floater] = []
        for f in gs.floaters:
            f.life -= dt
            f.y -= 28 * dt
            if f.life > 0:
                alive_f.append(f)
        gs.floaters = alive_f

        # ---- draw ----
        canvas.fill(C["bg"])
        for y in range(0, h, 3):
            pygame.draw.line(canvas, (10, 12, 22), (0, y), (w, y), 1)
        scroll = int((gs.time * 25) % 48)
        for x in range(-scroll, w, 48):
            pygame.draw.line(canvas, (16, 22, 40), (x, 90), (x, h - 55), 1)
        draw_pipes(canvas, w, h, gs.time, C)

        title_glow = 0.75 + 0.25 * math.sin(gs.time * 3)
        canvas.blit(font_big.render("LANE GUARD", True, tuple(int(c * title_glow) for c in C["neon_cyan"])), (18, 10))
        canvas.blit(font_small.render("NEON RATS", True, C["neon_magenta"]), (230, 20))

        wd = weapon_def(gs.selected_weapon)
        wcol = weapon_color(gs.selected_weapon)
        hud = (
            f"BASE {max(0, int(gs.base_hp))}  ENERGY {int(gs.energy)}  "
            f"WAVE {gs.wave}/{CONFIG['waves']['count']}  KILLS {gs.kills}"
        )
        canvas.blit(font.render(hud, True, C["text"]), (18, 50))
        # weapon bar
        bx = 18
        for kind in CONFIG["weapon_order"]:
            d = weapon_def(kind)
            active = kind == gs.selected_weapon
            col = weapon_color(kind) if active else C["muted"]
            cost = current_cost(gs, kind)
            label = f"[{d['key']}] {d['label']} ${cost}"
            canvas.blit(font_small.render(label, True, col), (bx, 74))
            if active:
                pygame.draw.rect(canvas, col, (bx - 4, 72, font_small.size(label)[0] + 8, 18), 1)
            bx += font_small.size(label)[0] + 18

        canvas.blit(font_small.render(gs.message, True, C["muted"]), (18, h - 26))

        pulse = 1 + gs.base_pulse * 0.5
        bw = int(18 * pulse)
        base_col = C["base"] if gs.base_pulse <= 0 else (255, 200, 220)
        for i in range(5, 0, -1):
            shade = tuple(int(c * (0.2 + 0.1 * i)) for c in base_col)
            pygame.draw.rect(canvas, shade, (40 - i, 88 - i, bw + i * 2, h - 160 + i * 2), 1)
        pygame.draw.rect(canvas, base_col, (42, 90, bw - 2, h - 164), 2)

        for i in range(CONFIG["lanes"]):
            y = lane_y(i, h)
            selected = i == gs.selected_lane
            col = C["neon_cyan"] if selected else C["lane"]
            pygame.draw.line(canvas, col, (70, int(y)), (w - 30, int(y)), 3 if selected else 1)
            canvas.blit(font_small.render(f"LANE {i + 1}", True, col), (74, int(y) - 24))

        if gs.spawn_fx > 0:
            gate = pygame.Surface((40, h - 160), pygame.SRCALPHA)
            gate.fill((255, 45, 149, int(120 * gs.spawn_fx)))
            canvas.blit(gate, (w - 50, 90))

        for tur in gs.turrets:
            draw_turret(canvas, tur, tur.lane == gs.selected_lane, gs.time, C, gs.range_mult)
        for rat in gs.rats:
            draw_rat(canvas, rat, C["neon_magenta"], gs.time)

        for b in gs.bullets:
            col = weapon_color(b.kind)
            if len(b.trail) >= 2:
                pygame.draw.lines(canvas, tuple(max(0, c // 3) for c in col), False, [(int(x), int(y)) for x, y in b.trail], 2 if b.kind != "rail" else 3)
            rad = 5 if b.kind == "rail" else 2 if b.kind == "needle" else 3
            glow_circle(canvas, (int(b.x), int(b.y)), rad, col, layers=2)

        for p in gs.particles:
            a = clamp(p.life / p.max_life, 0, 1)
            pygame.draw.circle(canvas, tuple(int(c * a) for c in p.color), (int(p.x), int(p.y)), max(1, int(p.size * a)))
        for f in gs.floaters:
            a = clamp(f.life / 0.7, 0, 1)
            canvas.blit(font_small.render(f.text, True, tuple(int(c * a) for c in f.color)), (int(f.x) - 10, int(f.y)))

        if gs.phase == "idle":
            tip = font.render("Q Pulse · W Needle · E Rail · 1/2/3 lane · SPACE place · ENTER start", True, C["neon_lime"])
            canvas.blit(tip, (18, h - 52))

        if gs.banner_t > 0 and gs.banner_text:
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            fade = clamp(gs.banner_t / 0.4, 0, 1) if gs.banner_t < 0.4 else 1.0
            overlay.fill((0, 0, 0, int(140 * fade)))
            canvas.blit(overlay, (0, 0))
            text = font_big.render(gs.banner_text, True, C["neon_cyan"])
            canvas.blit(text, text.get_rect(center=(w // 2, h // 2 - 20)))

        if gs.phase == "upgrade":
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            canvas.blit(overlay, (0, 0))
            canvas.blit(font_big.render("UPGRADE CORE", True, C["neon_cyan"]), (w // 2 - 120, 130))
            for idx, key in enumerate(gs.upgrade_options):
                pulse = 0.7 + 0.3 * math.sin(gs.time * 5 + idx)
                col = tuple(int(c * pulse) for c in C["neon_orange"])
                canvas.blit(font.render(f"[{idx + 1}] {UPGRADE_LABELS[key]}", True, col), (w // 2 - 180, 200 + idx * 40))

        if gs.phase in ("win", "lose"):
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            canvas.blit(overlay, (0, 0))
            col = C["neon_lime"] if gs.phase == "win" else C["neon_magenta"]
            canvas.blit(font_big.render(gs.message, True, col), (60, h // 2 - 24))
            canvas.blit(font.render("Press R to restart", True, C["text"]), (60, h // 2 + 24))

        ox = int(random.uniform(-1, 1) * gs.shake * 10) if gs.shake > 0 else 0
        oy = int(random.uniform(-1, 1) * gs.shake * 10) if gs.shake > 0 else 0
        screen.fill((0, 0, 0))
        screen.blit(canvas, (ox, oy))
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
