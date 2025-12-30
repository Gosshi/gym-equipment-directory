-- Migration: Normalize parsed_json pool data structure
-- Date: 2025-12-30
-- 
-- This migration moves pool-related fields from meta directly to a pool object
-- to follow the parsed_json spec. Fields affected:
-- - meta.lanes -> pool.lanes
-- - meta.length_m -> pool.length_m
-- - meta.heated -> pool.heated
--
-- NOTE: lanes = 0 or length_m = 0 is treated as NULL (couldn't scrape, not actual 0)

BEGIN;

-- Show current state
DO $$
DECLARE
    gyms_with_meta_lanes INT;
    candidates_with_meta_lanes INT;
BEGIN
    SELECT COUNT(*) INTO gyms_with_meta_lanes
    FROM gyms 
    WHERE parsed_json->'meta'->>'lanes' IS NOT NULL
      AND parsed_json->'pool' IS NULL;
    
    SELECT COUNT(*) INTO candidates_with_meta_lanes
    FROM gym_candidates 
    WHERE parsed_json->'meta'->>'lanes' IS NOT NULL
      AND parsed_json->'pool' IS NULL;
    
    RAISE NOTICE 'Gyms with meta.lanes but no pool object: %', gyms_with_meta_lanes;
    RAISE NOTICE 'Gym candidates with meta.lanes but no pool object: %', candidates_with_meta_lanes;
END $$;

-- Step 1: Create pool object from meta fields for gyms
-- Use NULL for lanes/length_m if value is 0 or missing (0 is not realistic for pools)
UPDATE gyms
SET parsed_json = jsonb_set(
    parsed_json,
    '{pool}',
    jsonb_build_object(
        'lanes', CASE 
            WHEN (parsed_json->'meta'->>'lanes')::int > 0 
            THEN (parsed_json->'meta'->>'lanes')::int 
            ELSE NULL 
        END,
        'length_m', CASE 
            WHEN (parsed_json->'meta'->>'length_m')::int > 0 
            THEN (parsed_json->'meta'->>'length_m')::int 
            ELSE NULL 
        END,
        'heated', (parsed_json->'meta'->>'heated')::boolean
    )
)
WHERE parsed_json->'meta'->>'lanes' IS NOT NULL
  AND parsed_json->'pool' IS NULL;

-- Step 2: Create pool object from meta fields for gym_candidates
UPDATE gym_candidates
SET parsed_json = jsonb_set(
    parsed_json,
    '{pool}',
    jsonb_build_object(
        'lanes', CASE 
            WHEN (parsed_json->'meta'->>'lanes')::int > 0 
            THEN (parsed_json->'meta'->>'lanes')::int 
            ELSE NULL 
        END,
        'length_m', CASE 
            WHEN (parsed_json->'meta'->>'length_m')::int > 0 
            THEN (parsed_json->'meta'->>'length_m')::int 
            ELSE NULL 
        END,
        'heated', (parsed_json->'meta'->>'heated')::boolean
    )
)
WHERE parsed_json->'meta'->>'lanes' IS NOT NULL
  AND parsed_json->'pool' IS NULL;

-- Step 3: Remove lanes, length_m, heated from meta for gyms
UPDATE gyms
SET parsed_json = parsed_json #- '{meta,lanes}' #- '{meta,length_m}' #- '{meta,heated}'
WHERE parsed_json->'pool' IS NOT NULL
  AND (parsed_json->'meta'->>'lanes' IS NOT NULL 
       OR parsed_json->'meta'->>'length_m' IS NOT NULL
       OR parsed_json->'meta'->>'heated' IS NOT NULL);

-- Step 4: Remove lanes, length_m, heated from meta for gym_candidates
UPDATE gym_candidates
SET parsed_json = parsed_json #- '{meta,lanes}' #- '{meta,length_m}' #- '{meta,heated}'
WHERE parsed_json->'pool' IS NOT NULL
  AND (parsed_json->'meta'->>'lanes' IS NOT NULL 
       OR parsed_json->'meta'->>'length_m' IS NOT NULL
       OR parsed_json->'meta'->>'heated' IS NOT NULL);

-- Step 5: Fix any existing pool objects with lanes = 0 to NULL
UPDATE gyms
SET parsed_json = jsonb_set(parsed_json, '{pool,lanes}', 'null'::jsonb)
WHERE parsed_json->'pool'->>'lanes' = '0';

UPDATE gym_candidates
SET parsed_json = jsonb_set(parsed_json, '{pool,lanes}', 'null'::jsonb)
WHERE parsed_json->'pool'->>'lanes' = '0';

-- Verify
DO $$
DECLARE
    remaining_gyms INT;
    remaining_candidates INT;
BEGIN
    SELECT COUNT(*) INTO remaining_gyms
    FROM gyms 
    WHERE parsed_json->'meta'->>'lanes' IS NOT NULL;
    
    SELECT COUNT(*) INTO remaining_candidates
    FROM gym_candidates 
    WHERE parsed_json->'meta'->>'lanes' IS NOT NULL;
    
    IF remaining_gyms > 0 OR remaining_candidates > 0 THEN
        RAISE WARNING 'Some records still have meta.lanes: gyms=% candidates=%', remaining_gyms, remaining_candidates;
    END IF;
    
    RAISE NOTICE 'Migration complete: pool fields moved from meta to pool object';
END $$;

-- Show final state
DO $$
DECLARE
    gyms_with_pool_obj INT;
BEGIN
    SELECT COUNT(*) INTO gyms_with_pool_obj
    FROM gyms 
    WHERE parsed_json->'pool' IS NOT NULL;
    
    RAISE NOTICE 'Gyms with pool object: %', gyms_with_pool_obj;
END $$;

COMMIT;
