-- Denormalized view of all games with dimension attributes
select
    g.game_id,
    g.eco,
    g.moves,
    g.is_consultation,

    -- Date
    d.date,
    d.year,
    d.month,
    d.day,

    -- Event
    e.name as event_name,
    e.site as event_site,
    e.round,

    -- Result
    r.result,
    case r.result
        when '1-0' then 'white'
        when '0-1' then 'black'
        when '1/2-1/2' then 'draw'
        else 'unknown'
    end as winner,

    -- White player
    g.white as white_player_id,
    pw.name as white_name,
    pw.display_name as white_display_name,

    -- Black player
    g.black as black_player_id,
    pb.name as black_name,
    pb.display_name as black_display_name,

    -- Derived
    length(g.moves) - length(replace(g.moves, ' ', '')) + 1 as move_count

from {{ source('chessprompter', 'fact_games') }} g
left join {{ source('chessprompter', 'dim_date') }} d on g.date_id = d.date_id
left join {{ source('chessprompter', 'dim_event') }} e on g.event_id = e.event_id
left join {{ source('chessprompter', 'dim_result') }} r on g.result_id = r.result_id
left join {{ source('chessprompter', 'dim_player') }} pw on g.white = pw.player_id
left join {{ source('chessprompter', 'dim_player') }} pb on g.black = pb.player_id
