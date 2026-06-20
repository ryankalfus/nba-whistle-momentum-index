# WMI Controlled Calculations

1. Raw: WMI_raw for OKC vs. MIL (February 12, 2026; output: `wmi_rawgame_breakdown_okc_mil.csv`) = `0.9523809523809524`
   Controlled: WMI_controlled for OKC vs. MIL (February 12, 2026; output: `wmi_controlledgame_breakdown_okc_mil.csv`) = `0.4577664628208559`
2. Raw: WMI_raw for 2025-26 season (as of March 1, 2026; output: `wmi_rawseason_2025_26_summary_asof_2026_03_01.csv`) = `0.9498474839224899`
   Controlled: WMI_controlled for 2025-26 season (mirrored March 1, 2026 scope; output: `wmi_controlledseason_2025_26_summary_asof_2026_03_01.csv`) = `0.9076415767800788` with `games_succeeded = 895` and `games_failed = 1` because `0022500652` returned a current NBA CDN `403` during the controlled rerun.
3. Raw: WMI_raw for 2024-25 season (output: `wmi_rawseason_2024_25_summary.csv`) = `0.9786445240516944`
   Controlled: WMI_controlled for 2024-25 season (output: `wmi_controlledseason_2024_25_summary.csv`) = `0.9184000344305718`
4. Raw: WMI_raw for 2023-24 season (output: `wmi_rawseason_2010_11_to_2023_24.csv`) = `0.9884629883031074`
   Controlled: WMI_controlled for 2023-24 season (output: `wmi_controlledseason_2010_11_to_2023_24.csv`) = `0.9254265988153246`
5. Raw: WMI_raw for 2022-23 season (output: `wmi_rawseason_2010_11_to_2023_24.csv`) = `0.9960930994135297`
   Controlled: WMI_controlled for 2022-23 season (output: `wmi_controlledseason_2010_11_to_2023_24.csv`) = `0.9465312412672284`
6. Raw: WMI_raw for 2021-22 season (output: `wmi_rawseason_2010_11_to_2023_24.csv`) = `0.942689878530503`
   Controlled: WMI_controlled for 2021-22 season (output: `wmi_controlledseason_2010_11_to_2023_24.csv`) = `0.8940441572083543`
7. Raw: WMI_raw for 2020-21 season (output: `wmi_rawseason_2010_11_to_2023_24.csv`) = `0.9874203265496059`
   Controlled: WMI_controlled for 2020-21 season (output: `wmi_controlledseason_2010_11_to_2023_24.csv`) = `0.9241352358771234`
8. Raw: WMI_raw for CLE vs. CHA (February 20, 2026; random 2025-26 game; game_id: `0022500802`) = `0.7185909980430528`
   Controlled: WMI_controlled for CLE vs. CHA (February 20, 2026; output: `wmi_controlledgame_breakdown_0022500802.csv`) = `0.7286340884318196`
9. Raw: WMI_rawgame list for completed 2025-26 regular-season games (as of March 23, 2026; output: `wmi_rawgames_2025_26_asof_2026_03_23.csv`) has `games_succeeded = 1034`, `games_failed = 2`, `mean_game_wmi_raw = 0.9344508632517702`, and `std_game_wmi_raw = 0.35882259210043344`
   Controlled: WMI_controlledgame list for completed 2025-26 regular-season games (mirrored March 23, 2026 scope; output: `wmi_controlledgames_2025_26_asof_2026_03_23.csv`) has `games_succeeded = 1033`, `games_failed = 3` (`0022500405`, `0022500652`, `0022501003`), `mean_game_wmi_controlled = 0.7661223911051365`, and `std_game_wmi_controlled = 0.4630505447819352`
