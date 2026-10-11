"""
Lane Guard — Neon Rats
Q Pulse bolts · W Beam laser · E Mortar bombs · A wall · B panic bomb
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
    "turret_max_per_lane": 4,
    "weapons": {
        "pulse": {
            "label": "PULSE",
            "key": "Q",
            "mode": "bolt",
            "cost": 12,
            "damage": 9,
            "range": 190,
            "cooldown": 0.55,
            "hp": 40,
            "color": "neon_orange",
            "blurb": "energy bolts",
        },
        "beam": {
            "label": "BEAM",
            "key": "W",
            "mode": "laser",
            "cost": 14,
            "damage": 5,
            "range": 240,
            "cooldown": 0.14,
            "hp": 32,
            "color": "neon_cyan",
            "blurb": "cutting laser",
        },
        "mortar": {
            "label": "MORTAR",
            "key": "E",
            "mode": "mortar",
            "cost": 16,
            "damage": 24,
            "blast": 78,
            "range": 300,
            "cooldown": 1.25,
            "hp": 50,
            "color": "neon_magenta",
            "blurb": "lob bombs · AOE",
        },
    },
    "weapon_order": ["pulse", "beam", "mortar"],
    "wall": {
        "label": "WALL",
        "key": "A",
        "cost": 10,
        "hp": 70,
        "color": "neon_lime",
        "blurb": "blocks rats · no guns",
    },
    "bomb": {
        "label": "BOMB",
        "key": "B",
        "cost": 14,
        "radius": 95,
        "damage": 32,
        "fuse": 0.85,
        "color": "neon_orange",
        "blurb": "timed blast · all lanes",
    },
    "rat": {
        "hp": 18,
        "speed": 55,
        "damage_to_base": 2,
        "damage_to_structure": 8,
        "chew_cooldown": 0.55,
        "reward": 5,
        "radius": 14,
    },
    "waves": {
        "base_rats": 5,
        "rats_per_wave": 2,
        "hp_scale": 0.15,
        "speed_scale": 0.04,
        "spawn_gap": 0.85,
        "spawn_gap_per_wave": -0.04,
        "min_spawn_gap": 0.35,
    },
    "difficulties": {
        "low": {
            "label": "LOW",
            "blurb": "chill neon stroll",
            "base_hp": 30,
            "start_energy": 55,
            "energy_per_sec": 4.5,
            "wave_count": 6,
            "rat_hp": 0.7,
            "rat_speed": 0.8,
            "rat_count": 0.75,
            "chew": 0.65,
            "color": "neon_lime",
        },
        "hard": {
            "label": "HARD",
            "blurb": "standard pressure",
            "base_hp": 20,
            "start_energy": 45,
            "energy_per_sec": 3.5,
            "wave_count": 8,
            "rat_hp": 1.0,
            "rat_speed": 1.0,
            "rat_count": 1.0,
            "chew": 1.0,
            "color": "neon_orange",
        },
        "doom": {
            "label": "DOOM",
            "blurb": "rats own the night",
            "base_hp": 12,
            "start_energy": 32,
            "energy_per_sec": 2.6,
            "wave_count": 10,
            "rat_hp": 1.55,
            "rat_speed": 1.3,
            "rat_count": 1.4,
            "chew": 1.5,
            "color": "neon_magenta",
        },
    },
    "diff_order": ["low", "hard", "doom"],
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
        "wall": (90, 200, 140),
    },
}


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def weapon_def(kind: str) -> dict:
    return CONFIG["weapons"][kind]


def weapon_color(kind: str) -> tuple[int, int, int]:
    return CONFIG["colors"][weapon_def(kind)["color"]]


def diff_def(key: str) -> dict:
    return CONFIG["difficulties"][key]


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
    hp: float
    max_hp: float
    cooldown: float = 0.0
    flash: float = 0.0
    spawn_pop: float = 0.35
    hit_flash: float = 0.0


@dataclass
class Wall:
    lane: int
    x: float
    y: float
    hp: float
    max_hp: float
    spawn_pop: float = 0.3
    hit_flash: float = 0.0


@dataclass
class Bomb:
    lane: int
    x: float
    y: float
    fuse: float
    max_fuse: float
    damage: float
    radius: float
    pulse: float = 0.0


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
    chew_cd: float = 0.0


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
class LaserBeam:
    x0: float
    y0: float
    x1: float
    y1: float
    life: float = 0.12
    max_life: float = 0.12


@dataclass
class Shell:
    """Mortar bomb — arcs then explodes."""
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    blast: float
    life: float = 2.2
    trail: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class GameState:
    phase: str = "menu"  # menu | idle | spawn | clear | upgrade | win | lose
    difficulty: str = "hard"
    base_hp: float = 20
    energy: float = 45
    energy_per_sec: float = 3.5
    wave_count: int = 8
    rat_hp_m: float = 1.0
    rat_speed_m: float = 1.0
    rat_count_m: float = 1.0
    chew_m: float = 1.0
    wave: int = 0
    spawn_left: int = 0
    spawn_timer: float = 0.0
    turrets: list[Turret] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    bombs: list[Bomb] = field(default_factory=list)
    rats: list[Rat] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)
    lasers: list[LaserBeam] = field(default_factory=list)
    shells: list[Shell] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    floaters: list[Floater] = field(default_factory=list)
    selected_lane: int = 1
    selected_build: str = "pulse"  # pulse|beam|mortar|wall|bomb
    message: str = "Pick difficulty: 1 LOW · 2 HARD · 3 DOOM"
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
    menu_cursor: int = 1  # hard


UPGRADE_LABELS = {
    "damage": "Overclock +25% damage",
    "range": "Long lens +15% range",
    "firerate": "Coolant −15% cooldown",
    "energy": "Solar drip +20% energy/s",
    "cheap": "Discount −2 all costs",
}


def lane_y(i: int, h: int) -> float:
    top = 100
    bottom = h - 70
    band = (bottom - top) / CONFIG["lanes"]
    return top + band * i + band * 0.5


def lane_occupancy(gs: GameState, lane: int) -> int:
    return sum(1 for t in gs.turrets if t.lane == lane) + sum(1 for w in gs.walls if w.lane == lane)


def next_slot_x(gs: GameState, lane: int) -> float:
    return 110 + lane_occupancy(gs, lane) * 68


def build_cost(gs: GameState, kind: str | None = None) -> int:
    kind = kind or gs.selected_build
    if kind == "wall":
        return max(4, CONFIG["wall"]["cost"] - gs.cost_off)
    if kind == "bomb":
        return max(5, CONFIG["bomb"]["cost"] - gs.cost_off)
    return max(4, weapon_def(kind)["cost"] - gs.cost_off)


def apply_difficulty(gs: GameState, key: str) -> None:
    d = diff_def(key)
    gs.difficulty = key
    gs.base_hp = float(d["base_hp"])
    gs.energy = float(d["start_energy"])
    gs.energy_per_sec = float(d["energy_per_sec"])
    gs.wave_count = int(d["wave_count"])
    gs.rat_hp_m = float(d["rat_hp"])
    gs.rat_speed_m = float(d["rat_speed"])
    gs.rat_count_m = float(d["rat_count"])
    gs.chew_m = float(d["chew"])
    gs.phase = "idle"
    gs.message = f"{d['label']}: Q bolts · W laser · E mortar · A wall · B bomb · ENTER wave"
    gs.banner_text = ""
    gs.banner_t = 0.0


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
    raw = wcfg["base_rats"] + (gs.wave - 1) * wcfg["rats_per_wave"]
    gs.spawn_left = max(3, int(round(raw * gs.rat_count_m)))
    gs.spawn_timer = 0.2
    gs.phase = "spawn"
    gs.message = f"WAVE {gs.wave}/{gs.wave_count} — neon rats"
    gs.banner_text = f"W{gs.wave}"
    gs.banner_t = 0.7
    gs.spawn_fx = 0.0


def rat_stats(gs: GameState) -> tuple[float, float]:
    r = CONFIG["rat"]
    w = CONFIG["waves"]
    hp = r["hp"] * (1 + (gs.wave - 1) * w["hp_scale"]) * gs.rat_hp_m
    speed = r["speed"] * (1 + (gs.wave - 1) * w["speed_scale"]) * gs.rat_speed_m
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
    gs.banner_text = ""
    gs.banner_t = 0.0


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
    if gs.wave >= gs.wave_count:
        gs.phase = "win"
        label = diff_def(gs.difficulty)["label"]
        gs.message = f"{label} CLEARED. Neon rats retreated."
        gs.banner_text = "VICTORY"
        gs.banner_t = 2.0
    else:
        start_wave(gs)


def place_build(gs: GameState, lane: int, h: int) -> None:
    if gs.phase in ("menu", "upgrade", "win", "lose"):
        return
    if gs.phase not in ("idle", "spawn", "clear"):
        return
    kind = gs.selected_build
    cost = build_cost(gs, kind)
    if gs.energy < cost:
        gs.message = "Not enough energy"
        return

    y = lane_y(lane, h)
    C = CONFIG["colors"]

    if kind == "bomb":
        # bombs drop mid-lane ahead of base, don't take build slots
        x = 200 + random.uniform(40, 280)
        bcfg = CONFIG["bomb"]
        gs.bombs.append(
            Bomb(
                lane=lane,
                x=x,
                y=y,
                fuse=float(bcfg["fuse"]),
                max_fuse=float(bcfg["fuse"]),
                damage=float(bcfg["damage"]) * gs.damage_mult,
                radius=float(bcfg["radius"]),
            )
        )
        gs.energy -= cost
        gs.message = f"BOMB armed · lane {lane + 1}"
        burst(gs, x, y, C["neon_orange"], n=10, speed=100, life=0.25)
        return

    if lane_occupancy(gs, lane) >= CONFIG["turret_max_per_lane"]:
        gs.message = "Lane full"
        return

    x = next_slot_x(gs, lane)

    if kind == "wall":
        whp = float(CONFIG["wall"]["hp"])
        gs.walls.append(Wall(lane=lane, x=x, y=y, hp=whp, max_hp=whp))
        gs.energy -= cost
        gs.message = f"WALL up · lane {lane + 1} · HP {int(whp)}"
        burst(gs, x, y, C["wall"], n=14, speed=140, life=0.3)
        return

    thp = float(weapon_def(kind)["hp"])
    gs.turrets.append(Turret(lane=lane, x=x, y=y, kind=kind, hp=thp, max_hp=thp))
    gs.energy -= cost
    label = weapon_def(kind)["label"]
    gs.message = f"{label} online · lane {lane + 1} · HP {int(thp)}"
    burst(gs, x, y, weapon_color(kind), n=16, speed=160, life=0.35)


def structures_on_lane(gs: GameState, lane: int) -> list[tuple[str, object, float]]:
    """Return (type, obj, x) for chew targets on a lane."""
    out: list[tuple[str, object, float]] = []
    for t in gs.turrets:
        if t.lane == lane:
            out.append(("turret", t, t.x))
    for w in gs.walls:
        if w.lane == lane:
            out.append(("wall", w, w.x))
    return out


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


def draw_wall(surf: pygame.Surface, wall: Wall, C: dict) -> None:
    x, y = int(wall.x), int(wall.y)
    pop = 1.0 + wall.spawn_pop * 0.6
    col = C["wall"]
    if wall.hit_flash > 0:
        col = (255, 255, 255)
    hw, hh = int(14 * pop), int(28 * pop)
    pygame.draw.rect(surf, tuple(int(c * 0.2) for c in col), (x - hw, y - hh, hw * 2, hh * 2), border_radius=3)
    pygame.draw.rect(surf, col, (x - hw, y - hh, hw * 2, hh * 2), 2, border_radius=3)
    # brick lines
    pygame.draw.line(surf, col, (x - hw, y), (x + hw, y), 1)
    pygame.draw.line(surf, col, (x, y - hh), (x, y + hh), 1)
    for i in range(3):
        pygame.draw.circle(surf, C["neon_lime"], (x - 6 + i * 6, y - hh + 4), 2)
    ratio = clamp(wall.hp / wall.max_hp, 0, 1)
    bar_c = C["neon_lime"] if ratio > 0.45 else C["neon_orange"] if ratio > 0.2 else C["base"]
    pygame.draw.rect(surf, (40, 40, 55), (x - 16, y + hh + 4, 32, 4))
    pygame.draw.rect(surf, bar_c, (x - 16, y + hh + 4, int(32 * ratio), 4))


def draw_bomb(surf: pygame.Surface, bomb: Bomb, C: dict, t: float) -> None:
    x, y = int(bomb.x), int(bomb.y)
    danger = 1.0 - bomb.fuse / bomb.max_fuse
    pulse = 0.6 + 0.4 * math.sin(t * (8 + danger * 20))
    col = C["neon_orange"]
    r = int(10 + danger * 6 + pulse * 2)
    glow_circle(surf, (x, y), r, col, layers=3)
    # fuse spark
    pygame.draw.line(surf, C["neon_lime"], (x, y - r), (x + 4, y - r - 10), 2)
    pygame.draw.circle(surf, (255, 255, 180), (x + 4, y - r - 10), 3)
    # radius preview when about to blow
    if danger > 0.55:
        a = int(40 + 80 * danger)
        ring = pygame.Surface((int(bomb.radius * 2), int(bomb.radius * 2)), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*col, a), (int(bomb.radius), int(bomb.radius)), int(bomb.radius), 2)
        surf.blit(ring, (x - int(bomb.radius), y - int(bomb.radius)))


def draw_turret(surf: pygame.Surface, t: Turret, pulse: float, C: dict) -> None:
    wd = weapon_def(t.kind)
    color = weapon_color(t.kind)
    lime = C["neon_lime"]
    pop = 1.0 + t.spawn_pop * 0.9
    x, y = int(t.x), int(t.y)
    hum = 0.65 + 0.35 * math.sin(pulse * 5 + t.x * 0.05)
    mode = wd["mode"]

    pad_w, pad_h = int(36 * pop), int(12 * pop)
    pygame.draw.ellipse(surf, (20, 24, 40), (x - pad_w // 2, y + 7, pad_w, pad_h))

    if mode == "laser":
        # dish + emitter lens
        pygame.draw.circle(surf, tuple(int(c * 0.22) for c in color), (x, y), int(14 * pop))
        pygame.draw.circle(surf, color, (x, y), int(14 * pop), 2)
        pygame.draw.circle(surf, (200, 255, 255), (x + 4, y), int(5 + t.flash * 4))
        pygame.draw.line(surf, color, (x + 8, y - 2), (x + 26, y - 2), 2)
        pygame.draw.line(surf, color, (x + 8, y + 2), (x + 26, y + 2), 2)
        if t.flash > 0:
            pygame.draw.circle(surf, (255, 255, 255), (x + 28, y), int(3 + t.flash * 8))
    elif mode == "mortar":
        # stubby tube angled up
        pygame.draw.rect(surf, tuple(int(c * 0.22) for c in color), (x - 12, y - 6, 22, 18), border_radius=3)
        pygame.draw.rect(surf, color, (x - 12, y - 6, 22, 18), 2, border_radius=3)
        tube = [
            (x + 2, y + 4),
            (x + 10, y - 18 - int(t.flash * 6)),
            (x + 18, y - 14 - int(t.flash * 6)),
            (x + 10, y + 6),
        ]
        pygame.draw.polygon(surf, tuple(int(c * 0.35) for c in color), tube)
        pygame.draw.polygon(surf, color, tube, 2)
        pygame.draw.circle(surf, color, (x + 14, y - 16), 4, 2)
    else:
        # pulse hex coil
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
        barrel = int(22 * pop + t.flash * 6)
        pygame.draw.rect(surf, tuple(int(c * 0.35) for c in color), (x + 6, y - 4, barrel, 8), border_radius=3)
        pygame.draw.rect(surf, color, (x + 6, y - 4, barrel, 8), 2, border_radius=3)
        pygame.draw.circle(surf, color, (x + 8 + barrel, y), 4, 2)

    if t.hit_flash > 0:
        pygame.draw.circle(surf, (255, 255, 255), (x, y), int(16 + t.hit_flash * 10), 2)

    glow_circle(surf, (x, y), int(4 + 2 * hum + t.flash * 3), color, layers=3)
    led = lime if t.cooldown < 0.08 else ((255, 80, 80) if t.cooldown > wd["cooldown"] * 0.6 else C["neon_cyan"])
    pygame.draw.circle(surf, led, (x - 10, y - 12), 3)

    if t.flash > 0 and mode == "bolt":
        fl = t.flash
        pygame.draw.circle(surf, lime, (x + 30, y), int(5 + fl * 12))
        pygame.draw.circle(surf, (255, 255, 220), (x + 32, y), int(2 + fl * 5))

    ratio = clamp(t.hp / t.max_hp, 0, 1)
    bar_c = lime if ratio > 0.45 else C["neon_orange"] if ratio > 0.2 else C["base"]
    pygame.draw.rect(surf, (40, 40, 55), (x - 16, y + 18, 32, 4))
    pygame.draw.rect(surf, bar_c, (x - 16, y + 18, int(32 * ratio), 4))


def kill_rat(gs: GameState, rat: Rat, C: dict) -> None:
    if rat in gs.rats:
        gs.rats.remove(rat)
    gs.energy = min(99, gs.energy + CONFIG["rat"]["reward"])
    gs.kills += 1
    gs.shake = max(gs.shake, 0.18)
    burst(gs, rat.x, rat.y, C["neon_magenta"], n=18, speed=200, life=0.45, size=3.2)
    gs.floaters.append(Floater(rat.x, rat.y - 28, "+ENERGY", C["neon_cyan"]))


def aoe_damage(gs: GameState, x: float, y: float, radius: float, damage: float, C: dict, label: str = "BOOM") -> None:
    burst(gs, x, y, C["neon_orange"], n=28, speed=240, life=0.5, size=3.5)
    burst(gs, x, y, C["neon_magenta"], n=14, speed=160, life=0.35, size=2.5)
    gs.shake = max(gs.shake, 0.45)
    gs.floaters.append(Floater(x, y - 20, label, C["neon_orange"], life=0.85))
    dead: list[Rat] = []
    for rat in gs.rats:
        if math.hypot(rat.x - x, rat.y - y) <= radius:
            rat.hp -= damage
            rat.hit_flash = 0.2
            gs.floaters.append(Floater(rat.x, rat.y - 18, f"-{int(damage)}", C["neon_orange"]))
            if rat.hp <= 0:
                dead.append(rat)
    for rat in dead:
        kill_rat(gs, rat, C)


def detonate_bomb(gs: GameState, bomb: Bomb, C: dict) -> None:
    aoe_damage(gs, bomb.x, bomb.y, bomb.radius, bomb.damage, C, "BOOM")


def point_near_segment(px: float, py: float, x0: float, y0: float, x1: float, y1: float, thick: float) -> bool:
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    t = clamp(((px - x0) * dx + (py - y0) * dy) / (length * length), 0.0, 1.0)
    cx, cy = x0 + t * dx, y0 + t * dy
    return math.hypot(px - cx, py - cy) <= thick


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
    build_keys = {
        "q": "pulse",
        "w": "beam",
        "e": "mortar",
        "a": "wall",
        "b": "bomb",
    }

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
                elif gs.phase == "menu":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        apply_difficulty(gs, "low")
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        apply_difficulty(gs, "hard")
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        apply_difficulty(gs, "doom")
                    elif event.key == pygame.K_UP:
                        gs.menu_cursor = (gs.menu_cursor - 1) % 3
                    elif event.key == pygame.K_DOWN:
                        gs.menu_cursor = (gs.menu_cursor + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        apply_difficulty(gs, CONFIG["diff_order"][gs.menu_cursor])
                elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_a, pygame.K_b):
                    name = build_keys[pygame.key.name(event.key)]
                    gs.selected_build = name
                    if name == "wall":
                        gs.message = f"WALL ready (${build_cost(gs)}) — click a lane or SPACE to place"
                    elif name == "bomb":
                        gs.message = f"BOMB ready (${build_cost(gs)}) — click a lane or SPACE to drop"
                    else:
                        wd = weapon_def(name)
                        gs.message = f"{wd['label']} ready (${build_cost(gs)}) — click lane / SPACE · ENTER = wave"
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
                        place_build(gs, gs.selected_lane, h)
                elif event.key == pygame.K_RETURN and gs.phase == "idle":
                    start_wave(gs)
                elif event.key == pygame.K_r and gs.phase in ("win", "lose"):
                    gs = GameState()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if gs.phase == "menu":
                    _, my = event.pos
                    for i, key in enumerate(CONFIG["diff_order"]):
                        cy = 200 + i * 70
                        if abs(my - cy) < 28:
                            apply_difficulty(gs, key)
                            break
                    continue
                if gs.phase == "upgrade":
                    continue
                if gs.phase in ("win", "lose"):
                    continue
                _, my = event.pos
                best = min(range(CONFIG["lanes"]), key=lambda i: abs(lane_y(i, h) - my))
                gs.selected_lane = best
                place_build(gs, best, h)

        if gs.phase not in ("menu", "upgrade", "win", "lose", "idle"):
            gs.energy = min(99, gs.energy + gs.energy_per_sec * gs.energy_mult * dt)

        if gs.phase == "spawn":
            gs.spawn_timer -= dt
            if gs.spawn_left > 0 and gs.spawn_timer <= 0:
                lane = random.randrange(CONFIG["lanes"])
                hp, speed = rat_stats(gs)
                rx, ry = w - 40, lane_y(lane, h)
                gs.rats.append(Rat(lane=lane, x=rx, y=ry, hp=hp, max_hp=hp, speed=speed))
                burst(gs, rx, ry, C["neon_magenta"], n=8, speed=90, life=0.25, size=2)
                gs.spawn_left -= 1
                gs.spawn_timer = spawn_gap(gs.wave)
                gs.spawn_fx = 0.25
            if gs.spawn_left <= 0 and not gs.rats:
                gs.phase = "clear"

        if gs.phase in ("spawn", "clear"):
            chew_dmg = CONFIG["rat"]["damage_to_structure"] * gs.chew_m
            chew_cd = CONFIG["rat"]["chew_cooldown"]

            for rat in gs.rats:
                rat.phase += dt * 12
                rat.hit_flash = max(0.0, rat.hit_flash - dt * 4)
                rat.spawn_t = max(0.0, rat.spawn_t - dt)
                rat.chew_cd = max(0.0, rat.chew_cd - dt)
                if random.random() < dt * 8:
                    gs.particles.append(
                        Particle(rat.x + 8, rat.y, 30, random.uniform(-20, 20), 0.25, 0.25, C["neon_magenta"], 2)
                    )

                # block on nearest wall/turret ahead on same lane
                blockers = [
                    (typ, obj, sx)
                    for typ, obj, sx in structures_on_lane(gs, rat.lane)
                    if sx - 18 <= rat.x <= sx + 28
                ]
                if blockers:
                    blockers.sort(key=lambda b: b[2], reverse=True)
                    typ, obj, _ = blockers[0]
                    if rat.chew_cd <= 0:
                        if typ == "turret":
                            tur: Turret = obj  # type: ignore
                            tur.hp -= chew_dmg
                            tur.hit_flash = 0.2
                            rat.chew_cd = chew_cd
                            burst(gs, tur.x, tur.y, C["base"], n=6, speed=80, life=0.2, size=2)
                            if tur.hp <= 0:
                                burst(gs, tur.x, tur.y, weapon_color(tur.kind), n=20, speed=180)
                                gs.floaters.append(Floater(tur.x, tur.y - 20, "TURRET DOWN", C["base"]))
                                gs.turrets.remove(tur)
                                gs.shake = max(gs.shake, 0.35)
                        else:
                            wall: Wall = obj  # type: ignore
                            wall.hp -= chew_dmg
                            wall.hit_flash = 0.2
                            rat.chew_cd = chew_cd
                            burst(gs, wall.x, wall.y, C["wall"], n=6, speed=80, life=0.2, size=2)
                            if wall.hp <= 0:
                                burst(gs, wall.x, wall.y, C["wall"], n=18, speed=160)
                                gs.floaters.append(Floater(wall.x, wall.y - 20, "WALL DOWN", C["base"]))
                                gs.walls.remove(wall)
                                gs.shake = max(gs.shake, 0.3)
                    # stay put while chewing
                else:
                    rat.x -= rat.speed * dt

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
                        gs.message = f"{diff_def(gs.difficulty)['label']} FAIL. Press R."
                        gs.banner_text = "DEFEAT"
                        gs.banner_t = 2.0
                        gs.shake = 0.8
                else:
                    survivors.append(rat)
            gs.rats = survivors

            for tur in gs.turrets:
                wd = weapon_def(tur.kind)
                mode = wd["mode"]
                dmg = wd["damage"] * gs.damage_mult
                rng = wd["range"] * gs.range_mult
                cd = wd["cooldown"] * gs.cooldown_mult
                tur.cooldown = max(0.0, tur.cooldown - dt)
                tur.flash = max(0.0, tur.flash - dt * 5)
                tur.spawn_pop = max(0.0, tur.spawn_pop - dt)
                tur.hit_flash = max(0.0, tur.hit_flash - dt * 4)
                if tur.cooldown > 0:
                    continue
                candidates = [
                    r
                    for r in gs.rats
                    if math.hypot(r.x - tur.x, r.y - tur.y) <= rng and r.x > tur.x - 40
                ]
                if not candidates:
                    continue
                target = min(candidates, key=lambda r: math.hypot(r.x - tur.x, r.y - tur.y))
                ang = math.atan2(target.y - tur.y, target.x - tur.x)
                col = weapon_color(tur.kind)

                if mode == "laser":
                    # hitscan beam — burns every rat on the line
                    tip = 28
                    x0 = tur.x + math.cos(ang) * tip
                    y0 = tur.y + math.sin(ang) * tip
                    x1 = tur.x + math.cos(ang) * rng
                    y1 = tur.y + math.sin(ang) * rng
                    gs.lasers.append(LaserBeam(x0, y0, x1, y1, life=0.11, max_life=0.11))
                    tur.flash = 0.25
                    tur.cooldown = cd
                    dead: list[Rat] = []
                    for r in gs.rats:
                        if point_near_segment(r.x, r.y, x0, y0, x1, y1, CONFIG["rat"]["radius"] + 6):
                            r.hp -= dmg
                            r.hit_flash = 0.12
                            if r.hp <= 0:
                                dead.append(r)
                    for r in dead:
                        kill_rat(gs, r, C)
                    continue

                if mode == "mortar":
                    # lob arcing shell toward target
                    dx = target.x - tur.x
                    flight = clamp(abs(dx) / 220.0, 0.55, 1.35)
                    vx = dx / flight
                    vy = (target.y - tur.y) / flight - 0.5 * 420 * flight
                    gs.shells.append(
                        Shell(
                            x=tur.x + 10,
                            y=tur.y - 16,
                            vx=vx,
                            vy=vy,
                            damage=dmg,
                            blast=float(wd["blast"]),
                        )
                    )
                    tur.flash = 0.35
                    tur.cooldown = cd
                    burst(gs, tur.x + 12, tur.y - 16, col, n=6, speed=80, life=0.2, size=2)
                    continue

                # pulse bolts
                tip = 30
                bx = tur.x + math.cos(ang) * tip
                by = tur.y + math.sin(ang) * tip
                gs.bullets.append(
                    Bullet(bx, by, target.x, target.y, dmg, kind=tur.kind, pierce_left=0, life=0.4)
                )
                tur.cooldown = cd
                tur.flash = 0.3
                burst(gs, bx, by, col, n=8, speed=110, life=0.2, size=2.5)

            for wall in gs.walls:
                wall.spawn_pop = max(0.0, wall.spawn_pop - dt)
                wall.hit_flash = max(0.0, wall.hit_flash - dt * 4)

            # panic bombs fuse
            alive_bombs: list[Bomb] = []
            for bomb in gs.bombs:
                bomb.fuse -= dt
                bomb.pulse += dt
                if bomb.fuse <= 0:
                    detonate_bomb(gs, bomb, C)
                else:
                    alive_bombs.append(bomb)
            gs.bombs = alive_bombs

            # mortar shells
            alive_shells: list[Shell] = []
            for s in gs.shells:
                s.life -= dt
                s.trail.append((s.x, s.y))
                if len(s.trail) > 12:
                    s.trail.pop(0)
                s.x += s.vx * dt
                s.y += s.vy * dt
                s.vy += 420 * dt
                # explode near any rat or when falling past lane band
                hit_rat = next(
                    (r for r in gs.rats if math.hypot(r.x - s.x, r.y - s.y) < CONFIG["rat"]["radius"] + 10),
                    None,
                )
                landed = s.vy > 0 and hit_rat is not None
                grounded = s.vy > 80 and any(abs(s.y - lane_y(i, h)) < 18 for i in range(CONFIG["lanes"]))
                if landed or grounded or s.life <= 0 or s.y > h:
                    aoe_damage(gs, s.x, s.y, s.blast, s.damage, C, "THUMP")
                else:
                    alive_shells.append(s)
            gs.shells = alive_shells

            # laser visuals fade
            alive_l: list[LaserBeam] = []
            for beam in gs.lasers:
                beam.life -= dt
                if beam.life > 0:
                    alive_l.append(beam)
            gs.lasers = alive_l

            # pulse bolts
            alive_b: list[Bullet] = []
            for b in gs.bullets:
                b.life -= dt
                b.trail.append((b.x, b.y))
                if len(b.trail) > 8:
                    b.trail.pop(0)
                dx = b.tx - b.x
                dy = b.ty - b.y
                step = min(1.0, dt * 18)
                b.x += dx * step
                b.y += dy * step

                col = weapon_color(b.kind)
                hits_this_frame = [
                    r
                    for r in gs.rats
                    if id(r) not in b.hit_ids
                    and math.hypot(r.x - b.x, r.y - b.y) < CONFIG["rat"]["radius"] + 8
                ]
                if hits_this_frame:
                    hit = min(hits_this_frame, key=lambda r: math.hypot(r.x - b.x, r.y - b.y))
                    b.hit_ids.add(id(hit))
                    hit.hp -= b.damage
                    hit.hit_flash = 0.15
                    burst(gs, b.x, b.y, col, n=10, speed=140, life=0.3)
                    gs.floaters.append(Floater(hit.x, hit.y - 18, f"-{int(b.damage)}", col))
                    if hit.hp <= 0:
                        kill_rat(gs, hit, C)
                elif b.life > 0 and 0 < b.x < w + 40 and -20 < b.y < h + 20:
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

        if gs.phase == "menu":
            title_glow = 0.75 + 0.25 * math.sin(gs.time * 3)
            canvas.blit(
                font_big.render("LANE GUARD", True, tuple(int(c * title_glow) for c in C["neon_cyan"])),
                (w // 2 - 120, 80),
            )
            canvas.blit(font.render("NEON RATS — pick your pain", True, C["neon_magenta"]), (w // 2 - 150, 130))
            for i, key in enumerate(CONFIG["diff_order"]):
                d = diff_def(key)
                selected = i == gs.menu_cursor
                col = C[d["color"]]
                pulse = 0.75 + 0.25 * math.sin(gs.time * 5 + i) if selected else 0.55
                col = tuple(int(c * pulse) for c in col)
                cy = 200 + i * 70
                label = f"[{i + 1}]  {d['label']}"
                canvas.blit(font_big.render(label, True, col), (w // 2 - 140, cy - 16))
                canvas.blit(
                    font_small.render(
                        f"{d['blurb']}  ·  {d['wave_count']} waves  ·  base {d['base_hp']} HP",
                        True,
                        C["muted"] if not selected else C["text"],
                    ),
                    (w // 2 - 140, cy + 22),
                )
                if selected:
                    pygame.draw.rect(canvas, col, (w // 2 - 160, cy - 22, 420, 58), 2, border_radius=6)
            canvas.blit(font_small.render("↑↓ + ENTER  or  click  ·  Esc quit", True, C["muted"]), (w // 2 - 120, h - 50))
            screen.blit(canvas, (0, 0))
            pygame.display.flip()
            continue

        title_glow = 0.75 + 0.25 * math.sin(gs.time * 3)
        canvas.blit(font_big.render("LANE GUARD", True, tuple(int(c * title_glow) for c in C["neon_cyan"])), (18, 10))
        dcol = C[diff_def(gs.difficulty)["color"]]
        canvas.blit(font_small.render(diff_def(gs.difficulty)["label"], True, dcol), (230, 18))

        hud = (
            f"BASE {max(0, int(gs.base_hp))}  ENERGY {int(gs.energy)}  "
            f"WAVE {gs.wave}/{gs.wave_count}  KILLS {gs.kills}"
        )
        canvas.blit(font.render(hud, True, C["text"]), (18, 48))

        # build bar
        bx = 18
        items = [
            ("pulse", f"[Q] PULSE ${build_cost(gs, 'pulse')}", weapon_color("pulse")),
            ("beam", f"[W] BEAM ${build_cost(gs, 'beam')}", weapon_color("beam")),
            ("mortar", f"[E] MORTAR ${build_cost(gs, 'mortar')}", weapon_color("mortar")),
            ("wall", f"[A] WALL ${build_cost(gs, 'wall')}", C["wall"]),
            ("bomb", f"[B] BOMB ${build_cost(gs, 'bomb')}", C["neon_orange"]),
        ]
        for kind, label, col in items:
            active = kind == gs.selected_build
            c = col if active else C["muted"]
            canvas.blit(font_small.render(label, True, c), (bx, 72))
            if active:
                pygame.draw.rect(canvas, col, (bx - 4, 70, font_small.size(label)[0] + 8, 18), 1)
            bx += font_small.size(label)[0] + 14

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
            col = (60, 90, 140) if selected else C["lane"]
            pygame.draw.line(canvas, col, (70, int(y)), (w - 30, int(y)), 2 if selected else 1)
            tag = C["neon_cyan"] if selected else C["muted"]
            canvas.blit(font_small.render(f"L{i + 1}", True, tag), (74, int(y) - 22))

        for wall in gs.walls:
            draw_wall(canvas, wall, C)
        for tur in gs.turrets:
            draw_turret(canvas, tur, gs.time, C)
        for bomb in gs.bombs:
            draw_bomb(canvas, bomb, C, gs.time)
        for rat in gs.rats:
            draw_rat(canvas, rat, C["neon_magenta"], gs.time)

        # laser beams
        for beam in gs.lasers:
            a = clamp(beam.life / beam.max_life, 0, 1)
            col = tuple(int(c * a) for c in C["neon_cyan"])
            p0 = (int(beam.x0), int(beam.y0))
            p1 = (int(beam.x1), int(beam.y1))
            pygame.draw.line(canvas, tuple(max(0, c // 3) for c in col), p0, p1, 5)
            pygame.draw.line(canvas, col, p0, p1, 2)
            pygame.draw.circle(canvas, (255, 255, 255), p0, 3)
            pygame.draw.circle(canvas, col, p1, 4)

        # mortar shells
        for s in gs.shells:
            col = C["neon_magenta"]
            if len(s.trail) >= 2:
                pygame.draw.lines(
                    canvas,
                    tuple(max(0, c // 3) for c in col),
                    False,
                    [(int(x), int(y)) for x, y in s.trail],
                    2,
                )
            glow_circle(canvas, (int(s.x), int(s.y)), 4, col, layers=2)

        for b in gs.bullets:
            col = weapon_color(b.kind)
            if len(b.trail) >= 2:
                pygame.draw.lines(
                    canvas,
                    tuple(max(0, c // 3) for c in col),
                    False,
                    [(int(x), int(y)) for x, y in b.trail],
                    2,
                )
            glow_circle(canvas, (int(b.x), int(b.y)), 3, col, layers=2)

        for p in gs.particles:
            a = clamp(p.life / p.max_life, 0, 1)
            pygame.draw.circle(canvas, tuple(int(c * a) for c in p.color), (int(p.x), int(p.y)), max(1, int(p.size * a)))
        for f in gs.floaters:
            a = clamp(f.life / 0.7, 0, 1)
            canvas.blit(font_small.render(f.text, True, tuple(int(c * a) for c in f.color)), (int(f.x) - 10, int(f.y)))

        if gs.phase == "idle":
            tip = font_small.render(
                "Q bolts · W laser · E mortar bombs · A wall · B panic bomb · ENTER start",
                True,
                C["muted"],
            )
            canvas.blit(tip, (18, h - 52))

        # tiny wave tag — no full-screen blackout
        if gs.banner_t > 0 and gs.banner_text and gs.phase not in ("win", "lose"):
            fade = clamp(gs.banner_t / 0.35, 0, 1)
            text = font.render(gs.banner_text, True, tuple(int(c * fade) for c in C["neon_cyan"]))
            canvas.blit(text, (w - 80, 18))

        if gs.phase == "upgrade":
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            canvas.blit(overlay, (0, 0))
            canvas.blit(font_big.render("UPGRADE CORE", True, C["neon_cyan"]), (w // 2 - 120, 130))
            for idx, key in enumerate(gs.upgrade_options):
                pulse_u = 0.7 + 0.3 * math.sin(gs.time * 5 + idx)
                col = tuple(int(c * pulse_u) for c in C["neon_orange"])
                canvas.blit(font.render(f"[{idx + 1}] {UPGRADE_LABELS[key]}", True, col), (w // 2 - 180, 200 + idx * 40))

        if gs.phase in ("win", "lose"):
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            canvas.blit(overlay, (0, 0))
            col = C["neon_lime"] if gs.phase == "win" else C["neon_magenta"]
            canvas.blit(font_big.render(gs.message, True, col), (60, h // 2 - 24))
            canvas.blit(font.render("Press R — back to difficulty select", True, C["text"]), (60, h // 2 + 24))

        ox = int(random.uniform(-1, 1) * gs.shake * 10) if gs.shake > 0 else 0
        oy = int(random.uniform(-1, 1) * gs.shake * 10) if gs.shake > 0 else 0
        screen.fill((0, 0, 0))
        screen.blit(canvas, (ox, oy))
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
