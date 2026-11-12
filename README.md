# sky-ocean

[![make.fun · coolest-art-01](https://make.fun/badge/coolest-art-01.svg)](https://make.fun/bounty/coolest-art-01?utm_source=github&utm_medium=readme&utm_campaign=coolest-art-01)
[![rank](https://make.fun/badge/coolest-art-01/cibzzz/sky-ocean/rank.svg)](https://make.fun/bounty/coolest-art-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=coolest-art-01)
[![reward](https://make.fun/badge/coolest-art-01/cibzzz/sky-ocean/reward.svg)](https://make.fun/bounty/coolest-art-01?utm_source=github&utm_medium=readme&utm_campaign=coolest-art-01)

**The Sky Ocean.** A humpback whale swims across the face of the moon above a
quiet night sea, trailing a stream of glowing plankton, while far below a lone
boat's lantern answers with the only other warm light in the world.

The picture is drawn entirely in code: `main.py` (Python 3, standard library
only) renders the scene pixel by pixel — gradient sky, star field, a shaded
moon, the whale as a hand-authored smoothed silhouette, light trails, sea
shimmer and vignette — encodes it as a PNG, and writes it to `entry.png` in
the output directory. It is fully deterministic: the same bytes on every run.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Without `MAKEFUN_OUTPUT_DIR` it writes to `/output/entry.png`, as in the
competition sandbox.
