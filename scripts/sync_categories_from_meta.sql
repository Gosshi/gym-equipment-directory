-- Migration: Sync categories column with parsed_json.meta.categories
-- Date: 2025-12-30
--
-- Problem: Some gyms have categories in meta.categories but not in the categories column
-- This causes features (like pool info) to not display even when data exists

BEGIN;

-- Show current mismatches
DO $$
DECLARE
    mismatch_count INT;
BEGIN
    SELECT COUNT(*) INTO mismatch_count
    FROM gyms
    WHERE parsed_json->'meta'->'categories' IS NOT NULL
      AND NOT categories @> ARRAY(SELECT jsonb_array_elements_text(parsed_json->'meta'->'categories'));
    
    RAISE NOTICE 'Gyms with categories mismatch: %', mismatch_count;
END $$;

-- Sync categories from meta.categories
UPDATE gyms
SET categories = ARRAY(
    SELECT DISTINCT unnest(
        ARRAY(SELECT jsonb_array_elements_text(parsed_json->'meta'->'categories'))
        || categories
    )
)
WHERE parsed_json->'meta'->'categories' IS NOT NULL
  AND NOT categories @> ARRAY(SELECT jsonb_array_elements_text(parsed_json->'meta'->'categories'));

-- Verify
DO $$
DECLARE
    remaining_mismatches INT;
BEGIN
    SELECT COUNT(*) INTO remaining_mismatches
    FROM gyms
    WHERE parsed_json->'meta'->'categories' IS NOT NULL
      AND NOT categories @> ARRAY(SELECT jsonb_array_elements_text(parsed_json->'meta'->'categories'));
    
    IF remaining_mismatches > 0 THEN
        RAISE WARNING 'Some categories still not synced: %', remaining_mismatches;
    ELSE
        RAISE NOTICE 'All categories synced successfully';
    END IF;
END $$;

COMMIT;
