-- Sample seed data for development/testing
-- Run this manually if you want sample data

INSERT INTO books (sku, title, author, price, currency, category, description, active, stock)
VALUES 
    ('BOOK-001', 'The Go Programming Language', 'Alan A. A. Donovan, Brian W. Kernighan', 4999, 'USD', 'programming', 
     'A comprehensive guide to the Go programming language.', true, 0),
    
    ('BOOK-002', 'Clean Code', 'Robert C. Martin', 3999, 'USD', 'programming',
     'A handbook of agile software craftsmanship.', true, 0),
    
    ('BOOK-003', 'Design Patterns', 'Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides', 5499, 'USD', 'programming',
     'Elements of reusable object-oriented software.', true, 0),
    
    ('BOOK-004', 'The Pragmatic Programmer', 'David Thomas, Andrew Hunt', 4299, 'USD', 'programming',
     'Your journey to mastery, 20th Anniversary Edition.', true, 0),
    
    ('BOOK-005', 'Microservices Patterns', 'Chris Richardson', 4799, 'USD', 'architecture',
     'With examples in Java.', true, 0),
    
    ('BOOK-006', 'Domain-Driven Design', 'Eric Evans', 5999, 'USD', 'architecture',
     'Tackling Complexity in the Heart of Software.', true, 0),
    
    ('BOOK-007', 'Building Microservices', 'Sam Newman', 4499, 'USD', 'architecture',
     'Designing Fine-Grained Systems.', true, 0),
    
    ('BOOK-008', 'Site Reliability Engineering', 'Betsy Beyer, Chris Jones, Jennifer Petoff, Niall Richard Murphy', 5299, 'USD', 'devops',
     'How Google Runs Production Systems.', true, 0),
    
    ('BOOK-009', 'The Phoenix Project', 'Gene Kim, Kevin Behr, George Spafford', 3499, 'USD', 'devops',
     'A Novel about IT, DevOps, and Helping Your Business Win.', true, 0),
    
    ('BOOK-010', 'Kubernetes in Action', 'Marko Luksa', 4999, 'USD', 'devops',
     'Learn Kubernetes from a developer perspective.', true, 0)
ON CONFLICT (sku) DO NOTHING;





