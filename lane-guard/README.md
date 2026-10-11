# Lane Guard — Neon Rats

Python / **pygame** prototype: defend three neon lanes from glowing **neon rats**.

## Run

```powershell
cd lane-guard
pip install -r requirements.txt
python main.py
```

## Difficulty

On boot pick **LOW / HARD / DOOM** (`1` `2` `3` or ↑↓ + Enter).

| Mode | Feel |
|------|------|
| LOW | More base HP, fewer weaker rats |
| HARD | Standard pressure |
| DOOM | Thin base, fat fast rats, more waves |

## Controls

| Input | Action |
|-------|--------|
| `Q` | **Pulse** turret |
| `W` | **Needle** turret |
| `E` | **Rail** turret |
| `A` | **Wall** — blocks / soaks chew damage |
| `B` | **Bomb** — timed blast across nearby lanes |
| `1` `2` `3` | Select lane (or upgrade after a wave) |
| `Space` / click | Place selected build |
| `Enter` | Start wave |
| `R` | Restart → difficulty select |
| `Esc` | Quit |

## Design notes

- Turrets have **HP**; rats chew walls and turrets before the base.
- Turrets shoot **cross-lane** inside range.
- Bombs are joke / panic buttons with a short fuse and AOE.

Balance lives in `CONFIG` at the top of `main.py`.
