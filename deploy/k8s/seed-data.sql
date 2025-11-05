-- Limpiar datos existentes
DELETE FROM items;
DELETE FROM books;

-- Insertar en Catalogo
INSERT INTO books (sku, title, author, description, category, price, currency, active, stock, created_at, updated_at) VALUES
('BOOK-001', 'Clean Code', 'Robert C. Martin', 'A Handbook of Agile Software Craftsmanship', 'technology', 3299, 'USD', true, 10, NOW(), NOW()),
('BOOK-002', 'The Pragmatic Programmer', 'David Thomas, Andrew Hunt', 'Your Journey To Mastery', 'technology', 3499, 'USD', true, 10, NOW(), NOW()),
('BOOK-003', 'Design Patterns', 'Erich Gamma', 'Elements of Reusable Object-Oriented Software', 'technology', 4299, 'USD', true, 10, NOW(), NOW()),
('BOOK-004', 'Refactoring', 'Martin Fowler', 'Improving the Design of Existing Code', 'technology', 3799, 'USD', true, 10, NOW(), NOW()),
('BOOK-005', 'Introduction to Algorithms', 'Thomas H. Cormen', 'Third Edition', 'technology', 8999, 'USD', true, 10, NOW(), NOW());

-- Insertar en Inventario (mismo SKU, stock de 10)
INSERT INTO items (item_id, name, category, quantity, price, created_at, updated_at) VALUES
('BOOK-001', 'Clean Code', 'technology', 10, 32.99, NOW(), NOW()),
('BOOK-002', 'The Pragmatic Programmer', 'technology', 10, 34.99, NOW(), NOW()),
('BOOK-003', 'Design Patterns', 'technology', 10, 42.99, NOW(), NOW()),
('BOOK-004', 'Refactoring', 'technology', 10, 37.99, NOW(), NOW()),
('BOOK-005', 'Introduction to Algorithms', 'technology', 10, 89.99, NOW(), NOW());

-- Verificar
SELECT '=== CATALOGO ===' as info;
SELECT sku, title, price/100.0 as price_usd FROM books ORDER BY sku;

SELECT '=== INVENTARIO ===' as info;
SELECT item_id as sku, name as title, quantity, price as price_usd FROM items ORDER BY item_id;

