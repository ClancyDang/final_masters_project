# Day 1 — Nottingham Forest defender positional maps

**Date:** 20 November 2026  
**Project:** ScoutAgent — Final Master Project  
**Initial club:** Nottingham Forest FC

## Purpose of today's work

The first feature of ScoutAgent will quantify where players perform their actions on the pitch. The longer-term aim is to build positional templates from player-match maps and use them to compare players, identify roles and assess potential tactical fit.

Because the available dataset contains event data rather than tracking data, these maps cannot measure the percentage of time a player physically occupied an area. Instead, the prototype measures the percentage of a player's recorded direct actions that began in each area.

## 1. Development environment

- Created a project-specific Python virtual environment in `.venv` rather than depending on Conda or Anaconda.
- Created the `FMP Scouting` Jupyter kernel using that environment.
- Confirmed that the environment contains the packages required for the prototype, including pandas, NumPy, Matplotlib, mplsoccer, PyArrow and Streamlit.

## 2. Understanding the available data

The event package appears to use Perform/Opta-style events and a 0–100 coordinate system.

For the initial prototype, I limited the analysis to Nottingham Forest and players carrying the provider's broad `Defender` squad label. I have deliberately not assigned centre-back, full-back or wing-back roles yet.

### Coverage

- Forest have 38 fixtures in the 2025/26 Premier League fixture index.
- Local event payloads are available for 36 matches.
- The final two payloads are missing: Manchester United and Bournemouth.
- The 36 available matches contain 61,522 events for both teams.
- 29,720 events are attributed to Nottingham Forest.
- 29,082 Forest events contain a player ID.
- 11,584 events belong to broadly labelled Forest defenders.

## 3. Important event fields

### Event identifiers

- `event_id` is the event sequence number for one team within one match.
- `provider_event_id` is the globally unique identifier for the event record.
- A reproducible quality check confirmed that `provider_event_id` is unique and that the combination of match, team and `event_id` is also unique.

### Event types

`type_id` identifies the provider's event type. Examples include:

- `1`: pass
- `3`: take-on
- `4`: foul
- `7`: tackle
- `8`: interception
- `12`: clearance
- `44`: aerial
- `49`: ball recovery

There is no direct carry event type in this feed. Carries would have to be inferred from event sequences, such as the location of a ball receipt and the player's following action. Carry derivation has been deliberately deferred because it introduces additional assumptions and is not required for the first action-location prototype.

### Coordinates

- `x` runs from 0 to 100 along the length of the pitch.
- `x = 0` represents the team's own goal.
- `x = 100` represents the opposition goal.
- `y` runs from 0 to 100 across the width of the pitch.
- Increasing `x` therefore represents progression toward the opposition goal.
- Some `Out` records use coordinates outside the 0–100 range to describe the ball leaving the pitch. These administrative records must not enter a positional map.

I validated the attacking direction using all shot events from home and away teams in both halves. Median shot locations were consistently around `x = 86–87`, confirming that both teams attack toward `x = 100`. No half-by-half coordinate mirroring is required.

### Qualifiers

`qualifiers` contain additional information about an event. For example, a pass may have qualifiers describing its direction, destination, length and angle.

The notebook creates `qualifier_map`, a convenient dictionary that avoids searching the complete qualifier list repeatedly. For example:

```python
end_x = row["qualifier_map"].get(140)
end_y = row["qualifier_map"].get(141)
```

Qualifiers `140` and `141` provide destination coordinates for passes and some other events. None of the 158 defender take-on attempts contained these destination qualifiers. I therefore decided to retain take-ons as point locations rather than inventing endpoints.

## 4. Event cleaning and taxonomy

The raw event feed mixes direct football actions with outcomes, contextual records and administrative records. I created an explicit four-family taxonomy.

### Direct actions

Examples include passes, take-ons, tackles, attempted tackles, interceptions, clearances, aerials, challenges, recoveries, touches, dispossessions, shields and blocked passes.

These are the primary inputs for the first positional fingerprint.

### Attacking outcomes

- Miss
- Post
- Attempt saved
- Goal

### Contextual outcomes

- Corner awarded
- Error
- Offside provoked

### Administrative records

- Ball out
- Card
- Player on
- Player off
- Deleted event

Administrative records are excluded from action-location maps.

### Cleaning results

- 11,584 raw defender event rows
- 10,565 valid spatial defender events
- 10,257 direct positional actions
- 100 attacking outcomes
- 208 contextual outcomes
- 1,019 administrative records
- 7,057 pass actions
- 2,373 defensive actions
- 100 shots
- 0 unknown event types
- 0 unclassified event families

## 5. Main analytical tables

### Fixtures, squad and raw events

- `matches_index`: complete Premier League fixture index.
- `forest_fixtures`: Forest's 38 fixtures and payload availability.
- `forest_squad`: normalized Forest squad records.
- `forest_defenders`: players with the provider's broad `Defender` label.
- `events`: both teams' events from the 36 available Forest matches.
- `forest_events`: all Forest events.
- `forest_player_events`: Forest events containing a player ID.
- `forest_defender_events`: raw player-attributed events for broadly labelled defenders.

### Cleaned event views

- `defender_events_enriched`: readable event labels, taxonomy, numeric coordinates, destinations and quality flags.
- `valid_spatial_events`: valid on-pitch events excluding administrative records.
- `direct_actions`: direct football actions.
- `attacking_outcomes`: defender shot outcomes.
- `contextual_outcomes`: contextual provider records.
- `administrative_events`: substitutions, cards, ball-out and deleted records.
- `positional_actions`: direct actions selected for the positional fingerprint.
- `defender_passes`: pass-related actions.
- `defender_defensive_actions`: defensive action subset.
- `defender_shots`: shot outcomes.
- `take_on_events`: defender take-on attempts.
- `successful_take_ons`: successful take-ons.

### Lineups and playing time

- `forest_team_setups`: initial Forest team-setup events.
- `forest_lineup_slots`: player, formation and lineup-slot records.
- `forest_starting_defenders`: broadly labelled defenders who started each match.
- `player_match_minutes`: reconstructed minutes for every Forest appearance.
- `defender_match_minutes`: reconstructed minutes for defender appearances.

Playing time is reconstructed from starting lineups, substitution events and dismissal events. The current calculation uses the provider's elapsed match clock, including stoppage time.

## 6. Eligibility decision

The positional templates will become baselines for comparing other players, so stability is more important than retaining every short appearance.

The prototype therefore uses:

```python
MIN_ELIGIBLE_MINUTES = 60
```

Sixty minutes represents approximately two-thirds of regulation time.

Current rules:

- An appearance is eligible when `minutes_played >= 60`.
- There is no minimum-action exclusion.
- There is no low-action warning yet.
- Minutes played and action count are always displayed beside the map.
- A future warning threshold can be calibrated from league-wide action-count distributions, potentially using a percentile approach by action channel or role.

The resulting tables are:

- `defender_match_action_counts`
- `defender_appearance_samples`
- `eligible_defender_appearances`
- `eligible_positional_actions`

The Forest data contains:

- 167 reconstructed defender appearances
- 144 eligible appearances of at least 60 minutes
- 9,739 eligible direct positional actions
- 10 defenders represented among eligible appearances

## 7. First positional-map prototype

The first test case is Murillo against Brentford on 17 August 2025.

- Minutes played: 99.8 provider minutes
- Direct actions: 69
- All 69 actions have valid Opta start coordinates.

The map represents:

> The percentage of Murillo's recorded direct actions that began in each pitch zone during the match.

It does not represent continuous time spent in each area.

### Positional 20-zone layout

The mplsoccer `positional="full"` layout creates 20 unequal tactical zones, including the half-spaces and differentiated central areas.

### Traditional 18-zone layout

The traditional layout divides the pitch into:

- Six equal lengthwise bands
- Three equal widthwise bands
- Eighteen equal rectangles

Zones 1–3 are nearest the player's own goal and zones 16–18 are nearest the opposition goal. The numbering runs left-to-right when the pitch is displayed vertically.

### Validation and presentation

- Both layouts use exactly the same 69 actions.
- Each distribution sums to 100%.
- Both maps use the same colour scale.
- White points show individual action locations.
- Every zone displays its zone ID and action percentage.
- The figure displays the player, match, date, minutes and action count.

The reusable outputs are:

- `selected_appearance`
- `selected_appearance_actions`
- `positional_20_distribution`
- `traditional_18_distribution`

## 8. First Streamlit prototype

I learned that Streamlit is a Python framework that converts Python scripts into interactive web applications. It starts a local web server and renders `st.*` commands as browser elements. When a user changes a widget, Streamlit reruns the script from top to bottom with the new selection.

The prototype was separated into three responsibilities.

### Offline data preparation

`scripts/build_streamlit_data.py` reproduces the notebook's preparation steps and exports compact Parquet tables:

- `forest_eligible_defender_appearances.parquet`
- `forest_eligible_positional_actions.parquet`

The application therefore does not reprocess all raw JSON after every interaction.

### Reusable visualization logic

`src/visualizations/positional_maps.py`:

- Validates the selected actions.
- Calculates both zone distributions.
- Confirms that no actions are lost and shares sum to one.
- Draws one or both layouts.
- Returns the figure and underlying tables.

### Interactive interface

`streamlit_app.py` provides:

- A Forest defender selector.
- A dependent match selector containing that player's eligible appearances.
- A layout selector for both maps, the 20-zone map or the 18-zone map.
- Minutes played, action count and eligibility-rule metrics.
- The selected positional map.
- Expandable distribution tables.
- A methodology and limitations section.

The interface currently contains all 144 eligible appearances rather than only the Murillo example. Changing a player, match or layout reruns the script and regenerates the relevant map.

The processed files are cached with `@st.cache_data`, so they are not reloaded unnecessarily after every widget change.

### Running the application locally

From the project directory:

```bash
.venv/bin/streamlit run streamlit_app.py
```

Streamlit normally makes the application available at:

```text
http://localhost:8501
```

The terminal must remain open while the server is running. Pressing `Ctrl+C` stops it.

The interface was tested by changing players, matches and layouts. It ran without application exceptions.

## 9. Important analytical lessons

1. **Event data is not tracking data.** Event locations describe where recorded actions occurred, not where a player continuously stood or moved.
2. **A normalized map measures distribution rather than volume.** A player with 40 actions and a player with 80 actions can have similar percentage maps, so the raw action count must remain visible.
3. **Minutes and actions describe different aspects of sample quality.** Minutes measure opportunity; action count measures the amount of spatial evidence.
4. **Provider labels are broad.** The current `Defender` label does not distinguish centre-backs, full-backs and wing-backs.
5. **Coordinate orientation must be validated.** A wrongly mirrored match would mix defensive and attacking zones and invalidate the resulting template.
6. **The visualization is not the analytical product by itself.** The underlying zone vectors are what can later be averaged, clustered and compared.
7. **Streamlit creates interactivity through reruns.** The widgets return Python values, and the script filters the data and redraws the map using those values.

## 10. Current limitations and deferred work

- Two Forest match payloads are missing.
- The analysis currently includes only Nottingham Forest defenders.
- Detailed defender roles have not been assigned.
- Carries have not been inferred.
- The primary map currently combines all direct-action types, so high-volume passes may strongly influence the distribution.
- No league-wide low-action threshold has been calibrated.
- No averaged player or positional templates have been created yet.
- The two zone systems have not yet been compared across a large set of appearances.
- Public deployment must wait until the event-data sharing and licensing restrictions are confirmed.

## 11. Next steps

1. Inspect several Forest defender maps for footballing plausibility.
2. Decide how to categorize defender roles using lineup information and action-location patterns.
3. Convert every eligible player-match appearance into reusable 18-zone and 20-zone vectors.
4. Compare how stable the two zone systems are across matches.
5. Decide how individual match maps should be averaged into player and role templates.
6. Expand the pipeline to eligible Premier League defenders.
7. Map Forest players onto the resulting positional templates.
8. Continue improving the Streamlit interface as the analytical method develops.
