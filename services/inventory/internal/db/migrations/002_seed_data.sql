-- Seed data for inventory matching catalog
-- This should match the books in the catalog service

-- First, clear existing data
TRUNCATE items CASCADE;

-- Insert inventory items matching catalog books
INSERT INTO items (item_id, name, category, quantity, price, reserved_quantity)
VALUES 
    ('BOOK-001', 'The Go Programming Language', 'programming', 50, 49.99, 0),
    ('BOOK-002', 'Clean Code', 'programming', 30, 39.99, 0),
    ('BOOK-003', 'Design Patterns', 'programming', 25, 54.99, 0),
    ('BOOK-004', 'The Pragmatic Programmer', 'programming', 40, 42.99, 0),
    ('BOOK-005', 'Microservices Patterns', 'architecture', 15, 47.99, 0),
    ('BOOK-006', 'Domain-Driven Design', 'architecture', 20, 59.99, 0),
    ('BOOK-007', 'Building Microservices', 'architecture', 35, 44.99, 0),
    ('BOOK-008', 'Site Reliability Engineering', 'devops', 28, 52.99, 0),
    ('BOOK-009', 'The Phoenix Project', 'devops', 45, 34.99, 0),
    ('BOOK-010', 'Kubernetes in Action', 'devops', 32, 49.99, 0)
ON CONFLICT (item_id) DO UPDATE SET
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    quantity = EXCLUDED.quantity,
    price = EXCLUDED.price;
