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
    g.white_display as white_player,
    g.black_display as black_player,

    -- result
    r.result,
    case
        when r.result = '1-0' then g.white_display
        when r.result = '0-1' then g.black_display
        else 'Draw'
    end as winner,

    -- derived
    length(g.moves) - length(replace(g.moves, ' ', '')) + 1 as move_count

from {{ source('chessprompter', 'fact_games') }} g
left join {{ source('chessprompter', 'dim_date') }} d on g.date_id = d.date_id
left join {{ source('chessprompter', 'dim_event') }} e on g.event_id = e.event_id
left join {{ source('chessprompter', 'dim_result') }} r on g.result_id = r.result_id
