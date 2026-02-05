-- Opening (ECO code) performance statistics
select
    eco,
    count(*) as total_games,
    sum(case when winner = 'white' then 1 else 0 end) as white_wins,
    sum(case when winner = 'black' then 1 else 0 end) as black_wins,
    sum(case when winner = 'draw' then 1 else 0 end) as draws,

    round(sum(case when winner = 'white' then 1 else 0 end) * 100.0 / count(*), 1) as white_win_rate,
    round(sum(case when winner = 'black' then 1 else 0 end) * 100.0 / count(*), 1) as black_win_rate,
    round(sum(case when winner = 'draw' then 1 else 0 end) * 100.0 / count(*), 1) as draw_rate,

    round(avg(move_count), 1) as avg_moves

from {{ ref('stg_games') }}
where eco is not null
group by eco
order by total_games desc
