-- Player performance statistics
with white_games as (
    select
        white_player_id as player_id,
        white_display_name as player_name,
        count(*) as games_as_white,
        sum(case when winner = 'white' then 1 else 0 end) as wins_as_white,
        sum(case when winner = 'black' then 1 else 0 end) as losses_as_white,
        sum(case when winner = 'draw' then 1 else 0 end) as draws_as_white
    from {{ ref('stg_games') }}
    group by 1, 2
),

black_games as (
    select
        black_player_id as player_id,
        black_display_name as player_name,
        count(*) as games_as_black,
        sum(case when winner = 'black' then 1 else 0 end) as wins_as_black,
        sum(case when winner = 'white' then 1 else 0 end) as losses_as_black,
        sum(case when winner = 'draw' then 1 else 0 end) as draws_as_black
    from {{ ref('stg_games') }}
    group by 1, 2
)

select
    coalesce(w.player_id, b.player_id) as player_id,
    coalesce(w.player_name, b.player_name) as player_name,

    coalesce(w.games_as_white, 0) as games_as_white,
    coalesce(b.games_as_black, 0) as games_as_black,
    coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0) as total_games,

    coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0) as wins,
    coalesce(w.losses_as_white, 0) + coalesce(b.losses_as_black, 0) as losses,
    coalesce(w.draws_as_white, 0) + coalesce(b.draws_as_black, 0) as draws,

    round(
        (coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0)) * 100.0
        / nullif(coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0), 0),
        1
    ) as win_rate

from white_games w
full outer join black_games b on w.player_id = b.player_id
order by total_games desc
