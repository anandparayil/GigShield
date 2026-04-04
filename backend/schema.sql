CREATE DATABASE IF NOT EXISTS gigshield_db;
USE gigshield_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password_hash VARCHAR(64) NOT NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    city VARCHAR(100) NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    preferred_hours VARCHAR(100) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS linked_platforms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    platform ENUM('Swiggy', 'Zomato', 'Rapido', 'Zepto') NOT NULL,
    worker_code VARCHAR(50) NOT NULL,
    trips_completed INT NOT NULL DEFAULT 0,
    avg_hourly_earning DECIMAL(10,2) NOT NULL DEFAULT 80.00,
    status ENUM('ACTIVE', 'PAUSED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_user_platform (user_id, platform),
    UNIQUE KEY uniq_platform_worker_code (platform, worker_code),
    CONSTRAINT fk_linked_platform_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_name ENUM('Basic', 'Plus', 'Max') NOT NULL,
    base_premium DECIMAL(10,2) NOT NULL,
    final_premium DECIMAL(10,2) NOT NULL,
    premium_breakdown JSON NULL,
    coverage_hours INT NOT NULL DEFAULT 4,
    max_payout DECIMAL(10,2) NOT NULL,
    status ENUM('ACTIVE', 'PAUSED', 'EXPIRED') NOT NULL DEFAULT 'ACTIVE',
    start_date DATE NOT NULL,
    renewal_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_policy_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS triggers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trigger_type ENUM('Heavy Rain', 'Extreme Heat', 'Severe Pollution', 'Demand Collapse', 'Platform Outage') NOT NULL,
    city VARCHAR(100) NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH') NOT NULL DEFAULT 'HIGH',
    description VARCHAR(255) DEFAULT '',
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    status ENUM('ACTIVE', 'RESOLVED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    trigger_id INT NOT NULL,
    expected_earnings DECIMAL(10,2) NOT NULL,
    actual_earnings DECIMAL(10,2) NOT NULL,
    payout_amount DECIMAL(10,2) NOT NULL,
    fraud_score DECIMAL(5,2) NOT NULL DEFAULT 0.10,
    claim_status ENUM('APPROVED', 'FLAGGED', 'PAID') NOT NULL DEFAULT 'APPROVED',
    reason VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_user_trigger (user_id, trigger_id),
    CONSTRAINT fk_claim_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_claim_trigger FOREIGN KEY (trigger_id) REFERENCES triggers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info', 'success', 'warning') NOT NULL DEFAULT 'info',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

INSERT INTO users (full_name, phone, password_hash, role, city, zone_name, preferred_hours)
SELECT 'Administrator', '9999999999', SHA2('admin1', 256), 'admin', 'Chennai', 'HQ', 'All Day'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE phone = '9999999999');
