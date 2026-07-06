# WMI Controlled Game Calculations

1. WMI: WMI for OKC vs. MIL (February 12, 2026; output: `wmi_breakdown_okc_mil.csv`) = `0.9523809523809524`
   Controlled: WMI_controlledgame for OKC vs. MIL (February 12, 2026; output: `wmi_controlledgame_breakdown_okc_mil.csv`) = `0.6482661547572947`
2. WMI: WMI for CLE vs. CHA (February 20, 2026; random 2025-26 game; game_id: `0022500802`) = `0.7185909980430528`
   Controlled: WMI_controlledgame for CLE vs. CHA (February 20, 2026; output: `wmi_controlledgame_breakdown_0022500802.csv`) = `0.7044370826279954`
3. WMI: WMI comparison list for completed 2025-26 regular-season games (as of March 23, 2026; output: `wmi_games_2025_26_asof_2026_03_23.csv`) has `games_succeeded = 1034`, `games_failed = 2`, `mean_wmi = 0.9344508632517702`, and `std_wmi = 0.35882259210043344`
   Controlled: WMI_controlledgame comparison list currently uses the active regression-controlled `M_t` model for 2020-21 through 2024-25 in `wmi_controlledgames_2020_21_to_2025_26.csv`; it has `controlled_games = 5693`, `controlled_games_with_wmi = 5693`, `mean_wmi_controlled = 0.806753`, and `median_game_wmi_controlled = 0.763403`. The old 2025-26 controlled snapshot is not mixed into this distribution because it used a different method.
