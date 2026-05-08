-- Migration 002: Convert opcol_quantity from VARCHAR/TEXT to INTEGER
-- 
-- Rationale: Quantity is always numeric but was stored as TEXT requiring
-- conversions everywhere. Pydantic already validates as int.

-- PostgreSQL: use USING clause to cast existing values
ALTER TABLE onepiecetcg.opcollection
ALTER COLUMN opcol_quantity TYPE INTEGER
USING opcol_quantity::integer;

-- Add CHECK constraint to ensure non-negative values
ALTER TABLE onepiecetcg.opcollection
ADD CONSTRAINT chk_opcol_quantity_nonnegative
CHECK (opcol_quantity >= 0);
