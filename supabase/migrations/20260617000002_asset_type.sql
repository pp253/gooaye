-- 為 stocks / mentions 加上資產類型，用來區分「可交易個股/ETF」與「題材、指數、商品」
-- 個股 | ETF | 題材 | 指數 | 商品

alter table stocks   add column if not exists asset_type text not null default '個股';
alter table mentions add column if not exists asset_type text not null default '個股';

create index if not exists stocks_asset_type_idx on stocks (asset_type);
