.open pokemon_cards.db
.tables
vacuum

drop table if exists api_calls;
drop table if exists api_calls_2;
drop table if exists cards2;

create table api_calls (
    id integer primary key autoincrement, 
    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    request text, 
    status text,
    response text
);

delete from sets;
select count(*) from sets;
create table sets (
    id integer primary key autoincrement,
    code text,
    name text,
    printedTotal integer,
    total integer,
    updatedAt datetime,
    json text
);

select * from cards2 limit 1;
select * from cards limit 10;
create table cards2 as select * from cards;   
drop table cards;

insert into cards (set_code, code, name, card_number, artist, flavorText, supertype, updatedAt, json)
select set_code, code, name, card_number, artist, flavorText, supertype, updatedAt, json from cards2;

create table cards (
    id integer primary key autoincrement,
	set_code text,
	code text,
    updatedAt datetime,
	card_number text,	
    name text,
    artist text,
	flavorText text,
	supertype text,
    rarity text,
    averageSellPrice text,
    artStyle text,
    trendPrice text,
    json text
);
alter table cards rename column recentSalePrice to trendPrice;

update cards 
set rarity=json_extract(json, '$.rarity'),
    averageSellPrice=json_extract(json, '$.cardmarket.prices.averageSellPrice'),
    trendPrice=json_extract(json, '$.cardmarket.prices.trendPrice'),
    updatedAt=json_extract(json, '$.cardmarket.updatedAt')

select c.code
,json_extract(c.json, '$.rarity') as rarity
,json_extract(c.json, '$.cardmarket.prices.averageSellPrice') as averageSellPrice
,json_extract(c.json, '$.cardmarket.prices.trendPrice') as trendPrice
,json_extract(c.json, '$.cardmarket.updatedAt') as updatedAt
,c.json
from cards c, json_each(c.json)
limit 10;


select * from cards limit 10;





alter table api_calls drop column data_json;
alter table api_calls add column request_time DATETIME DEFAULT CURRENT_TIMESTAMP

select a.id, a.request, a.status,
json_extract(a.response, '$.data.name') , json_extract(a.response, '$.data.supertype')
-- api_calls.*
from api_calls a,
json_each(a.response) 
where 
json_extract(a.response, '$.data.name') like '%venusa%'

select id, set_code, code, name, card_number,	artist, flavorText, supertype, updatedAt
from cards;


select count(1) from sets;
select count(1) from cards;
select * from api_calls order by 1 desc limit 1;
select * from cards order by 1 desc limit 1;


api_calls

select 
code,

json_extract(cards.json, '$.images.small') as small,
json_extract(cards.json, '$.images.large') as large
from cards, json_each(cards.json)
where code='base2-26'
limit 1

select count(1) from cards;
select count(distinct(code)) from cards;
select code from cards limit 100;
code
from cards


where


delete from cards where id in (
    select id from (
        select id,code,name,row_number() over(partition by code order by id) as n
        from cards 
        where code in (
            select code from cards
            group by code
            having count(1) > 1
        )
    )
    where n > 1
)


select count(1) as number_of_sets from sets;
select count(1) as number_of_cards from cards;
select set_code, count(1) as number_of_cards from cards group by set_code;

select id, code, name, printedTotal, total, updatedAt from sets;
select id, set_code, code, name, card_number,	artist, flavorText, supertype, updatedAt from cards limit 200;
select * from api_calls order by 1 desc limit 10;
delete from api_calls;

select * from cards limit 5;


select 
code,
set_code,
json_extract(cards.json, '$.images.small') as small,
json_extract(cards.json, '$.images.large') as large
from cards

select * from cards where code='base2-1'

select 
set_code, code, averageSellPrice
from cards 
where cast(averageSellPrice as decimal) > 5
order by cast(averageSellPrice as decimal) desc
limit 500;

select 
count(1)
from cards 
-- where cast(averageSellPrice as decimal) > 5
order by cast(averageSellPrice as decimal) desc
limit 500;

select set_code,code from cards 
where name like '%cufant%';

select set_code,code,name from cards 
where code like '%191%';

select set_code,code,name,replace(code,set_code || '-','') as card_number
from cards 
where set_code like '%swsh8%'
order by cast(card_number as decimal) asc;

select * from sets;

create table cards_bu as
select * from cards;

create table sets_bu as
select * from sets;

select * from cards_bu limit 5;
select * from sets_bu limit 5;


select response from api_calls order by request_time desc limit 1 ;
