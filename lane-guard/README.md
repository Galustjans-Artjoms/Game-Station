# Lane Guard — Neon Rats

Python / **pygame** prototype: defend three neon lanes from glowing **neon rats**.

## Run

```powershell
cd lane-guard
pip install -r requirements.txt
python main.py
```

## Controls

| Key / input | Action |
|-------------|--------|
| `Q` | **Pulse** turret — balanced |
| `W` | **Needle** turret — cheap, rapid fire |
| `E` | **Rail** turret — expensive, heavy, pierces |
| `1` `2` `3` | Select lane (or pick upgrade after a wave) |
| `Space` / click | Place selected weapon on lane |
| `Enter` | Start first wave |
| `R` | Restart after win/lose |
| `Esc` | Quit |

## Weapons (design roles)

| Weapon | Cost | Role |
|--------|------|------|
| Pulse | 12 | Default all-rounder |
| Needle | 8 | Spam / early economy |
| Rail | 18 | Slow nuke, pierces 2 rats |

Balance numbers live in `CONFIG["weapons"]` at the top of `main.py`.

## Design notes

**Loop:** pick weapon → place on lanes → clear wave → upgrade → harder rats.

**Juice:** run-cycle rats, trails, muzzle flash, hit flash, death bursts, floating damage, screen shake, wave banners, distinct turret silhouettes per weapon.

**Next:** rats chew turrets, king rat, sell/move, short tutorial.
