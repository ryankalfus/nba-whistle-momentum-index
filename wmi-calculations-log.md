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
10/ WMI for 2025-26 season (controlled logistic model; as of March 23, 2026; output: wmi_controlled_2025_26_summary_asof_2026_03_23.csv) has `games_succeeded = 1034`, `games_failed = 2`, `rows_excluded_intentional = 720`, `rows_excluded_score_margin = 32438`, `rows_excluded_total = 33109`, `beta_trigger = -0.11880345006084772`, and `odds_ratio_trigger = 0.8879823164811339` for trigger `L_count_t`
11/ WMI_controlled for OKC vs. MIL (February 12, 2026; output: wmi_controlledgame_breakdown_okc_mil.csv) = 0.4577664628208559
12/ WMI_controlled for 2025-26 season (mirrored March 1, 2026 scope; output: wmi_controlledseason_2025_26_summary_asof_2026_03_01.csv) = 0.9076415767800788 with `games_succeeded = 895`, `games_failed = 1`, `rows_excluded_score_margin = 35704`, `rows_excluded_intentional = 574`, and `rows_excluded_total = 36247`
13/ WMI_controlled for 2024-25 season (output: wmi_controlledseason_2024_25_summary.csv) = 0.9184000344305718
14/ WMI_controlled for 2023-24 season (output: wmi_controlledseason_2010_11_to_2023_24.csv) = 0.9254265988153246
15/ WMI_controlled for 2022-23 season (output: wmi_controlledseason_2010_11_to_2023_24.csv) = 0.9465312412672284
16/ WMI_controlled for 2021-22 season (output: wmi_controlledseason_2010_11_to_2023_24.csv) = 0.8940441572083543
17/ WMI_controlled for 2020-21 season (output: wmi_controlledseason_2010_11_to_2023_24.csv) = 0.9241352358771234
18/ WMI_controlled for CLE vs. CHA (February 20, 2026; game_id: 0022500802; output: wmi_controlledgame_breakdown_0022500802.csv) = 0.7286340884318196
19/ WMI_controlledgame list for completed 2025-26 regular-season games (mirrored March 23, 2026 scope; output: wmi_controlledgames_2025_26_asof_2026_03_23.csv) has `games_succeeded = 1033`, `games_failed = 3` (`0022500405`, `0022500652`, `0022501003`), `mean_game_wmi_controlled = 0.7661223911051365`, and `std_game_wmi_controlled = 0.4630505447819352`
