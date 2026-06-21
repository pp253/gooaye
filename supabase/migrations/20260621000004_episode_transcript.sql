-- 把逐字稿存進 DB：在 episodes 加大欄位。
-- 注意：transcript 很大（平均 ~21k 字），列表頁查詢務必明列欄位排除它，
-- 只有單集詳情才 select 到 transcript（見 frontend EpisodeList vs EpisodeDetail）。

alter table episodes add column if not exists transcript       text;
alter table episodes add column if not exists transcript_chars integer;
alter table episodes add column if not exists site_desc        text;   -- 站方官方摘要（非我們 LLM 產的）
