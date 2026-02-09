# dbt for chessprompter — Guided Setup

## Why Python First, Then dbt

dbt only does the **T** (Transform) in ELT. It cannot read files, parse data, or insert rows — it assumes data is **already in a database**. It runs SELECT statements against existing tables, nothing more.

For chessprompter, that means:

| Responsibility | Tool | What it does |
|---|---|---|
| Read `.pgn` files from disk | Python | `chess.pgn.read_game()` |
| Parse chess notation + metadata | Python | Extract players, dates, ECO codes, moves |
| Create star schema tables | Python | DDL: `CREATE TABLE fact_games ...` |
| Insert raw data into DuckDB | Python | `INSERT INTO fact_games VALUES (...)` |
| Transform raw → derived tables | **dbt** | `SELECT ... FROM fact_games JOIN ...` |
| Test data quality | **dbt** | `unique`, `not_null`, `accepted_values` |

**Pipeline order**: Python (PGN files → parse → DuckDB star schema) → dbt (star schema → derived views/tables)

The boundary between the two is `sources.yml` — it tells dbt "these tables already exist, I didn't create them, but I want to build on top of them." Everything above `sources.yml` is Python's job. Everything below it is dbt's.

dbt *could* come first if your raw data were already in a database (e.g., a Postgres replica of a production system). In our case it's not — it's `.pgn` files on disk — so Python must run first.

## What dbt Actually Is

dbt is **not** a query tool — it's a **dependency-aware SQL compiler**. It takes SELECT statements, wraps them in `CREATE VIEW AS ...` or `CREATE TABLE AS ...`, and runs them in the right order.

The problem it solves: when you have 20+ SQL transformations that depend on each other, dbt manages the DAG (run order), `ref()` links, and materializations so you don't have to.

For chessprompter specifically: dbt sits *on top of* the existing DuckDB, reads the star schema tables as "sources", and creates new derived tables (views/tables) inside the same database.

## Step 1: Delete existing dbt files

```bash
rm -rf chessprompter_dbt/
```

Start fresh so each file is understood as it's created.

## Step 2: Scaffold from scratch

### `profiles.yml` — Database connection

```yaml
chessprompter_dbt:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ~/.chessprompter/games.duckdb
```

This tells dbt *where your database is*. dbt doesn't create a database; it connects to one. Think of it like a database connection string.

- `chessprompter_dbt` — profile name (must match `profile:` in `dbt_project.yml`)
- `target: dev` — which output to use (you could have `dev`, `prod`, etc.)
- `type: duckdb` — the adapter
- `path` — where the DuckDB file lives; dbt reads existing tables from here *and* writes its models into the same database

We keep this in the project directory (not `~/.dbt/`) so the config is version-controlled and portable.

### `dbt_project.yml` — Project manifest

```yaml
name: chessprompter_dbt
version: "1.0.0"

profile: chessprompter_dbt

model-paths: ["models"]

models:
  chessprompter_dbt:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

- `name` / `profile` — links this project to the profile in `profiles.yml`
- `model-paths` — where dbt looks for `.sql` files (each file = one model = one table or view)
- `staging → +materialized: view` — anything in `models/staging/` becomes a VIEW (cheap, always fresh, just a saved query)
- `marts → +materialized: table` — anything in `models/marts/` becomes a TABLE (physically stored, faster to query, needs rebuilding when source data changes)

**Key concept**: dbt models are just SELECT statements. dbt wraps them in `CREATE VIEW AS ...` or `CREATE TABLE AS ...` depending on materialization. You never write DDL yourself.

### `.gitignore`

```
target/
dbt_packages/
logs/
```

- `target/` — compiled SQL and run artifacts (generated on every run)
- `dbt_packages/` — third-party dbt packages
- `logs/` — run logs

### Verify the connection

```bash
uv run dbt debug --profiles-dir .
```

Should output `All checks passed!`.

## Step 3: Define sources

Sources tell dbt: "these tables already exist in my database — I didn't create them with dbt, but I want to reference them in my models."

### `models/staging/sources.yml`

```yaml
version: 2

sources:
  - name: chessprompter
    schema: main
    description: Raw star schema tables created by the chessprompter Python CLI
    tables:
      - name: fact_games
        description: Central fact table — one row per chess game
      - name: dim_player
        description: Player dimension — unique players
      - name: dim_date
        description: Date dimension — game dates
      - name: dim_event
        description: Event dimension — tournament/match info
      - name: dim_result
        description: Result dimension — game outcomes (1-0, 0-1, 1/2-1/2)
      - name: game_players
        description: Junction table for consultation games with multiple players per side
```

- `name: chessprompter` — a namespace. In SQL models you reference these as `{{ source('chessprompter', 'fact_games') }}`
- `schema: main` — DuckDB's default schema. Without this, dbt assumes the source name (`chessprompter`) is the schema, which fails
- **Why not just write `FROM fact_games` directly?** Because `source()` registers the dependency in dbt's DAG and lets dbt apply freshness checks, documentation, and tests to external tables

## Step 4: Build the first staging model

A staging model denormalizes the star schema into a single wide table. Downstream models (marts) reference this instead of joining 5 tables every time.

### `models/staging/stg_games.sql`

```sql
-- stg_games: Denormalized view of the star schema.
-- Joins fact_games with all dimension tables so downstream
-- models can just SELECT from this single clean table.

select
    g.game_id,
    g.eco,
    g.moves,
    g.is_consultation,

    -- date fields
    d.date,
    d.year,
    d.month,

    -- event fields
    e.name as event_name,
    e.site as event_site,
    e.round as event_round,

    -- player fields
    pw.display_name as white_player,
    pb.display_name as black_player,

    -- result
    r.result,
    case
        when r.result = '1-0' then pw.display_name
        when r.result = '0-1' then pb.display_name
        else 'Draw'
    end as winner,

    -- derived
    length(g.moves) - length(replace(g.moves, ' ', '')) + 1 as move_count

from {{ source('chessprompter', 'fact_games') }} g
left join {{ source('chessprompter', 'dim_date') }} d on g.date_id = d.date_id
left join {{ source('chessprompter', 'dim_event') }} e on g.event_id = e.event_id
left join {{ source('chessprompter', 'dim_player') }} pw on g.playing_white_id = pw.player_id
left join {{ source('chessprompter', 'dim_player') }} pb on g.playing_black_id = pb.player_id
left join {{ source('chessprompter', 'dim_result') }} r on g.result_id = r.result_id
```

Key concepts:

1. **`{{ source('chessprompter', 'fact_games') }}`** — Jinja templating. dbt compiles this to the actual table reference (`main.fact_games`). It also tells dbt "this model depends on the `fact_games` source" — that's a DAG edge.

2. **The file IS the model.** The filename `stg_games.sql` means dbt will create a view/table called `stg_games`. You never write `CREATE VIEW` — dbt does the wrapping based on materialization config.

### Run it

```bash
uv run dbt run --profiles-dir .
```

Output: `1 of 1 OK created sql view model main.stg_games`

dbt took the SELECT statement, wrapped it in `CREATE VIEW main.stg_games AS (...)`, and ran it against DuckDB.

## Step 5: Add tests

### `models/staging/schema.yml`

```yaml
version: 2

models:
  - name: stg_games
    description: Denormalized game data — one row per game with all dimensions joined
    columns:
      - name: game_id
        description: Primary key
        data_tests:
          - unique
          - not_null
      - name: result
        data_tests:
          - accepted_values:
              arguments:
                values: ['1-0', '0-1', '1/2-1/2']
```

What the tests do under the hood:

- `unique` — runs `SELECT game_id, count(*) FROM stg_games GROUP BY 1 HAVING count(*) > 1` and fails if any rows return
- `not_null` — runs `SELECT * FROM stg_games WHERE game_id IS NULL` and fails if any rows return
- `accepted_values` — checks that `result` only contains the listed values

**This is where dbt's value clicks**: SQL transformations + data quality tests + documentation in one workflow. Without dbt, you'd write these checks as separate scripts.

```bash
uv run dbt test --profiles-dir .
```

### `dbt run` vs `dbt test` vs `dbt build`

| Command | What it does |
|---------|-------------|
| `dbt run` | Materializes models (creates views/tables) |
| `dbt test` | Runs data tests against already-materialized models |
| `dbt build` | Both, in the right order: run model → test it → run next model → test it |

## Step 6: Build the marts

Marts are "business-facing" models — aggregated, ready-to-query tables. They reference `stg_games` via `{{ ref() }}`.

**`{{ ref('stg_games') }}`** means: "I depend on the `stg_games` model. Build it before me." This creates an edge in the DAG. dbt figures out execution order automatically.

### `models/marts/player_stats.sql`

```sql
-- player_stats: Aggregated win/loss/draw statistics per player.
-- Uses ref('stg_games') — dbt knows to build stg_games first.

with white_games as (
    select
        white_player as player,
        count(*) as games_as_white,
        count(*) filter (where result = '1-0') as wins_as_white,
        count(*) filter (where result = '0-1') as losses_as_white,
        count(*) filter (where result = '1/2-1/2') as draws_as_white
    from {{ ref('stg_games') }}
    group by white_player
),

black_games as (
    select
        black_player as player,
        count(*) as games_as_black,
        count(*) filter (where result = '0-1') as wins_as_black,
        count(*) filter (where result = '1-0') as losses_as_black,
        count(*) filter (where result = '1/2-1/2') as draws_as_black
    from {{ ref('stg_games') }}
    group by black_player
)

select
    coalesce(w.player, b.player) as player,
    coalesce(w.games_as_white, 0) as games_as_white,
    coalesce(b.games_as_black, 0) as games_as_black,
    coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0) as total_games,
    coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0) as total_wins,
    coalesce(w.losses_as_white, 0) + coalesce(b.losses_as_black, 0) as total_losses,
    coalesce(w.draws_as_white, 0) + coalesce(b.draws_as_black, 0) as total_draws,
    round(
        (coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0))::float
        / nullif(coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0), 0)
        * 100, 1
    ) as win_rate
from white_games w
full outer join black_games b on w.player = b.player
order by total_games desc
```

### `models/marts/opening_stats.sql`

```sql
-- opening_stats: Performance statistics grouped by ECO opening code.

select
    eco,
    count(*) as total_games,
    count(*) filter (where result = '1-0') as white_wins,
    count(*) filter (where result = '0-1') as black_wins,
    count(*) filter (where result = '1/2-1/2') as draws,
    round(count(*) filter (where result = '1-0')::float / count(*) * 100, 1) as white_win_pct,
    round(count(*) filter (where result = '0-1')::float / count(*) * 100, 1) as black_win_pct,
    round(avg(move_count), 1) as avg_moves
from {{ ref('stg_games') }}
where eco is not null
group by eco
order by total_games desc
```

### `models/marts/schema.yml`

```yaml
version: 2

models:
  - name: player_stats
    description: Win/loss/draw statistics aggregated per player
    columns:
      - name: player
        description: Player display name
        data_tests:
          - unique
          - not_null

  - name: opening_stats
    description: Game statistics aggregated by ECO opening code
    columns:
      - name: eco
        description: ECO opening code
        data_tests:
          - unique
          - not_null
```

## Step 7: Run `dbt build` — the DAG in action

```bash
uv run dbt build --profiles-dir .
```

Output:

```
 1 of 10 OK created sql view model main.stg_games
 2 of 10 PASS accepted_values_stg_games_result__1_0__0_1__1_2_1_2
 3 of 10 PASS not_null_stg_games_game_id
 4 of 10 PASS unique_stg_games_game_id
 5 of 10 OK created sql table model main.opening_stats
 6 of 10 OK created sql table model main.player_stats
 7 of 10 PASS not_null_opening_stats_eco
 8 of 10 PASS unique_opening_stats_eco
 9 of 10 PASS not_null_player_stats_player
10 of 10 PASS unique_player_stats_player

Done. PASS=10 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=10
```

dbt figured out the execution order from `ref()` calls alone:

1. `stg_games` (view) — built first because the marts depend on it
2. Tests on `stg_games` — run immediately after to catch problems early
3. `opening_stats` + `player_stats` (tables) — built after staging passes
4. Tests on both marts — run after materialization

If you had 50 models with complex interdependencies, it would still sort them correctly. That's the DAG.

**The "aha" moment**: modify `stg_games.sql` → re-run `dbt build` → downstream marts auto-rebuild in the right order. Without dbt, you'd track these dependencies yourself.

## Final project structure

```
chessprompter_dbt/
├── profiles.yml              # DB connection (points at games.duckdb)
├── dbt_project.yml           # Project config (staging=view, marts=table)
├── .gitignore                # Exclude build artifacts
└── models/
    ├── staging/
    │   ├── sources.yml       # "These tables already exist" (star schema)
    │   ├── stg_games.sql     # Denormalized join of fact + dimensions
    │   └── schema.yml        # Tests on stg_games
    └── marts/
        ├── player_stats.sql  # Win/loss/draw per player
        ├── opening_stats.sql # Stats by ECO opening code
        └── schema.yml        # Tests on marts
```

## Key concepts

| Concept | What it does | Why it matters |
|---------|-------------|----------------|
| `source()` | References tables dbt didn't create | Boundary between your Python pipeline and dbt |
| `ref()` | References another dbt model | Creates DAG edges — dbt auto-sorts execution order |
| `dbt build` | Run + test in DAG order | One command rebuilds everything in the right sequence |
| Materialization | `view` vs `table` | Views are cheap/fresh; tables are fast to query |
| YAML tests | `unique`, `not_null`, `accepted_values` | Data quality checks without writing test scripts |

## Commands

All from the `chessprompter_dbt/` directory:

```bash
uv run dbt build --profiles-dir .      # Build + test everything
uv run dbt run --profiles-dir .        # Just materialize models
uv run dbt test --profiles-dir .       # Just run tests
uv run dbt compile --profiles-dir .    # Compile Jinja → SQL without running (inspect target/compiled/)
uv run dbt debug --profiles-dir .      # Verify connection and config
```
