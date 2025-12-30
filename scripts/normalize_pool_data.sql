-- Migration: Normalize parsed_json pool data structure
-- Date: 2025-12-30
-- 
-- This migration moves pool-related fields from meta directly to a pool object
-- to follow the parsed_json spec. Fields affected:
-- - meta.lanes -> pool.lanes
-- - meta.length_m -> pool.length_m
-- - meta.heated -> pool.heated

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
UPDATE gyms
SET parsed_json = jsonb_set(
    parsed_json,
    '{pool}',
    jsonb_build_object(
        'lanes', COALESCE((parsed_json->'meta'->>'lanes')::int, 0),
        'length_m', COALESCE((parsed_json->'meta'->>'length_m')::int, 0),
        'heated', COALESCE((parsed_json->'meta'->>'heated')::boolean, false)
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
        'lanes', COALESCE((parsed_json->'meta'->>'lanes')::int, 0),
        'length_m', COALESCE((parsed_json->'meta'->>'length_m')::int, 0),
        'heated', COALESCE((parsed_json->'meta'->>'heated')::boolean, false)
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
