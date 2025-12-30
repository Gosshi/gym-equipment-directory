-- Migration: Unify category (single) to categories (array)
-- Date: 2025-12-30
-- 
-- This migration consolidates the legacy `category` column (single string) 
-- into the `categories` column (array of strings) for both gyms and gym_candidates.
--
-- IMPORTANT: Run this script within a transaction to ensure atomicity.
-- If any step fails, the entire migration will be rolled back.

BEGIN;

-- ============================================================================
-- STEP 1: Add categories column to gym_candidates if not exists
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'gym_candidates' AND column_name = 'categories'
    ) THEN
        ALTER TABLE gym_candidates ADD COLUMN categories TEXT[];
        RAISE NOTICE 'Added categories column to gym_candidates';
    ELSE
        RAISE NOTICE 'categories column already exists in gym_candidates';
    END IF;
END$$;

-- ============================================================================
-- STEP 2: Migrate data from category to categories for gyms
-- Only update rows where categories is NULL or empty AND category has value
-- This preserves existing categories data (intentional - avoid overwriting)
-- ============================================================================
UPDATE gyms 
SET categories = ARRAY[category] 
WHERE category IS NOT NULL 
  AND category != ''
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

DO $$ 
BEGIN 
    RAISE NOTICE 'Gyms: migrated category to categories for % rows', 
        (SELECT COUNT(*) FROM gyms WHERE categories IS NOT NULL AND array_length(categories, 1) > 0);
END $$;

-- ============================================================================
-- STEP 3: Migrate data from category to categories for gym_candidates
-- Same logic as above: only update if categories is empty
-- ============================================================================
UPDATE gym_candidates 
SET categories = ARRAY[category] 
WHERE category IS NOT NULL 
  AND category != ''
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

DO $$ 
BEGIN 
    RAISE NOTICE 'Gym candidates: migrated category to categories for % rows', 
        (SELECT COUNT(*) FROM gym_candidates WHERE categories IS NOT NULL AND array_length(categories, 1) > 0);
END $$;

-- ============================================================================
-- STEP 4: Extract categories from parsed_json for gyms (if not already set)
-- Priority: existing categories > parsed_json.categories > category
-- ============================================================================
UPDATE gyms
SET categories = (
    SELECT array_agg(elem::text)
    FROM jsonb_array_elements_text(parsed_json->'categories') AS elem
)
WHERE parsed_json ? 'categories' 
  AND jsonb_typeof(parsed_json->'categories') = 'array'
  AND jsonb_array_length(parsed_json->'categories') > 0
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

-- ============================================================================
-- STEP 5: Extract categories from parsed_json for gym_candidates
-- ============================================================================
UPDATE gym_candidates
SET categories = (
    SELECT array_agg(elem::text)
    FROM jsonb_array_elements_text(parsed_json->'categories') AS elem
)
WHERE parsed_json ? 'categories' 
  AND jsonb_typeof(parsed_json->'categories') = 'array'
  AND jsonb_array_length(parsed_json->'categories') > 0
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

-- ============================================================================
-- VERIFICATION: Check that no data will be lost before dropping columns
-- ============================================================================
DO $$
DECLARE
    gyms_with_category_only INT;
    candidates_with_category_only INT;
BEGIN
    -- Count rows where category exists but categories is still NULL
    SELECT COUNT(*) INTO gyms_with_category_only
    FROM gyms 
    WHERE category IS NOT NULL 
      AND category != ''
      AND (categories IS NULL OR array_length(categories, 1) IS NULL);
      
    SELECT COUNT(*) INTO candidates_with_category_only
    FROM gym_candidates 
    WHERE category IS NOT NULL 
      AND category != ''
      AND (categories IS NULL OR array_length(categories, 1) IS NULL);
    
    IF gyms_with_category_only > 0 THEN
        RAISE EXCEPTION 'VERIFICATION FAILED: % gyms still have category but no categories', gyms_with_category_only;
    END IF;
    
    IF candidates_with_category_only > 0 THEN
        RAISE EXCEPTION 'VERIFICATION FAILED: % gym_candidates still have category but no categories', candidates_with_category_only;
    END IF;
    
    RAISE NOTICE 'VERIFICATION PASSED: All category data has been migrated to categories';
END $$;

-- ============================================================================
-- STEP 6: Drop category column from gyms (safe after verification)
-- ============================================================================
ALTER TABLE gyms DROP COLUMN IF EXISTS category;
DO $$ BEGIN RAISE NOTICE 'Dropped category column from gyms'; END $$;

-- ============================================================================
-- STEP 7: Drop category column from gym_candidates (safe after verification)
-- ============================================================================
ALTER TABLE gym_candidates DROP COLUMN IF EXISTS category;
DO $$ BEGIN RAISE NOTICE 'Dropped category column from gym_candidates'; END $$;

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================
DO $$
DECLARE
    gyms_with_categories INT;
    candidates_with_categories INT;
BEGIN
    SELECT COUNT(*) INTO gyms_with_categories
    FROM gyms WHERE categories IS NOT NULL AND array_length(categories, 1) > 0;
    
    SELECT COUNT(*) INTO candidates_with_categories
    FROM gym_candidates WHERE categories IS NOT NULL AND array_length(categories, 1) > 0;
    
    RAISE NOTICE '=== Migration Complete ===';
    RAISE NOTICE 'Gyms with categories: %', gyms_with_categories;
    RAISE NOTICE 'Gym candidates with categories: %', candidates_with_categories;
END $$;

COMMIT;
