USE quickfix_db;

-- Add new columns to service_providers
ALTER TABLE service_providers
    ADD COLUMN IF NOT EXISTS photo VARCHAR(255) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS aadhar_number VARCHAR(12) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS location VARCHAR(150) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS is_verified TINYINT(1) DEFAULT 0;

-- Add new columns to bookings
ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) DEFAULT 'cash',
    ADD COLUMN IF NOT EXISTS is_confirmed TINYINT(1) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP NULL DEFAULT NULL;

-- Add equipment column to services
ALTER TABLE services
    ADD COLUMN IF NOT EXISTS equipment TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS department VARCHAR(100) DEFAULT NULL;

-- Ratings table
CREATE TABLE IF NOT EXISTS ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    user_id INT NOT NULL,
    provider_id INT NOT NULL,
    stars INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES service_providers(id) ON DELETE CASCADE
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    provider_id INT DEFAULT NULL,
    message TEXT NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update existing services with department and equipment
UPDATE services SET department='Plumbing', equipment='Pipe wrench, Plunger, Teflon tape, Pipe cutter, Sealant' WHERE name='Plumbing Repair';
UPDATE services SET department='Electrical', equipment='Multimeter, Wire stripper, Screwdrivers, Electrical tape, Circuit tester' WHERE name='Electrical Wiring';
UPDATE services SET department='HVAC', equipment='Refrigerant gauge, Cleaning brush, Vacuum pump, AC coil cleaner, Gas cylinder' WHERE name='AC Servicing';
UPDATE services SET department='Cleaning', equipment='Mop, Vacuum cleaner, Cleaning liquid, Microfiber cloth, Scrub brush' WHERE name='House Cleaning';
UPDATE services SET department='Carpentry', equipment='Hammer, Saw, Drill machine, Sandpaper, Wood screws, Measuring tape' WHERE name='Carpentry Work';

-- Add Painting service
INSERT INTO services (name, description, price, department, equipment)
VALUES ('Painting Work', 'Interior and exterior wall painting with quality finish', 999.00, 'Painting',
        'Paint brushes, Rollers, Paint trays, Masking tape, Putty knife, Sandpaper, Drop cloth');
