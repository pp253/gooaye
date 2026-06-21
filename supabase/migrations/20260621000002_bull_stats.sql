-- 每檔個股「看多訊號」的命中統計（持有 60 天）
alter table stock_performance add column if not exists bull_n          integer;
alter table stock_performance add column if not exists bull_win_rate   numeric(8,4);  -- 0~1
alter table stock_performance add column if not exists bull_avg_return numeric(8,4);  -- 小數
