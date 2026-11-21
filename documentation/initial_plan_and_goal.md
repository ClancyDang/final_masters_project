# ScoutAgent — Initial plan and end goal

**Document status:** Consolidated working plan   
**FMP route:** Sporting Management and Scouting  
**Initial club:** Nottingham Forest FC

This document combines the original long-term vision for ScoutAgent with the practical application plan. It is a living plan and should change as the data, university requirements and analytical methodology become clearer.

## 1. Background

ScoutAgent is being developed as the Final Master Project for the Master's programme in Sport Analysis & Analytics at Universidad Europea de Madrid and the Real Madrid Graduate School.

### Key dates

- **18 December 2026:** First interim submission covering the club, project topic, objectives, scope and data sources.
- **26 February 2027:** Second interim submission covering tool-development progress, initial findings and difficulties.
- **11 June 2027:** Final project submission.

The project should be developed incrementally. The priority is to build a simple, reliable and useful scouting application first, then extend it as the technical and analytical methodology improves.

## 2. Core vision

ScoutAgent will be a web application that automates useful parts of a football club's scouting and recruitment-analysis workflow while keeping final decisions with human scouts, coaches and recruitment analysts.

The long-term ambition is an evidence-based, AI-assisted recruitment platform. The initial application does **not** require AI. It should first become a dependable conventional analytical tool with transparent calculations, validated data and reproducible outputs.

The application should eventually help a user:

1. Define a club's positional and tactical recruitment need.
2. Specify playing-model requirements and recruitment constraints.
3. Search and filter a player database.
4. Calculate transparent, role-specific performance metrics.
5. Compare candidates with suitable peers and current squad players.
6. Evaluate tactical and positional fit.
7. Create and manage a shortlist.
8. Produce an evidence-backed recommendation and scouting report.
9. Export the results for further review and communication.

ScoutAgent should support professional judgement rather than automatically make recruitment decisions.

## 3. University FMP requirements

The university describes the FMP as:

> An individual tool addressing a real need at a club.

The project should demonstrate:

- An individual, tailored solution for a specific club.
- Technical proficiency with data and analytical tools.
- Interpretation within a specific sporting context.
- Conclusions and recommendations supported by checkable evidence.

### Player scouting and comparison

- Define positional requirements from the club's playing model.
- Produce individual player profiles.
- Build player-search and comparison functionality.
- Make evidence-based recruitment recommendations.

### Coaching decision

- Justify retaining or replacing the club's coach.
- Consider the playing model, current squad and club objectives.

### 2027/28 squad planning

- Analyze the current squad.
- Recommend retained players, departures and signings.
- Evaluate positional coverage and squad balance.
- Align the proposed squad with the playing model.

### Financial feasibility

- Develop an evidence-based transfer plan.
- Meet the specified transfer-balance condition: sales minus acquisition costs must be greater than or equal to zero.
- Consider wages and other relevant costs separately.

The precise interpretation of these requirements, including which components must appear inside the web application, should be confirmed with the FMP supervisor.

## 4. Final deliverables

1. A GitHub repository containing the code, ETL pipeline, analytical workflow, automation and run instructions.
2. A functioning analytical tool and its solution files.
3. A PDF presentation documenting the methodology, process, results and reports.
4. A demonstration video of no more than 45 minutes.
5. A one-page FMP poster.
6. An in-person project defence.

## 5. Intended users and problem

The intended users are football scouts, recruitment analysts and coaches who need to translate a club's playing model into transparent player-search and comparison criteria.

A typical use case could be:

> A recruitment analyst wants to identify defensive midfielders suited to a high-pressing system who demonstrate strong ball recovery and progressive passing.

The application should help the analyst define the requirement, identify an appropriate comparison population, search eligible players, inspect the evidence and produce a reproducible recommendation.

## 6. Development principles

### Build incrementally

Start with a small working application and add complexity only when the underlying data and methodology are understood.

### Keep the analysis explainable

- Make metrics, weights and comparison populations visible.
- Document assumptions, transformations and limitations.
- Avoid unexplained black-box rankings.
- Preserve traceability from outputs to source data.

### Keep the human responsible

The system can organize evidence and support decisions, but it should not present automated output as a definitive recruitment judgement.

### Learn through implementation

The project should improve the developer's understanding of:

- Football tactics, playing models and positional roles.
- Scouting and recruitment methodology.
- Football metrics and their limitations.
- Python, pandas, NumPy and SQL.
- Statistics and player-comparison methods.
- Streamlit application development.
- Plotly, Matplotlib and mplsoccer.
- Software architecture, testing and documentation.
- Machine learning and AI only after the analytical foundation is reliable.

### Prefer maintainability over unnecessary complexity

Use straightforward tools and a modular architecture. Every important component should be understandable and maintainable without depending entirely on generated code.

## 7. Available data

The university has indicated that the supplied event data covers:

- 2025/26 Premier League
- 2025/26 LaLiga
- 2025/26 Serie A
- 2025/26 Bundesliga
- 2025/26 Ligue 1
- 2025/26 Champions League
- 2025/26 Europa League
- 2025/26 Conference League
- 2026 FIFA World Cup

The exact coverage, structure, provider documentation, missing data and available metrics must be validated before each dataset is used.

University-provided data should be used wherever appropriate. Any supplementary source should be documented with its purpose, coverage, refresh date and limitations.

## 8. High-level architecture

```text
Raw event and player data
        ↓
Validation and cleaning
        ↓
Canonical player, team, match and event tables
        ↓
Player-match and player-season aggregates
        ↓
Per-90 metrics, success rates and percentiles
        ↓
Role profiles and transparent scoring models
        ↓
Parquet files and/or DuckDB
        ↓
Streamlit application
        ↓
Searches, profiles, comparisons, shortlists and reports
```

The Streamlit application should not process the complete raw package on every page load or interaction. Raw data should be processed separately and saved as compact analytical tables.

## 9. Proposed application workflow

### 9.1 Club requirements

The user defines the recruitment problem before searching:

- Target club.
- Position and tactical role.
- Playing-model requirements.
- Preferred competitions.
- Minimum playing time.
- Age range when available.
- Preferred foot when available.
- Financial limits when transfer and wage data become available.
- Required metrics and their weights.

Criteria and weights should remain visible and editable so the process is explainable.

### 9.2 Player search

Potential filters include:

- Competition.
- Team.
- Position or tactical role.
- Minimum minutes.
- Age, nationality and preferred foot when available.
- Individual metric thresholds.
- Tactical-role suitability.

The results table should eventually show:

- Player and current club.
- Competition and position.
- Minutes, starts and appearances.
- Important raw and per-90 metrics.
- Role-specific percentiles.
- Tactical-role fit.
- Actions for opening the profile or adding the player to a shortlist.

### 9.3 Player profile

Each profile should contain:

- Player, club, competition and position information.
- Minutes and sample-size context.
- Raw totals and per-90 metrics.
- Position- or role-specific percentiles.
- Strengths and weaknesses.
- Radar charts or percentile bars where justified.
- Passing, defensive-action or positional maps where supported by the data.
- Tactical-fit interpretation.
- Data-quality warnings and limitations.
- An add-to-shortlist action.

### 9.4 Candidate comparison

Allow approximately two to four players to be compared using:

- A side-by-side KPI table.
- Per-90 values.
- Percentile comparisons.
- Radar charts or percentile bars.
- Sample-size warnings.
- Strengths and weaknesses.
- Comparison with the target club's current player.
- Financial information when available.

### 9.5 Shortlist

Allow the scout to:

- Add and remove players.
- Assign `Longlist`, `Shortlist`, `Watch` or `Recommended` status.
- Rank candidates.
- Save observations and risk notes.
- Select a preferred candidate.
- Preserve the shortlist between sessions.

### 9.6 Report generation

A reproducible scouting report should contain:

- The club's identified need.
- Search criteria and comparison population.
- KPI definitions and methodology.
- Candidate profile and visualizations.
- Strengths and weaknesses.
- Tactical fit.
- Comparison with alternative candidates.
- Sample size, uncertainty and limitations.
- Final evidence-backed recommendation.

Search results should be downloadable as CSV. Selected candidates may later be exportable as HTML or PDF reports.

### 9.7 Methodology and data quality

The application should document:

- Data provider and season coverage.
- Last data refresh.
- KPI definitions.
- Minimum-minutes rules.
- Missing-value treatment.
- Match and player deduplication.
- Known provider errors and missing matches.
- Coordinate assumptions and transformations.
- Comparison-population definitions.
- Supplementary data sources.

## 10. Proposed application pages

The eventual application may include:

1. **Club overview:** playing model, squad composition, performance and recruitment needs.
2. **Player search:** filters, eligibility rules, relevant metrics and candidate ranking.
3. **Player profile:** contextual statistics, visualizations and tactical interpretation.
4. **Player comparison:** side-by-side comparison of shortlisted candidates and current players.
5. **Shortlist:** statuses, rankings, notes and risk tracking.
6. **Report generator:** reproducible scouting-report creation and export.
7. **Methodology:** data coverage, metric definitions, assumptions and limitations.
8. **ScoutAgent assistant:** a future natural-language interface over validated analytical functions.

These pages are preliminary and should be prioritized according to the final FMP scope.

## 11. Proposed data model

### `players`

- `player_id`
- `player_name`
- `country`
- `date_of_birth`
- `age`
- `preferred_foot`
- `height`
- `primary_position`

### `teams`

- `team_id`
- `team_name`
- `competition_id`
- `season`

### `player_team_season`

- `player_id`
- `team_id`
- `competition_id`
- `season`
- `position`
- `shirt_number`
- `minutes`
- `appearances`
- `starts`

### `player_metrics`

- `player_id`
- `team_id`
- `competition_id`
- `season`
- `minutes`
- Calculated totals
- Per-90 metrics
- Success rates

### `events`

- `match_id`
- `event_id`
- `player_id`
- `team_id`
- `event_type_id`
- `period`
- `minute`
- `second`
- `x`
- `y`
- `outcome`
- `qualifiers`

### `role_percentiles`

- `player_id`
- `role`
- `comparison_population`
- `metric`
- `raw_value`
- `per90_value`
- `percentile`

### `shortlists`

- `shortlist_id`
- `player_id`
- `status`
- `rank`
- `scout_note`
- `created_at`

## 12. Raw-data preparation

The preprocessing pipeline should:

1. Validate relevant JSON and CSV files.
2. Exclude provider-error payloads.
3. Deduplicate matches using stable match identifiers and update timestamps where necessary.
4. Normalize competition, team, match and player identifiers.
5. Select canonical player names and positions.
6. Validate and standardize event coordinates.
7. Create player-match aggregates.
8. Create player-team-season aggregates.
9. Calculate per-90 values and success rates.
10. Calculate position- and role-specific percentiles.
11. Save compact Parquet files and/or a DuckDB database for the application.

## 13. Technology stack

- **Python:** application and analytical code.
- **Streamlit:** web application interface.
- **pandas or Polars:** cleaning and transformation.
- **NumPy:** numerical calculations.
- **SQL and DuckDB:** analytical queries and compact local storage.
- **Parquet:** compressed processed tables.
- **SQLite:** persistent shortlist statuses and scout notes if required.
- **Plotly:** interactive charts where appropriate.
- **Matplotlib and mplsoccer:** football-specific visualizations.
- **scikit-learn:** future statistical and machine-learning methods.
- **pytest:** automated testing.
- **Ruff:** formatting and code-quality checks.
- **Git and GitHub:** version control, documentation and submission.
- **OpenAI API:** possible future AI-assistant integration.
- **Codex:** development assistance and technical mentoring.

## 14. Proposed repository structure

```text
streamlit_app.py

app/
    pages/
        club_requirements.py
        player_search.py
        player_profile.py
        player_comparison.py
        shortlist.py
        report_generator.py
        methodology.py
    components/
        filters.py
        player_card.py
        metric_table.py
        charts.py
    state.py

src/
    data/
        loaders.py
        cleaning.py
        validation.py
        database.py
    metrics/
        per90.py
        percentiles.py
        role_profiles.py
        scoring.py
    reports/
        scouting_report.py
    visualizations/
        radar.py
        heatmap.py
        passing_map.py

scripts/
    build_database.py
    process_events.py
    validate_data.py

data/
    processed/
    app/

tests/
requirements.txt
README.md
.gitignore
```

The exact structure may evolve, but data preparation, analytical logic, visualization and interface code should remain separated.

## 15. Minimum viable product

The smallest useful application should focus on one complete recruitment workflow:

- Use domestic-league player data.
- Select one target club.
- Select one position or tactical role.
- Apply a minimum-minutes rule.
- Search and rank eligible players using a small set of justified KPIs.
- Open an individual player profile.
- Compare two or more players.
- Add candidates to a shortlist.
- Display the methodology and limitations.

The MVP does **not** need:

- AI functionality.
- Every football position.
- Every possible event map.
- Live scraping.
- Authentication.
- A complete financial model.

## 16. Initial implementation direction

The first target club has been selected as **Nottingham Forest FC**.

The first working feature explores defender action-location maps using event data. It is intended to establish a transparent spatial foundation that may later support:

- Empirical defender-role definitions.
- Player-match positional fingerprints.
- Passing and carrying-style profiles.
- Comparison with Forest's current players.
- Tactical-fit assessment against club-specific templates.

This feature is an analytical prototype rather than the complete scouting workflow described in the MVP.

## 17. Development roadmap

### Stage 1 — Foundational application

**Target: 18 December 2026**

- Define the club, problem, objectives, scope and data sources.
- Build the Streamlit application shell and navigation.
- Validate and combine the initial domestic data.
- Create canonical player and match tables.
- Choose one recruitment role or analytical use case.
- Define a small, justified KPI set.
- Calculate basic per-90 metrics and comparison percentiles.
- Build an initial player search or player-profile workflow.
- Demonstrate at least one working analytical feature.

The formal submission does not require a working prototype at this stage, but one would provide useful additional progress.

### Stage 2 — Advanced scouting analytics

**Target: 26 February 2027**

- Expand role-specific performance metrics.
- Develop positional recruitment profiles.
- Add tactical-fit criteria.
- Improve contextual and percentile comparisons.
- Develop transparent weighted scoring.
- Build player comparison.
- Add shortlist storage and scout notes.
- Add club-specific squad analysis.
- Add event-based visualizations.
- Begin automated scouting-report generation.

### Stage 3 — AI-assistant integration

**Provisional target: spring 2027**

Only after the analytical workflow is reliable, introduce a single AI assistant that can:

- Interpret natural-language scouting requests.
- Select appropriate validated analytical functions.
- Query the player database.
- Run reproducible statistical calculations.
- Generate relevant visualizations.
- Explain results with supporting evidence.
- Identify uncertainty, limitations and missing data.

The assistant should orchestrate reliable tools rather than invent statistics or unsupported tactical conclusions.

### Stage 4 — FMP completion

**Target: 11 June 2027**

- Complete club-specific scouting recommendations.
- Address 2027/28 squad planning.
- Complete applicable coaching and financial analysis.
- Add external age, preferred-foot, contract and financial data where feasible.
- Test and validate the full workflow.
- Complete academic documentation.
- Prepare the presentation, demonstration video and poster.

The functioning application and validated sporting analysis take priority over additional AI features.

## 18. Deployment approach

### Local full version

- Runs against the processed database on the development computer.
- Supports complete analysis and the in-person demonstration.
- May access data that cannot be distributed publicly.

### Online demonstration version

- May be hosted through Streamlit Community Cloud or another suitable service.
- Uses compact player metrics and selected derived event data.
- Must not include the complete raw dataset in GitHub.
- Must comply with the provider's licensing and distribution restrictions.

Raw event data, temporary files, secrets and local database write-ahead files should be excluded from version control.

## 19. FMP alignment checklist

The finished project should demonstrate:

- [ ] A real Nottingham Forest recruitment need and intended user.
- [ ] A tailored analytical solution.
- [ ] A reproducible ETL and validation process.
- [ ] Transparent position and role requirements.
- [ ] Player search and filtering.
- [ ] Individual player profiles.
- [ ] Candidate comparison.
- [ ] Tactical interpretation within the club context.
- [ ] Evidence-backed recommendations.
- [ ] Documented data sources, sample sizes and limitations.
- [ ] A working tool suitable for the final demonstration.
- [ ] Applicable squad-planning, coaching and financial requirements.

## 20. Guidance for project support

Development support should combine practical implementation with structured learning. It should:

1. Help define and protect a manageable MVP.
2. Explain relevant football-analytics concepts.
3. Teach Streamlit and supporting Python tools incrementally.
4. Help organize a maintainable GitHub repository.
5. Encourage testing, documentation and reproducibility.
6. Challenge incorrect statistical or tactical assumptions.
7. Prioritize work according to FMP requirements and deadlines.
8. Distinguish essential features from optional extensions.
9. Avoid premature AI complexity.
10. Help make the application a credible sports-analytics portfolio project.

## 21. Deferred research idea: CultureLab

CultureLab is a separate long-term sports-psychology research idea. It should not be included in the initial ScoutAgent application or treated as an FMP requirement.

The responsible version would be a research-informed cultural-assessment support tool rather than a system that infers players' personalities from interviews or video.

Potential functions could include:

- A searchable sports-psychology research database.
- Tools for defining organizational culture and behavioral expectations.
- Research-informed structured interview frameworks.
- Evidence-quality assessments.
- Support for human-led qualitative evaluation.

The concept must recognize that:

- Public interviews cannot reliably establish personality traits.
- Edited footage is not a substitute for psychological assessment.
- AI-generated personality predictions may be inaccurate or biased.
- Psychological constructs require valid and reliable measurement.
- Cultural compatibility is context-dependent.
- Privacy, discrimination and regulatory risks are significant.

## 22. Open decisions

- Confirm the final interpretation of every scouting-route requirement with the supervisor.
- Define the specific Nottingham Forest recruitment problem that will anchor the final workflow.
- Decide which first position or tactical role will be used for candidate search and comparison.
- Confirm which data may be stored in GitHub or deployed publicly.
- Define the comparison populations, minimum-minutes rules and metric methodology.
- Decide the minimum financial functionality required for the final submission.
- Decide which advanced features belong in the final product and which should remain future work.

The immediate priority is a transparent, functional football scouting application supported by a reliable analytical foundation. AI assistance and CultureLab should remain deferred until that foundation is complete.
