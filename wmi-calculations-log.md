# **WMI Calculations Log**

## *All WMI (WMI, WMI_raw, any WMI calclation) calculations are logged here. Start with WMI calculation type (e.g. WMI_raw, WMI_controlled), by going off the Definitions markdown. If the calculation doesn't match a definition, make a new definition and log it in the definitions markdown and then log the calculation in here using the term. Make sure game dates / any important info is specified.*

1/ WMI_raw for OKC vs. MIL (February 12, 2026; output: wmi_rawgame_breakdown_okc_mil.csv) = 0.9523809523809524
2/ WMI_raw for 2025-26 season (as of March 1, 2026; output: wmi_rawseason_2025_26_summary_asof_2026_03_01.csv) = 0.9498474839224899
3/ WMI_raw for 2024-25 season (output: wmi_rawseason_2024_25_summary.csv) = 0.9786445240516944
4/ WMI_raw for 2023-24 season (output: wmi_rawseason_2010_11_to_2023_24.csv) = 0.9884629883031074
5/ WMI_raw for 2022-23 season (output: wmi_rawseason_2010_11_to_2023_24.csv) = 0.9960930994135297
6/ WMI_raw for 2021-22 season (output: wmi_rawseason_2010_11_to_2023_24.csv) = 0.942689878530503
7/ WMI_raw for 2020-21 season (output: wmi_rawseason_2010_11_to_2023_24.csv) = 0.9874203265496059
8/ WMI_raw for CLE vs. CHA (February 20, 2026; random 2025-26 game; game_id: 0022500802; computed with current definitions from NBA CDN play-by-play) = 0.7185909980430528
9/ WMI_rawgame list for completed 2025-26 regular-season games (as of March 23, 2026; output: wmi_rawgames_2025_26_asof_2026_03_23.csv) has `games_succeeded = 1034`, `games_failed = 2` (current NBA CDN `403` responses on `0022500652` and `0022501003`), `mean_game_wmi_raw = 0.9344508632517702`, and `std_game_wmi_raw = 0.35882259210043344`
10/ WMI for 2025-26 season (controlled logistic model; as of March 23, 2026; output: wmi_controlled_2025_26_summary_asof_2026_03_23.csv) has `games_succeeded = 1034`, `games_failed = 2`, `rows_excluded_intentional = 720`, `beta_trigger = -0.10327505778698004`, and `odds_ratio_trigger = 0.9018788705555008` for trigger `L_count_t`
