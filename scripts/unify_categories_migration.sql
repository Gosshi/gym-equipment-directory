-- Migration: Unify category (single) to categories (array)
-- Date: 2024-12-30

-- Step 1: Add categories column to gym_candidates if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'gym_candidates' AND column_name = 'categories') THEN
        ALTER TABLE gym_candidates ADD COLUMN categories TEXT[];
    END IF;
END$$;

-- Step 2: Migrate data - copy category to categories array for gyms
UPDATE gyms 
SET categories = ARRAY[category] 
WHERE category IS NOT NULL 
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

-- Step 3: Migrate data - copy category to categories array for gym_candidates  
UPDATE gym_candidates 
SET categories = ARRAY[category] 
WHERE category IS NOT NULL 
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

-- Step 4: Also get categories from parsed_json if available
UPDATE gyms
SET categories = (
    SELECT array_agg(elem::text)
    FROM jsonb_array_elements_text(parsed_json->'categories') AS elem
)
WHERE parsed_json ? 'categories' 
  AND jsonb_typeof(parsed_json->'categories') = 'array'
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

UPDATE gym_candidates
SET categories = (
    SELECT array_agg(elem::text)
    FROM jsonb_array_elements_text(parsed_json->'categories') AS elem
)
WHERE parsed_json ? 'categories' 
  AND jsonb_typeof(parsed_json->'categories') = 'array'
  AND (categories IS NULL OR array_length(categories, 1) IS NULL);

-- Step 5: Drop category column from gyms
ALTER TABLE gyms DROP COLUMN IF EXISTS category;

-- Step 6: Drop category column from gym_candidates
ALTER TABLE gym_candidates DROP COLUMN IF EXISTS category;
