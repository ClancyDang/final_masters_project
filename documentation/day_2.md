# Day 2 — League positional templates and Forest comparisons

**Date:** 21–22 November 2026

**Project:** ScoutAgent — Final Master Project

**Initial club:** Nottingham Forest FC

## Purpose of this development session

Day 1 produced a working Nottingham Forest defender action-location prototype. The next objective was to turn that prototype into a league-wide analytical method that could:

1. assign a specific position to each eligible appearance;
2. build stable Premier League positional templates;
3. compare Forest players with independent league baselines;
4. validate whether the results are robust enough for later tactical-fit analysis; and
5. expose the comparisons through the Streamlit application.

The project has now progressed from isolated match maps to reusable player profiles and positional league templates. Similarity still describes the conventionality of a player's action locations, not performance quality or tactical suitability.

## 1. Repository organisation and data protection

The project was reorganised into a reproducible GitHub repository with separate locations for documentation, notebooks, build scripts, reusable source code and tests.

Important repository decisions were:

- Raw licensed event data is stored locally under `data/raw/eventing_FMP/`.
- Derived event-level and analytical outputs are stored under `data/processed/`.
- Both raw and processed data directories are ignored by Git.
- Only `data/README.md` is committed from the data directory.
- Notebook outputs containing derived licensed data are not required for reproduction and should not be committed accidentally.
- Application dependencies are recorded in `requirements.txt`.
- Development and notebook dependencies are recorded in `requirements-dev.txt`.
- The local `.venv/`, caches and temporary files are ignored.

The repository was created at:

```text
https://github.com/ClancyDang/final_masters_project
```

This creates a clear distinction between code that can be shared publicly and football data that requires provider and university permission.

## 2. Formation and position mapping

The provider's broad squad labels were not precise enough for positional templates. For example, a player labelled `Defender` could have appeared as a centre-back, full-back or wing-back. Positions therefore needed to be assigned per appearance rather than permanently per player.

### Provider decoding

The raw lineup information contains:

- `formation_code`: the team's starting formation;
- `lineup_slot`: the player's slot within that formation.

These values must be interpreted together. A lineup slot does not have one universal meaning across every formation. For example, a provider `RightBack` in a back four is treated differently from the corresponding wide defender in a back five.

`src/positions/formation_mapping.py` was created using the Stats Perform formation-slot reference from the Kloppy repository. The external provider decoding is kept separate from this project's own analytical rules.

The mapping produces:

- `formation_name`;
- `decoded_provider_position`;
- `standardised_position`;
- `position_group`;
- `mapping_confidence`; and
- `mapping_status`.

### Project-standardised roles

Examples of the standardised hierarchy include:

- `Left centre-back`, `Centre-back` and `Right centre-back` → `Centre-back`;
- `Left full-back` and `Right full-back` → `Full-back`;
- `Left wing-back` and `Right wing-back` → `Wing-back`;
- `Left central midfielder`, `Central midfielder` and `Right central midfielder` → `Central midfield`;
- `Left attacking midfielder`, `Attacking midfielder` and `Right attacking midfielder` → `Attacking midfield`;
- `Left winger` and `Right winger` → `Winger`; and
- `Left forward`, `Centre-forward` and `Right forward` → `Forward`.

Formation-aware rules distinguish full-backs from wing-backs:

- a provider left/right back in a back four becomes a full-back;
- a provider left/right back in a back five becomes a wing-back; and
- a left/right midfielder in a back three is treated as a wing-back.

The central analytical role is determined from the provider formation and lineup slot. It is not inferred from the positional map itself. The maps can later be used to test, describe or challenge the provider role, but they do not currently generate the label.

Unknown formations, unknown provider positions and bench slot `0` remain unresolved rather than being guessed. This makes `unresolved_appearances` an auditable quality-control output instead of silently forcing uncertain records into a template.

The mapping was reviewed in `notebooks/02_position_mapping_validation.ipynb` and covered by automated tests.

## 3. Generalising the data pipeline to the Premier League

The Forest-only notebook logic was converted into a reusable league-wide pipeline in `src/data/premier_league_pipeline.py`.

The pipeline:

- reads each available match payload once;
- imports event, lineup and formation information for all teams;
- reconstructs player appearances and minutes;
- applies the event taxonomy from Day 1;
- applies the formation-position mapping;
- retains valid direct-action start coordinates;
- applies the 60-minute eligibility rule; and
- reports missing or unresolved records through quality checks.

### League coverage

- 380 Premier League fixtures are indexed for 2025/26.
- 361 local event payloads are available.
- Missing payloads are reported rather than silently ignored.
- All 20 Premier League teams are processed by the same rules.

The main ignored local outputs are:

- `premier_league_eligible_appearances.parquet`;
- `premier_league_eligible_positional_actions.parquet`;
- `premier_league_centre_back_appearances.parquet`; and
- `premier_league_pipeline_quality_checks.csv`.

The reusable build command is:

```bash
.venv/bin/python scripts/build_league_data.py
```

The league pipeline was reviewed in `notebooks/03_premier_league_pipeline_validation.ipynb`.

## 4. Template construction methodology

The positional template is built in three stages.

### Stage 1: appearance profiles

Every eligible appearance is converted into an 18-zone vector and a 20-zone vector. Each vector is normalised to sum to 100%, so it describes the distribution of actions rather than action volume.

### Stage 2: player profiles

A player's eligible appearance vectors are averaged with equal weight. This prevents a single high-action match from dominating the player's spatial profile.

### Stage 3: league templates

Qualified player profiles are averaged with equal weight. This prevents players with more appearances from dominating the league baseline.

The current qualification rule is:

```python
MIN_PLAYER_APPEARANCES = 5
```

A player with fewer than five eligible appearances can still be displayed, but the profile is marked as provisional and does not contribute to the league template.

At least two qualified players are required for a valid template. This is necessary because a qualified player must be compared with an independent leave-one-out baseline.

## 5. Centre-back templates

Centre-back templates were implemented first because they provided the clearest reference case for validating the full method.

`src/analysis/centre_back_templates.py` creates:

- one profile per eligible centre-back appearance;
- one average profile per centre-back;
- a Premier League centre-back template for each zone layout; and
- reproducible quality checks.

The build command is:

```bash
.venv/bin/python scripts/build_centre_back_templates.py
```

The template construction was reviewed in `notebooks/04_centre_back_template_validation.ipynb`.

## 6. Comparing a player with a template

`src/analysis/player_template_comparison.py` contains reusable comparison calculations.

### Independent baseline

- A qualified player is compared with the mean of the other qualified players: a leave-one-out baseline.
- A provisional player is compared with the complete qualified template because that player did not contribute to it.

### Zone differences

For every zone:

```text
zone difference = player action share − template action share
```

A positive value means the player records a greater share of actions in that zone than the baseline. A negative value means a smaller share.

### Overall similarity

Overall similarity is based on total variation distance:

```text
similarity = 100 × (1 − 0.5 × Σ|player share − template share|)
```

- `100` means the two distributions are identical.
- `0` means they have no spatial overlap.
- A higher value means the player has a more conventional spatial distribution for the selected role.
- It does not mean the player is better.

### Percentiles

Percentiles are used to provide peer context for:

- the overall similarity score;
- eligible appearance count;
- total action count; and
- the player's share in each zone.

The midpoint method is used for tied values. Percentiles were not used to replace the underlying zone differences or similarity score; they are an additional layer of interpretation.

## 7. Centre-back validation and interpretation

The centre-back results were validated before expanding the method to other positions.

`src/analysis/centre_back_validation.py` and `scripts/validate_forest_centre_backs.py` test:

- provider-role agreement;
- bootstrap uncertainty;
- repeated split-half stability;
- sensitivity to the 18-zone and 20-zone layouts; and
- sensitivity to the selected action family.

### Bootstrap uncertainty

Bootstrap samples resample complete match appearances, not individual actions. The league baseline remains fixed, so the interval represents uncertainty in the player's appearance sample.

### Split-half stability

Repeated split-half tests divide a player's appearances into two groups and compare the resulting profiles. These estimates are only reported for players with at least ten eligible appearances.

### Layout robustness

The 18-zone and 20-zone systems produced similar centre-back scores and rankings. This supports the general reliability of the main interpretation while retaining both layouts as separate analytical views.

### Action-family sensitivity

Combined direct actions are heavily influenced by passes. Pass-only and defensive-action profiles therefore answer different football questions and should remain available separately in future versions.

### Forest observations

- The Forest profiles occupy recognisable centre-back areas.
- Murillo, and to a lesser extent Morato, show a left-sided spatial tendency relative to the league template.
- Murillo, Morato and Nikola Milenković have samples that are sufficiently stable for interpretation.
- Jair Cunha remains provisional because his small sample produces greater uncertainty and cannot support split-half validation.
- The 18-zone and 20-zone similarity results are generally close; Cunha is more sensitive because of his small sample.

These findings are documented in `notebooks/05_forest_centre_back_results_validation.ipynb`.

The main conclusion was that the centre-back pipeline is coherent enough to serve as the reference implementation for other roles, but it is not yet a complete tactical-fit model.

## 8. Full-back and wing-back templates

Wide defenders require special handling because equivalent left- and right-sided roles occur on opposite sides of the pitch.

For both full-backs and wing-backs, three template groups are created:

- left-sided role;
- right-sided role; and
- overarching role-normalised group.

### Mirrored overarching profiles

Side-specific profiles retain the original coordinates. For an overarching template, right-sided appearances are mirrored across the width of the pitch:

```text
role_normalised_y = 100 − original_y
```

Left-sided appearances remain unchanged. This aligns tactically equivalent left- and right-sided actions without overwriting the original coordinates.

The original and normalised coordinates are both retained for auditing.

### Validation findings

- The full-back templates passed orientation and quality checks.
- Neco Williams, Ola Aina and Nicolò Savona qualify for the overarching Forest full-back comparison.
- Williams qualifies for the left full-back template.
- Aina and Savona qualify for the right full-back template.
- Williams and Aina have the strongest within-player stability.
- Savona qualifies with nine appearances but remains below the ten-appearance split-half threshold.
- The two layouts broadly agree for full-backs, although less strongly than for centre-backs; they should remain separate views.
- The wing-back league templates are valid, but every Forest wing-back profile is provisional because none reaches five eligible appearances.

The implementation is in `src/analysis/wide_defender_templates.py`, and the results are documented in `notebooks/06_wide_defender_results_validation.ipynb`.

## 9. Templates for the remaining positions

The template framework was expanded to:

- goalkeeper;
- defensive midfield;
- central midfield;
- attacking midfield;
- wide midfield;
- winger; and
- forward.

Where appropriate, each group contains role-specific templates plus one overarching side-normalised template. Right-sided roles are mirrored only for the overarching template; role-specific profiles retain their original coordinates.

### Template availability

League templates have sufficient peer coverage for:

- goalkeeper;
- central midfield;
- attacking midfield;
- wide midfield;
- winger; and
- forward.

Defensive midfield is currently unavailable because fewer than two league players have five eligible appearances in the mapped group. The project reports this limitation instead of creating an unreliable baseline.

For Nottingham Forest:

- goalkeeper, central midfield, attacking midfield and forward contain qualifying samples;
- wide-midfield and winger profiles are available but provisional; and
- defensive midfield cannot yet be compared with a valid league baseline.

Coverage is documented in `notebooks/07_remaining_position_template_coverage.ipynb`. Validation results are documented in `notebooks/08_remaining_position_results_validation.ipynb`.

## 10. Expanded Streamlit application

The Streamlit prototype now has two analysis views:

### Match explorer

The original view still allows the user to:

- select a Forest defender;
- select an eligible match;
- switch between the 18-zone, 20-zone or combined map;
- inspect minutes and action count; and
- view the underlying zone distributions.

### League comparison

The new view allows the user to select:

- a position group;
- a role-specific or overarching template;
- an eligible Nottingham Forest player; and
- either zone layout.

It displays:

- template similarity;
- typicality percentile;
- eligible appearance count;
- direct-action count;
- the player's positional profile;
- the league baseline;
- a zone-by-zone difference map;
- zone shares, differences and peer percentiles; and
- the comparison methodology and limitations.

The interface supports centre-backs, full-backs, wing-backs, goalkeepers, central midfielders, attacking midfielders, wide midfielders, wingers and forwards. Defensive midfield is explicitly shown as unavailable rather than silently omitted.

### Clearer template labels

The selector naming was revised to distinguish a position group from a specific role. For example:

- `All attacking midfield roles (side-normalised)` is the overarching group;
- `Central attacking midfielder` is the central number-10 role;
- `Left attacking midfielder` is the left-specific role; and
- `Right attacking midfielder` is the right-specific role.

The same `All … roles (side-normalised)` convention is used for other multi-role groups. The displayed names changed, but the stored template identifiers and calculations did not.

### Presentation fixes

- The page and comparison plots were scaled to reduce unnecessary scrolling.
- Figure-title spacing was corrected so the overall title no longer overlaps the subplot titles.
- Explanatory text makes clear that similarity measures conventionality, not quality.
- Provisional profiles remain visible with an explicit sample warning.

During development, a `template_group` error appeared because an older Streamlit server process still held the previous imported function in memory. Restarting the local server loaded the updated function signature and resolved the error. This demonstrated that Streamlit can hot-reload the main script while an imported module remains stale in a long-running process.

## 11. Automated testing

The test suite now contains 38 passing tests covering:

- formation-slot decoding;
- formation-aware position standardisation;
- unresolved position handling;
- league pipeline taxonomy and qualifiers;
- coordinate validation;
- 18-zone and 20-zone distributions;
- equal-appearance and equal-player weighting;
- template eligibility rules;
- leave-one-out baselines;
- total-variation similarity;
- empirical percentiles and ties;
- side mirroring and original-coordinate preservation;
- bootstrap and split-half validation outputs; and
- action-family and layout robustness checks.

The complete suite can be run with:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/fmp-mpl \
  .venv/bin/python -m unittest discover -s tests -v
```

The Streamlit views were also checked with headless application tests and the running-app interface. The final changes produced no application exceptions.

## 12. Main analytical lessons from Day 2

1. **Position must be assigned per appearance.** A player can occupy different formation roles in different matches.
2. **Provider decoding and analytical standardisation are different steps.** Keeping them separate makes the assumptions auditable.
3. **Uncertain mappings should remain unresolved.** Guessing would contaminate positional templates.
4. **Normalisation must happen at several levels.** Match profiles, player averages and league templates answer different weighting problems.
5. **Independent baselines matter.** A qualified player should not contribute to the template used to evaluate that player.
6. **Similarity is not quality.** A conventional profile may fit the average role without indicating superior performance.
7. **Percentiles provide context, not a replacement metric.** The underlying shares and differences must remain inspectable.
8. **Mirroring is useful only for a clearly defined question.** It supports an overarching role comparison, while original coordinates are necessary for side-specific interpretation.
9. **Small samples must remain visible but provisional.** Removing them hides useful exploratory information, while treating them as stable would overstate the evidence.
10. **Validation should precede tactical interpretation.** Bootstrap uncertainty, split-half stability, layout robustness and action-family sensitivity reveal whether a conclusion is dependable.
11. **Action selection changes the profile.** Passing and defending should eventually become distinct scouting lenses rather than being interpreted only through one combined map.
12. **A valid league template requires enough independent peers.** Defensive midfield is withheld because the current mapped sample cannot support a defensible comparison.

## 13. Current limitations

- The source is event data, so profiles still measure action locations rather than continuous occupancy.
- Carries have not been inferred.
- The 60-minute appearance threshold remains a methodological choice that may require sensitivity testing.
- Five appearances are required to contribute to a league template, but the best threshold may vary by role.
- The combined direct-action profile is influenced by high-volume passing.
- Split-half estimates require at least ten appearances.
- Wide-midfield, winger and Forest wing-back samples are currently provisional.
- Defensive midfield lacks a viable peer baseline.
- Formation mapping currently describes the starting role and does not reconstruct in-match position changes after tactical switches.
- Similarity does not yet measure tactical fit, performance, progression, passing style or defensive effectiveness.
- Public deployment still depends on permission to use the licensed data.

## 14. Next steps

1. Add separate pass and defensive-action comparison controls to the application.
2. Interpret and validate the supported non-defender roles in more football detail.
3. Develop tactical-style features beyond starting action locations, including pass destinations, progression and defensive behaviour.
4. Decide how to represent tactical fit as a combination of several interpretable dimensions rather than one similarity score.
5. Investigate whether role-specific sample thresholds should be calibrated using league distributions.
6. Review unresolved and low-coverage positions before changing the mapping rules.
7. Preserve the distinction between exploratory provisional profiles and stable comparison samples.
8. Continue recording methodological decisions and validation findings before expanding the interface further.

## 15. GitHub milestones

The following development stages were committed and pushed:

- formation-position mapping;
- reusable Premier League pipeline;
- Premier League centre-back templates;
- Forest centre-back league comparisons;
- centre-back validation and wide-defender templates;
- remaining positional templates and validation; and
- expanded Streamlit comparisons and clearer template naming.

At the end of the session, the local `main` branch and GitHub `origin/main` were synchronized, and no licensed raw or processed data had been committed.
