# EA SPORTS FC 27 Player Ratings

All 19,789 players from EA's official ratings API for EA SPORTS FC 27, snapshot taken 2026-09-12. One row per player. The `snapshot_date` column is the same on every row of a version and changes with each new one, so you can line up successive versions and follow rating changes through the reveal window, launch day, and later title updates.

The file has every stat EA publishes: the six card facets (pace through physicality), the 34 detailed attributes behind them, and the goalkeeping stats for the 2,204 goalkeepers in the set.

`playstyles` lists a player's PlayStyles, comma separated (41% of players have at least one). A PlayStyle+ comes last and keeps EA's own trailing `+`, as in `Finesse Shot+`.

EA's schema has `height_cm` and `weight_kg`, but EA has not published values for them yet. The columns are present and empty in this version and will fill in a later one once EA populates them.

## Men's and women's football

Both divisions are in this one file. The `gender` column separates them with EA's own values, "Men's Football" and "Women's Football": 17,849 men's players and 1,940 women's players. Filter with `df[df.gender == "Women's Football"]`. The two share no leagues, so a split is clean if you want one.

`common_name` is filled only for players EA gives a single-name form (15% of rows), and `alternate_positions` only for players who have any (65% of rows). Blanks in either column are expected.

## Columns

| column | description |
|--------|-------------|
| `player_id` | EA's numeric player id, stable across snapshots. |
| `common_name` | Single display name EA gives some players. Blank for most. |
| `first_name` | First name. |
| `last_name` | Last name. |
| `overall_rating` | Overall card rating, 1-99. |
| `position` | Primary position, EA's short label (GK, CB, ST, ...). |
| `alternate_positions` | Other playable positions, space separated. Blank if none. |
| `club` | Club the player plays for. |
| `league` | League the club plays in. |
| `nationality` | Country EA lists for the player. |
| `gender` | EA's division label: "Men's Football" or "Women's Football". |
| `preferred_foot` | Right or Left. |
| `skill_moves` | Skill moves star rating, 1-5. |
| `weak_foot` | Weak foot star rating, 1-5. |
| `height_cm` | Height in centimeters. |
| `weight_kg` | Weight in kilograms. |
| `birthdate` | Birthdate as an ISO 8601 date (YYYY-MM-DD). |
| `playstyles` | PlayStyles, comma separated. A PlayStyle+ keeps EA's trailing +. |
| `pace` | Pace card facet, 1-99. |
| `shooting` | Shooting card facet, 1-99. |
| `passing` | Passing card facet, 1-99. |
| `dribbling` | Dribbling card facet, 1-99. |
| `defending` | Defending card facet, 1-99. |
| `physicality` | Physicality card facet, 1-99. |
| `attacking_crossing` | Crossing detailed attribute (attacking group), 1-99. |
| `attacking_finishing` | Finishing detailed attribute (attacking group), 1-99. |
| `attacking_heading_accuracy` | Heading accuracy detailed attribute (attacking group), 1-99. |
| `attacking_short_passing` | Short passing detailed attribute (attacking group), 1-99. |
| `attacking_volleys` | Volleys detailed attribute (attacking group), 1-99. |
| `skill_dribbling` | Dribbling detailed attribute (skill group), 1-99. |
| `skill_curve` | Curve detailed attribute (skill group), 1-99. |
| `skill_fk_accuracy` | Free kick accuracy detailed attribute (skill group), 1-99. |
| `skill_long_passing` | Long passing detailed attribute (skill group), 1-99. |
| `skill_ball_control` | Ball control detailed attribute (skill group), 1-99. |
| `movement_acceleration` | Acceleration detailed attribute (movement group), 1-99. |
| `movement_sprint_speed` | Sprint speed detailed attribute (movement group), 1-99. |
| `movement_agility` | Agility detailed attribute (movement group), 1-99. |
| `movement_reactions` | Reactions detailed attribute (movement group), 1-99. |
| `movement_balance` | Balance detailed attribute (movement group), 1-99. |
| `power_shot_power` | Shot power detailed attribute (power group), 1-99. |
| `power_jumping` | Jumping detailed attribute (power group), 1-99. |
| `power_stamina` | Stamina detailed attribute (power group), 1-99. |
| `power_strength` | Strength detailed attribute (power group), 1-99. |
| `power_long_shots` | Long shots detailed attribute (power group), 1-99. |
| `mentality_aggression` | Aggression detailed attribute (mentality group), 1-99. |
| `mentality_interceptions` | Interceptions detailed attribute (mentality group), 1-99. |
| `mentality_positioning` | Positioning detailed attribute (mentality group), 1-99. |
| `mentality_vision` | Vision detailed attribute (mentality group), 1-99. |
| `mentality_penalties` | Penalties detailed attribute (mentality group), 1-99. |
| `mentality_composure` | Composure detailed attribute (mentality group), 1-99. |
| `defending_awareness` | Awareness detailed attribute (defending group), 1-99. |
| `defending_standing_tackle` | Standing tackle detailed attribute (defending group), 1-99. |
| `defending_sliding_tackle` | Sliding tackle detailed attribute (defending group), 1-99. |
| `goalkeeping_diving` | Diving detailed attribute (goalkeeping group), 1-99. |
| `goalkeeping_handling` | Handling detailed attribute (goalkeeping group), 1-99. |
| `goalkeeping_kicking` | Kicking detailed attribute (goalkeeping group), 1-99. |
| `goalkeeping_positioning` | Positioning detailed attribute (goalkeeping group), 1-99. |
| `goalkeeping_reflexes` | Reflexes detailed attribute (goalkeeping group), 1-99. |
| `edition` | Game edition the snapshot came from, e.g. fc27. |
| `snapshot_date` | Date the snapshot was taken. Same on every row of a version. |

## Source and legal

The data comes from EA's public ratings API, the same feed behind the ratings pages on ea.com, fetched with a delay between requests. All player data and names belong to Electronic Arts. This is an unofficial, non-commercial snapshot for analysis and education, and it includes no imagery.

Exported 2026-09-14 by the [ea-fc-player-stats](https://github.com/mikedpad/ea-fc-player-stats) pipeline.
