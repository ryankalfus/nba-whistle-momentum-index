# WMI v1 Release Notes

Release date: July 2, 2026

## What This Release Is

This release publishes the first clean version of NBA Whistle Momentum Index.

The active metric is:

- `WMI`
- `WMI_game`
- `wmi_game_percentile`

The product is game-by-game. Multi-game outputs are used for percentile and distribution context only.

## Included Artifacts

- Full active WMI definitions in `PROJECT/Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`
- Public project guide in `README.md`
- One-game WMI scripts
- 2025-26 completed-game snapshot
- 2020-21 through 2025-26 comparison distribution
- Distribution visual
- Tests and lint configuration through `requirements.txt`

## Current Distribution

- Games with WMI: `6,727`
- Mean `WMI_game`: `0.960619`
- Median `WMI_game`: `0.909180`
- Logged data failures: `503`

## Scope Decisions

- Controlled WMI is paused and archived.
- Season-level pooled WMI is not part of the active release.
- Z-scores were replaced with percentiles for simpler interpretation.
- WMI should be presented as whistle-pattern behavior, not proof of referee intent.

## Verification

Release checks:

```bash
ruff check .
pytest -q
```
