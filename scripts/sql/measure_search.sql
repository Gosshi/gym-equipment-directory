-- 入力: :pref, :city, :per_page, :token などを psql \set で与える
-- 代表ケース: sort=score（現状は計算列→索引は freshness/richness 構成要素を狙う）
BEGIN;
SET LOCAL statement_timeout = '15s';

-- freshness キーセット相当
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT g.id, g.name, g.city, g.prefecture, g.last_verified_at_cached
FROM gyms g
WHERE g.prefecture = :pref AND g.city = :city
ORDER BY g.last_verified_at_cached DESC NULLS LAST, g.id DESC
LIMIT :per_page;

-- richness（設備数）用のサマリ join 例
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT g.id, cnt.c AS equip_count
FROM gyms g
LEFT JOIN (
  SELECT ge.gym_id, COUNT(*) AS c
  FROM gym_equipments ge
  GROUP BY ge.gym_id
) cnt ON cnt.gym_id = g.id
WHERE g.prefecture = :pref AND g.city = :city
ORDER BY cnt.c DESC NULLS LAST, g.id DESC
LIMIT :per_page;

ROLLBACK;
