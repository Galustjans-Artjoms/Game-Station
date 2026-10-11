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
| `1` `2` `3` | Select lane (or pick upgrade after a wave) |
| `Space` / click | Place turret on selected / clicked lane |
| `Enter` | Start first wave (from idle) |
| `R` | Restart after win/lose |
| `Esc` | Quit |

## Design notes

**Loop:** place turrets → clear wave of neon rats → pick 1 of 3 upgrades → harder wave → survive all waves.

**Why neon rats:** readable silhouettes on a dark HUD; “threat crawling down pipes” fantasy without needing spritesheets.

**Balance knobs:** all in `CONFIG` at the top of `main.py` (HP scale, spawn gap, turret cost, upgrade mults) — change numbers, replay, note what felt fair.

**Juice / animation:** run-cycle rats, trails, muzzle flash, hit flash, death bursts, floating damage, screen shake, wave banners, spawn-gate pulse, spinning turret rings.

**Next iterations:** rats that chew turrets, elite “king rat”, sell/move turrets, short tutorial overlay.
