-- Synthetic SQL Database Dump
CREATE TABLE customer_accounts (
    user_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(64),
    status VARCHAR(64)
);

INSERT INTO customer_accounts VALUES ('user_syn_101', '[REDACTED]', '[REDACTED]', '[REDACTED]', 'DELETED');
INSERT INTO customer_accounts VALUES ('user_syn_102', 'Bob Jones', 'bob.jones@example.com', '+1 555-0102', 'ACTIVE');
