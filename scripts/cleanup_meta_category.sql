-- Cleanup: Remove meta.category from parsed_json (keep meta.categories only)
-- Date: 2025-12-30
-- 
-- This script removes the legacy `meta.category` field from parsed_json,
-- keeping only `meta.categories` (array) and root-level `categories` for consistency.

BEGIN;

-- Show current state
DO $$
DECLARE
    gyms_with_meta_category INT;
    candidates_with_meta_category INT;
BEGIN
    SELECT COUNT(*) INTO gyms_with_meta_category
    FROM gyms 
    WHERE parsed_json->'meta'->>'category' IS NOT NULL;
    
    SELECT COUNT(*) INTO candidates_with_meta_category
    FROM gym_candidates 
    WHERE parsed_json->'meta'->>'category' IS NOT NULL;
    
    RAISE NOTICE 'Gyms with meta.category: %', gyms_with_meta_category;
    RAISE NOTICE 'Gym candidates with meta.category: %', candidates_with_meta_category;
END $$;

-- Remove meta.category from gyms parsed_json
UPDATE gyms
SET parsed_json = parsed_json #- '{meta,category}'
WHERE parsed_json->'meta'->>'category' IS NOT NULL;

-- Remove meta.category from gym_candidates parsed_json
UPDATE gym_candidates
SET parsed_json = parsed_json #- '{meta,category}'
WHERE parsed_json->'meta'->>'category' IS NOT NULL;

-- Verify cleanup
DO $$
DECLARE
    remaining_gyms INT;
    remaining_candidates INT;
BEGIN
    SELECT COUNT(*) INTO remaining_gyms
    FROM gyms 
    WHERE parsed_json->'meta'->>'category' IS NOT NULL;
    
    SELECT COUNT(*) INTO remaining_candidates
    FROM gym_candidates 
    WHERE parsed_json->'meta'->>'category' IS NOT NULL;
    
    IF remaining_gyms > 0 OR remaining_candidates > 0 THEN
        RAISE EXCEPTION 'Cleanup failed: still have gyms=% candidates=% with meta.category', remaining_gyms, remaining_candidates;
    END IF;
    
    RAISE NOTICE 'Cleanup complete: meta.category removed from all records';
END $$;

COMMIT;
