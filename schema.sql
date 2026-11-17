-- MadePharmEasy - Pharmacy Management System: database setup
CREATE DATABASE IF NOT EXISTS pharmacy_db;
USE pharmacy_db;

-- Login users (passwords stored as SHA-256 hashes)
CREATE TABLE IF NOT EXISTS users (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password CHAR(64) NOT NULL
);

-- Medicine stock
CREATE TABLE IF NOT EXISTS medicines (
    ref_no     VARCHAR(20) PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    company    VARCHAR(100),
    type       VARCHAR(30),
    batch_no   VARCHAR(30),
    mfg_date   DATE,
    exp_date   DATE,
    price      DECIMAL(10,2) DEFAULT 0,
    quantity   INT DEFAULT 0,
    notes      VARCHAR(255)
);

-- Default login: admin / admin123
INSERT IGNORE INTO users (username, password) VALUES ('admin', SHA2('admin123', 256));

-- Sample data
INSERT IGNORE INTO medicines VALUES
('M001', 'Paracetamol 500mg', 'Cipla',      'Tablet',   'B1001', '2025-01-10', '2027-01-10', 25.00, 200, 'Fever and pain relief'),
('M002', 'Amoxicillin 250mg', 'Sun Pharma', 'Capsule',  'B1002', '2025-03-05', '2026-09-05', 90.50,   8, 'Antibiotic'),
('M003', 'Cough Syrup',       'Dabur',      'Syrup',    'B1003', '2024-06-01', '2026-06-01', 75.00,  40, 'Dry cough'),
('M004', 'Insulin Glargine',  'Biocon',     'Injection','B1004', '2025-08-15', '2027-02-15',650.00,   5, 'Store refrigerated'),
('M005', 'Cetirizine 10mg',   'Dr Reddys',  'Tablet',   'B1005', '2025-02-20', '2028-02-20', 18.00, 150, 'Allergy'),
('M006', 'Betadine Ointment', 'Win-Medicare','Ointment','B1006', '2025-05-11', '2027-05-11', 60.00,  30, 'Antiseptic');
