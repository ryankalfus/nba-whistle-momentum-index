# Plan for NBA Analytics Research Log - Ryan Kalfus (2026)

_Converted from PDF on 2026-02-21._

Plan for NBA Analytics Research Log​
​
Goal

The goal of this project is to investigate whether foul calls in NBA games exhibit short-term clustering across
possessions. Specifically, I want to test whether a team is more (or less) likely to have a defensive foul called against
them if the opposing team experienced a defensive foul in one of its previous possessions. The data will be controlled
for game setting, including to be determined elements such as score margin, time left, and more. In simpler terms:
do referees subconsciously “balance” calls, or do whistles tend to come in streaks?
This project is not about arguing bias or conspiracy. It is about testing whether there is measurable statistical
dependence in foul calls across alternating possessions.




Scale of the Project


This will be a full-season study using the 2025–26 NBA regular season.
The unit of analysis will not be individual events (like shots or rebounds), but possessions. That means I will:


    ●​   Construct every possession in every game.​


    ●​   Identify how each possession ends.​


    ●​   Classify whether the possession ended in a defensive foul.​


    ●​   Track the outcomes of the previous 1–2 possessions by the opposing team.​


The dataset will include every possession from the season, resulting in thousands of observations. This makes the
project large enough to produce meaningful statistical results rather than anecdotal conclusions.




What I Will Be Using


Data Source


    ●​   Official NBA play-by-play data (live JSON data feed).​


    ●​   No third-party scraped datasets unless necessary.​


Tools


    ●​   Python​
    ●​    Pandas (for cleaning and structuring data)​


    ●​    NumPy (for logical operations and calculations)​


    ●​    Statistical modeling tools (likely statsmodels for regression)​


No advanced machine learning is required. The focus is on careful data construction and probability modeling.




Core Structure of the Analysis


    1.​ Convert play-by-play event data into possession-level data.​


    2.​ Define clear rules for when a possession starts and ends.​


    3.​ Identify whether each possession ends in a defensive foul.​


    4.​ Create an indicator for whether one of the previous two opposing possessions ended in a defensive foul.​


    5.​ Compare:​


              ○​   Probability of foul when prior opposing possession had a foul.​


              ○​   Probability of foul when it did not.​


    6.​ Compute a ratio (Whistle Momentum Index) to measure the strength of the effect.​


    7.​   Extend with regression analysis to control for score margin, quarter, and other game context variables.

