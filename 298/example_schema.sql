-- Example Database Schema for Testing
-- This is a sample e-commerce schema

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    status TINYINT DEFAULT 1,
    country VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INT,
    price DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_status (status),
    INDEX idx_price (price)
);

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id)
);

-- Insert some sample data
INSERT INTO users (username, email, password_hash, first_name, last_name, status, country) VALUES
('user1', 'user1@example.com', 'hash1', 'John', 'Doe', 1, 'USA'),
('user2', 'user2@example.com', 'hash2', 'Jane', 'Smith', 1, 'UK'),
('user3', 'user3@example.com', 'hash3', 'Bob', 'Johnson', 0, 'CN'),
('user4', 'user4@example.com', 'hash4', 'Alice', 'Williams', 1, 'DE'),
('user5', 'user5@example.com', 'hash5', 'Charlie', 'Brown', 1, 'JP');

INSERT INTO products (name, category_id, price, stock, status) VALUES
('Laptop', 1, 999.99, 50, 'active'),
('Smartphone', 1, 699.99, 100, 'active'),
('Headphones', 2, 149.99, 200, 'active'),
('Keyboard', 2, 79.99, 150, 'out_of_stock'),
('Monitor', 3, 299.99, 75, 'active');

INSERT INTO orders (user_id, total_amount, status, shipping_address) VALUES
(1, 1149.98, 'completed', '123 Main St, NY'),
(2, 699.99, 'shipped', '456 Oak Ave, London'),
(1, 299.99, 'pending', '123 Main St, NY'),
(4, 149.99, 'completed', '789 Berlin Str'),
(5, 999.99, 'processing', 'Tokyo Japan');

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 999.99),
(1, 3, 1, 149.99),
(2, 2, 1, 699.99),
(3, 5, 1, 299.99),
(4, 3, 1, 149.99),
(5, 1, 1, 999.99);
