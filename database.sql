-- =====================================================================
--  WASTENOFOOD — FOOD WASTE MANAGEMENT PLATFORM
--  Professional MySQL Database Schema
--  Reverse-engineered from the complete Flask project (app.py + helper
--  scripts) so that every table/column/ENUM matches the application
--  code exactly. Safe to import in phpMyAdmin / MySQL 5.7+ / MySQL 8+.
--
--  NOTES ON CLEANUP FROM THE OLD database.sql
--  --------------------------------------------------------------------
--  The old file created THREE different databases in one script
--  (food_waste_db, wastenofood, food_donation), defined the `admins`
--  table twice, inserted the admin twice, and created an orphan
--  `donations` table inside an unrelated `food_donation` database.
--  All of that has been removed. This file creates ONE database
--  (wastenofood) with ONE definition per table, and adds the columns
--  the live Flask code actually needs (e.g. `leftover_food_reports`
--  was missing `user_id`, which app.py inserts into).
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

-- ---------------------------------------------------------------------
-- 1. DATABASE
-- ---------------------------------------------------------------------
DROP DATABASE IF EXISTS wastenofood;
CREATE DATABASE wastenofood
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE wastenofood;

-- =====================================================================
-- 2. TABLE: admins
--    Used by: /admin_login, /login (user_type='admin'), check_admins.py,
--             insert_admin.py, update_admin_password.py
-- =====================================================================
CREATE TABLE admins (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)        NOT NULL,
    email           VARCHAR(100)        NOT NULL,
    password        VARCHAR(255)        NOT NULL,
    role            VARCHAR(50)         NOT NULL DEFAULT 'admin',
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_admins_email (email),
    INDEX idx_admins_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 3. TABLE: users
--    Used by: /register, /login, /dashboard, /donor/dashboard, etc.
-- =====================================================================
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)        NOT NULL,
    email           VARCHAR(100)        NOT NULL,
    phone           VARCHAR(15)         NOT NULL,
    password        VARCHAR(255)        NOT NULL,
    user_type       ENUM('Individual','Restaurant','NGO','Hotel')
                                         NOT NULL DEFAULT 'Individual',
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_email (email),
    INDEX idx_users_email (email),
    INDEX idx_users_user_type (user_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 4. TABLE: ngos  (verified / approved NGOs)
--    Used by: /ngos, /ngo/<id>, /ngo/login, /ngo/dashboard,
--             /ngo/register (direct-insert path), admin_approve_ngo
-- =====================================================================
CREATE TABLE ngos (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(200)    NOT NULL,
    description             TEXT,
    mission                 TEXT,
    process                 TEXT,
    activities              TEXT,
    impact                  TEXT,
    contact_email           VARCHAR(100),
    contact_phone           VARCHAR(15),
    address                 TEXT,
    website                 VARCHAR(255),
    logo_url                VARCHAR(255),
    image_url               VARCHAR(255),
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    is_verified             BOOLEAN         NOT NULL DEFAULT FALSE,
    registration_number     VARCHAR(100),
    contact_person          VARCHAR(100),
    government_id_path      VARCHAR(500),
    password                VARCHAR(255),
    created_at              TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ngos_registration_number (registration_number),
    INDEX idx_ngos_is_verified (is_verified),
    INDEX idx_ngos_is_active (is_active),
    INDEX idx_ngos_contact_email (contact_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 5. TABLE: unverified_ngos  (pending NGO applications)
--    Used by: /ngo/register, /ngo/login, /admin/ngos/pending,
--             /admin/ngos/approve/<id>, /admin/ngos/reject/<id>
-- =====================================================================
CREATE TABLE unverified_ngos (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(200)    NOT NULL,
    address                 TEXT            NOT NULL,
    registration_number     VARCHAR(100)    NOT NULL,
    government_id_path      VARCHAR(500)    NOT NULL,
    contact_person          VARCHAR(100)    NOT NULL,
    phone                   VARCHAR(15)     NOT NULL,
    email                   VARCHAR(100)    NOT NULL,
    password                VARCHAR(255)    NOT NULL,
    is_approved             BOOLEAN         NOT NULL DEFAULT FALSE,
    rejection_reason        TEXT,
    created_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                             ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_unverified_ngos_registration_number (registration_number),
    UNIQUE KEY uq_unverified_ngos_email (email),
    INDEX idx_unverified_ngos_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 6. TABLE: donations  (monetary donations to NGOs)
--    Used by: /payment, /ngo-donation, /dashboard, /admin/dashboard,
--             /ngo/<id>/donations
-- =====================================================================
CREATE TABLE donations (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT             NOT NULL,
    ngo_id              INT             NULL,
    amount              DECIMAL(10,2)   NOT NULL,
    payment_method      ENUM('card','upi','netbanking','cod')
                                        NOT NULL DEFAULT 'card',
    transaction_id      VARCHAR(100)    NULL,
    status              ENUM('pending','completed','failed')
                                        NOT NULL DEFAULT 'pending',
    message             TEXT,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_donations_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_donations_ngo FOREIGN KEY (ngo_id) REFERENCES ngos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_donations_user_id (user_id),
    INDEX idx_donations_ngo_id (ngo_id),
    INDEX idx_donations_status (status),
    INDEX idx_donations_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 7. TABLE: donations_tracking  (in-kind food donation tracking + OTP)
--    Used by: /food_donation, /donate-food-track, /ngo/dashboard,
--             /ngo/proof-of-delivery, /donor/dashboard,
--             /user/donation-tracking
-- =====================================================================
CREATE TABLE donations_tracking (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    donation_id         VARCHAR(20)     NOT NULL,
    donor_name          VARCHAR(100)    NOT NULL,
    donor_id            INT             NULL,
    ngo_id              INT             NULL,
    food_quantity       VARCHAR(50),
    location            TEXT,
    status              ENUM('Pending','Collected','Completed')
                                        NOT NULL DEFAULT 'Pending',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    collected_at        TIMESTAMP       NULL DEFAULT NULL,
    proof_image_path    VARCHAR(500),
    ngo_representative  VARCHAR(100),
    otp_code            VARCHAR(6),
    otp_verified        BOOLEAN         NOT NULL DEFAULT FALSE,
    UNIQUE KEY uq_donations_tracking_donation_id (donation_id),
    CONSTRAINT fk_dt_donor FOREIGN KEY (donor_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_dt_ngo FOREIGN KEY (ngo_id) REFERENCES ngos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_dt_donor_id (donor_id),
    INDEX idx_dt_ngo_id (ngo_id),
    INDEX idx_dt_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 8. TABLE: leftover_food_reports
--    Used by: /report-leftover-food, /assign-ngo-to-report,
--             /report-success/<id>, /track-leftover-report/<id>,
--             /ngo/dashboard, /ngo/accept-leftover-report,
--             /user/leftover-reports
--    NOTE: original create_leftover_food_table.py was MISSING the
--    user_id column even though app.py inserts a user_id value and
--    /user/leftover-reports filters "WHERE lfr.user_id = %s".
--    That inconsistency is fixed here.
-- =====================================================================
CREATE TABLE leftover_food_reports (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    event_type          ENUM('Wedding','Party','Hotel','Function') NOT NULL,
    event_date          DATE            NOT NULL,
    event_time          TIME            NOT NULL,
    location            TEXT            NOT NULL,
    latitude            DECIMAL(10,8)   NULL,
    longitude           DECIMAL(11,8)   NULL,
    people_invited      INT             NOT NULL,
    people_ate          INT             NOT NULL,
    food_left_kg        DECIMAL(10,2),
    food_left_plates    INT,
    food_type           ENUM('Veg','Non-Veg','Both') NOT NULL,
    food_photo_path     VARCHAR(255),
    kitchen_photo_path  VARCHAR(255),
    organizer_name      VARCHAR(100)    NOT NULL,
    contact_number      VARCHAR(15)     NOT NULL,
    user_id             INT             NULL,
    status              ENUM('Reported','NGO_Assigned','Picked_Up','Completed','Cancelled')
                                        NOT NULL DEFAULT 'Reported',
    ngo_id              INT             NULL,
    ngo_name            VARCHAR(200),
    proof_image_path    VARCHAR(255),
    donor_confirmed     BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_lfr_ngo FOREIGN KEY (ngo_id) REFERENCES ngos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_lfr_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_lfr_ngo_id (ngo_id),
    INDEX idx_lfr_user_id (user_id),
    INDEX idx_lfr_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 9. TABLE: food_donations  (simple food-drop tracking, dashboard sync)
--    Used by: /food_donation, /dashboard (auto-create + sync logic),
--             /admin/dashboard
-- =====================================================================
CREATE TABLE food_donations (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT             NULL,
    donor_name          VARCHAR(100),
    donor_phone         VARCHAR(15),
    donor_address       TEXT,
    food_type           VARCHAR(50),
    quantity            VARCHAR(50),
    time_available      VARCHAR(50),
    note                TEXT,
    ngo_id              INT             NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'Pending',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fd_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_fd_ngo FOREIGN KEY (ngo_id) REFERENCES ngos(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_fd_user_id (user_id),
    INDEX idx_fd_ngo_id (ngo_id),
    INDEX idx_fd_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 10. TABLE: deliveries
--     Used by: /admin/dashboard ("SELECT COUNT(*) FROM deliveries")
-- =====================================================================
CREATE TABLE deliveries (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL,
    name            VARCHAR(100)    NOT NULL,
    address         TEXT            NOT NULL,
    phone           VARCHAR(15)     NOT NULL,
    food_type       VARCHAR(100),
    quantity        VARCHAR(50),
    pickup_date     DATE,
    pickup_time     TIME,
    status          ENUM('pending','confirmed','picked_up','delivered','cancelled')
                                    NOT NULL DEFAULT 'pending',
    driver_id       INT             NULL,
    notes           TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_deliveries_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_deliveries_user_id (user_id),
    INDEX idx_deliveries_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 11. TABLE: feedback
--     Used by: /submit_feedback, /admin/feedback
-- =====================================================================
CREATE TABLE feedback (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NULL,
    rating          TINYINT UNSIGNED NOT NULL,
    comment         TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_feedback_rating CHECK (rating BETWEEN 1 AND 5),
    INDEX idx_feedback_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 12. TABLE: issues
--     Used by: /submit_issue, /admin/feedback
-- =====================================================================
CREATE TABLE issues (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NULL,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT            NOT NULL,
    status          ENUM('new','in_progress','resolved','closed')
                                    NOT NULL DEFAULT 'new',
    priority        ENUM('low','medium','high','urgent')
                                    NOT NULL DEFAULT 'medium',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_issues_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_issues_user_id (user_id),
    INDEX idx_issues_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 13. TABLE: contact_messages
--     (Reserved for the Contact/Support form — no live route wired to
--     it yet in app.py, kept per project requirements for future use.)
-- =====================================================================
CREATE TABLE contact_messages (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    email           VARCHAR(100)    NOT NULL,
    phone           VARCHAR(15),
    subject         VARCHAR(200),
    message         TEXT            NOT NULL,
    status          ENUM('new','read','responded') NOT NULL DEFAULT 'new',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_contact_messages_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 14. TABLE: impact_stats
--     (Reserved per-user impact summary — no live route wired to it
--     yet in app.py, kept per project requirements for future use.)
-- =====================================================================
CREATE TABLE impact_stats (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    user_id                 INT             NOT NULL,
    total_food_saved        DECIMAL(10,2)   NOT NULL DEFAULT 0,
    total_meals_donated     INT             NOT NULL DEFAULT 0,
    total_co2_saved         DECIMAL(10,2)   NOT NULL DEFAULT 0,
    total_money_saved       DECIMAL(10,2)   NOT NULL DEFAULT 0,
    last_updated            TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                             ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_impact_stats_user_id (user_id),
    CONSTRAINT fk_impact_stats_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 15. TABLE: composting_tips  (static content for /composite page)
-- =====================================================================
CREATE TABLE composting_tips (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT            NOT NULL,
    category        ENUM('green','brown','avoid','process','benefits') NOT NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_composting_tips_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 16. TABLE: eco_tips  (static content for /eco page)
-- =====================================================================
CREATE TABLE eco_tips (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT            NOT NULL,
    category        VARCHAR(50),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_eco_tips_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
--  SAMPLE / SEED DATA
-- =====================================================================

-- ---------------------------------------------------------------------
-- Admin account
--   Email:    admin123@gmail.com
--   Password: admin123
--   Hash generated with: werkzeug.security.generate_password_hash(
--             'admin123', method='pbkdf2:sha256')  — same call app.py
--             uses, so login works out of the box.
-- ---------------------------------------------------------------------
INSERT INTO admins (name, email, password, role) VALUES
('Admin User', 'admin123@gmail.com',
 'pbkdf2:sha256:1000000$1UkwYOHCmrLqYmuS$eec9b4811c4fafb6783b35cf69acf21365f3b46c5f83d002efe62fb18e25c72c',
 'super_admin');

-- ---------------------------------------------------------------------
-- Sample users
--   Password for ALL sample users below: user123
--   Hash generated with the same pbkdf2:sha256 method as app.py.
-- ---------------------------------------------------------------------
INSERT INTO users (name, email, phone, password, user_type) VALUES
('Ravi Kumar',      'ravi.kumar@example.com',    '9876543210',
 'pbkdf2:sha256:1000000$DC3brleqalopGHay$99e9443892b4206a460bd656eaf196cfd381b2c9fc2099d220b178293da317e2', 'Individual'),
('Priya Sharma',     'priya.sharma@example.com',  '9876543211',
 'pbkdf2:sha256:1000000$DC3brleqalopGHay$99e9443892b4206a460bd656eaf196cfd381b2c9fc2099d220b178293da317e2', 'Individual'),
('Spice Route Restaurant', 'contact@spiceroute.com', '9876543212',
 'pbkdf2:sha256:1000000$DC3brleqalopGHay$99e9443892b4206a460bd656eaf196cfd381b2c9fc2099d220b178293da317e2', 'Restaurant'),
('Grand Palace Hotel', 'events@grandpalace.com',  '9876543213',
 'pbkdf2:sha256:1000000$DC3brleqalopGHay$99e9443892b4206a460bd656eaf196cfd381b2c9fc2099d220b178293da317e2', 'Hotel'),
('Anita Desai',       'anita.desai@example.com',  '9876543214',
 'pbkdf2:sha256:1000000$DC3brleqalopGHay$99e9443892b4206a460bd656eaf196cfd381b2c9fc2099d220b178293da317e2', 'Individual');

-- ---------------------------------------------------------------------
-- 10 verified & active NGOs
--   Password for ALL sample NGOs below: ngo123
--   Hash generated with the same pbkdf2:sha256 method as app.py.
-- ---------------------------------------------------------------------
INSERT INTO ngos
(name, description, mission, process, activities, impact,
 contact_email, contact_phone, address, website, logo_url, image_url,
 is_active, is_verified, registration_number, contact_person,
 government_id_path, password) VALUES

('Akshaya Patra Foundation',
 'Largest mid-day meal programme in India, feeding millions of school children every day.',
 'No child in India shall be deprived of education because of hunger.',
 '1. Collect grain and funds donations\n2. Cook in centralized kitchens\n3. Distribute hot meals to schools',
 'Mid-day meal distribution, Nutrition awareness programs',
 'Feeds 2+ million children daily across India.',
 'info@akshayapatra.org', '+91-80-30143400', 'Hare Krishna Hill, Chord Road, Bengaluru, Karnataka',
 'https://www.akshayapatra.org', '', '', 1, 1, 'NGO-REG-0001', 'Suresh Rao', 'gov_id_akshaya.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Robin Hood Army',
 'Zero-funds volunteer organization that collects surplus food from restaurants and events.',
 'Eliminate hunger and reduce food waste through community volunteering.',
 '1. Partner with restaurants and event organizers\n2. Volunteers collect surplus food\n3. Distribute directly to those in need',
 'Food drives, Feeding homeless communities, Volunteer recruitment',
 'Served 100+ million meals across India.',
 'contact@robinhoodarmy.com', '+91-11-41551800', 'Connaught Place, New Delhi',
 'https://robinhoodarmy.com', '', '', 1, 1, 'NGO-REG-0002', 'Neel Ghose', 'gov_id_robinhood.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Feeding India (by Zomato)',
 'Tech-driven donation platform connecting surplus food with hungry communities.',
 'End hunger in India using technology and a strong volunteer network.',
 'Real-time app-based food donation and pickup coordination system.',
 'Food rescue operations, Hunger relief drives, School meal programs',
 '50+ million meals rescued and redistributed.',
 'support@feedingindia.org', '+91-124-4616161', 'Zomato Tower, Gurugram, Haryana',
 'https://www.feedingindia.org', '', '', 1, 1, 'NGO-REG-0003', 'Meera Iyer', 'gov_id_feedingindia.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Annamrita Foundation (ISKCON)',
 'Provides nutritious cooked meals to underprivileged children through modern kitchens.',
 'Improve health and education outcomes by ending classroom hunger.',
 '1. Operate large-scale modern kitchens\n2. Prepare fresh meals daily\n3. Distribute meals to partner schools',
 'Mid-day meal program, Emergency relief feeding',
 'Serves 1.5+ million meals daily across several states.',
 'info@annamrita.org', '+91-22-61470000', 'Juhu, Mumbai, Maharashtra',
 'https://annamrita.org', '', '', 1, 1, 'NGO-REG-0004', 'Govind Das', 'gov_id_annamrita.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Food For All',
 'We distribute surplus food to poor families and homeless communities.',
 'Ensure no edible food goes to waste while people go hungry nearby.',
 '1. Receive surplus food reports\n2. Coordinate volunteer pickup\n3. Distribute same-day to shelters',
 'Daily food distribution, Shelter partnerships',
 'Supports over 5,000 families every month.',
 'foodforall@gmail.com', '+91-98765-10001', 'Andheri East, Mumbai, Maharashtra',
 'https://foodforall.example.org', '', '', 1, 1, 'NGO-REG-0005', 'Rakesh Mehta', 'gov_id_foodforall.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Hunger Relief India',
 'A nationwide movement ensuring leftover food from events reaches the needy.',
 'Build a hunger-free India through rapid food redistribution.',
 '1. Partner with event venues\n2. Rapid-response pickup teams\n3. Same-day distribution',
 'Event food rescue, Community kitchens',
 'Redistributed over 2 million meals since inception.',
 'hungerreliefindia@gmail.com', '+91-98765-10002', 'Banjara Hills, Hyderabad, Telangana',
 'https://hungerreliefindia.example.org', '', '', 1, 1, 'NGO-REG-0006', 'Lakshmi Reddy', 'gov_id_hungerrelief.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Robin Food Mission',
 'We rescue food from events, restaurants, and markets before it is wasted.',
 'Turn surplus food into meals for people who need it most.',
 '1. Identify surplus food sources\n2. Volunteer-driven collection\n3. Deliver to community kitchens',
 'Market food rescue, Restaurant partnerships',
 'Rescued 800,000+ kg of food from going to waste.',
 'robinfoodmission@gmail.com', '+91-98765-10003', 'Salt Lake, Kolkata, West Bengal',
 'https://robinfoodmission.example.org', '', '', 1, 1, 'NGO-REG-0007', 'Arjun Sen', 'gov_id_robinfood.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Feeding Smiles Foundation',
 'A youth-led initiative providing daily meals to underprivileged kids.',
 'Bring a smile to every child through consistent access to food.',
 '1. School and community outreach\n2. Volunteer-cooked meals\n3. Weekly distribution drives',
 'Child nutrition programs, Youth volunteering',
 'Feeds 3,000+ children every week.',
 'feedingsmilesfoundation@gmail.com', '+91-98765-10004', 'Koramangala, Bengaluru, Karnataka',
 'https://feedingsmiles.example.org', '', '', 1, 1, 'NGO-REG-0008', 'Divya Nair', 'gov_id_feedingsmiles.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Green Earth Food Rescue',
 'We work with supermarkets and grocers to save unsold but edible food.',
 'Reduce landfill waste by redirecting near-expiry food to people in need.',
 '1. Partner with supermarkets\n2. Daily surplus pickup\n3. Sort and redistribute via local NGOs',
 'Supermarket rescue program, Cold-storage logistics',
 'Diverted 1.2 million kg of food from landfills.',
 'greenearthfoodrescue@gmail.com', '+91-98765-10005', 'Vashi, Navi Mumbai, Maharashtra',
 'https://greenearthfoodrescue.example.org', '', '', 1, 1, 'NGO-REG-0009', 'Kabir Malhotra', 'gov_id_greenearth.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02'),

('Humanity First Kitchen',
 'Runs free community kitchens for anyone who needs a meal, no questions asked.',
 'No one should sleep hungry in our city.',
 '1. Operate daily free-kitchen sites\n2. Source surplus and donated ingredients\n3. Serve meals to all',
 'Free kitchens, Night shelters meal service',
 'Serves 4,000+ meals daily across 6 kitchen locations.',
 'humanityfirstkitchen@gmail.com', '+91-98765-10006', 'Chandni Chowk, Delhi',
 'https://humanityfirstkitchen.example.org', '', '', 1, 1, 'NGO-REG-0010', 'Fatima Sheikh', 'gov_id_humanityfirst.pdf',
 'pbkdf2:sha256:1000000$AwbmeRSB5Y8VQIwp$beb267d1e60115521498d7c2d7898f2965652dd22609f859c5a495b0e7fe2c02');

-- ---------------------------------------------------------------------
-- Sample monetary donations
-- ---------------------------------------------------------------------
INSERT INTO donations (user_id, ngo_id, amount, payment_method, status, message, created_at) VALUES
(1, 1, 500.00,  'upi',        'completed', 'Keep up the great work!',            '2026-06-01 10:15:00'),
(1, 2, 1000.00, 'card',       'completed', NULL,                                  '2026-06-10 14:20:00'),
(2, 3, 250.00,  'netbanking', 'completed', 'Happy to support Feeding India.',     '2026-06-15 09:05:00'),
(3, 4, 2000.00, 'upi',        'completed', 'From Spice Route Restaurant.',        '2026-06-20 18:45:00'),
(5, 5, 150.00,  'card',       'pending',   NULL,                                  '2026-07-01 11:30:00'),
(2, 6, 750.00,  'upi',        'completed', 'For the Hyderabad kitchen.',          '2026-07-03 08:00:00'),
(1, 7, 300.00,  'cod',        'failed',    'Payment did not go through.',         '2026-07-05 16:10:00');

-- ---------------------------------------------------------------------
-- Sample donations_tracking (in-kind food donations with OTP)
-- ---------------------------------------------------------------------
INSERT INTO donations_tracking
(donation_id, donor_name, donor_id, ngo_id, food_quantity, location, status, otp_code, otp_verified, created_at) VALUES
('FD10234', 'Ravi Kumar',  1, 1, '10 kg Rice and Curry',     'Bengaluru, Karnataka',  'Completed', '482913', 1, '2026-06-02 09:00:00'),
('FD10587', 'Priya Sharma', 2, 3, '25 boxes Cooked Meals',    'Gurugram, Haryana',     'Pending',   '739104', 0, '2026-07-04 12:00:00'),
('FD10692', 'Grand Palace Hotel', 4, 4, '50 kg Mixed Food',   'Mumbai, Maharashtra',   'Collected', '215687', 1, '2026-07-06 15:30:00'),
('FD10745', 'Anita Desai', 5, 8, '5 kg Snacks',               'Bengaluru, Karnataka',  'Pending',   '904321', 0, '2026-07-08 10:00:00');

-- ---------------------------------------------------------------------
-- Sample food_donations
-- ---------------------------------------------------------------------
INSERT INTO food_donations
(user_id, donor_name, donor_phone, donor_address, food_type, quantity, time_available, note, ngo_id, status, created_at) VALUES
(1, 'Ravi Kumar', '9876543210', 'HSR Layout, Bengaluru', 'Cooked Meal', '10 kg', 'Evening 6-8 PM', 'Leftover from birthday party', 1, 'Completed', '2026-06-02 08:30:00'),
(3, 'Spice Route Restaurant', '9876543212', 'MG Road, Gurugram', 'Cooked Meal', '25 boxes', 'Night 9-10 PM', 'Daily surplus', 3, 'Pending', '2026-07-04 11:30:00'),
(4, 'Grand Palace Hotel', '9876543213', 'Bandra, Mumbai', 'Mixed Food', '50 kg', 'Afternoon 2-4 PM', 'Wedding leftovers', 4, 'Completed', '2026-07-06 14:45:00'),
(NULL, 'Guest Donor', '9998887771', 'Indiranagar, Bengaluru', 'Snacks', '5 kg', 'Morning 9-11 AM', 'Office event leftovers', 8, 'Pending', '2026-07-08 09:15:00');

-- ---------------------------------------------------------------------
-- Sample leftover_food_reports
-- ---------------------------------------------------------------------
INSERT INTO leftover_food_reports
(event_type, event_date, event_time, location, latitude, longitude, people_invited, people_ate,
 food_left_kg, food_left_plates, food_type, organizer_name, contact_number, user_id, status,
 ngo_id, ngo_name, donor_confirmed, created_at) VALUES
('Wedding', '2026-06-05', '20:00:00', 'JP Nagar, Bengaluru, Karnataka', 12.90930000, 77.58480000,
 300, 240, 35.50, 70, 'Both', 'Ramesh Gowda', '9876500001', 1, 'Completed', 1, 'Akshaya Patra Foundation', 1, '2026-06-05 22:00:00'),
('Party', '2026-07-01', '22:30:00', 'Sector 29, Gurugram, Haryana', 28.46950000, 77.07230000,
 80, 60, 8.00, 20, 'Veg', 'Simran Kaur', '9876500002', 2, 'NGO_Assigned', 3, 'Feeding India (by Zomato)', 0, '2026-07-01 23:00:00'),
('Function', '2026-07-07', '19:00:00', 'Bandra West, Mumbai, Maharashtra', 19.05960000, 72.83540000,
 500, 420, 60.00, 100, 'Non-Veg', 'Grand Palace Events Team', '9876500003', 4, 'Reported', NULL, NULL, 0, '2026-07-07 21:30:00');

-- ---------------------------------------------------------------------
-- Sample deliveries
-- ---------------------------------------------------------------------
INSERT INTO deliveries
(user_id, name, address, phone, food_type, quantity, pickup_date, pickup_time, status, notes, created_at) VALUES
(1, 'Ravi Kumar', 'HSR Layout, Bengaluru, Karnataka', '9876543210', 'Cooked Meal', '10 kg', '2026-06-02', '18:00:00', 'delivered', 'Delivered to Akshaya Patra volunteers.', '2026-06-01 20:00:00'),
(3, 'Spice Route Restaurant', 'MG Road, Gurugram, Haryana', '9876543212', 'Cooked Meal', '25 boxes', '2026-07-05', '21:00:00', 'confirmed', 'Awaiting pickup confirmation.', '2026-07-04 12:00:00'),
(4, 'Grand Palace Hotel', 'Bandra, Mumbai, Maharashtra', '9876543213', 'Mixed Food', '50 kg', '2026-07-06', '15:00:00', 'delivered', 'Wedding surplus collected successfully.', '2026-07-06 13:00:00'),
(2, 'Priya Sharma', 'Banjara Hills, Hyderabad, Telangana', '9876543211', 'Snacks', '5 kg', '2026-07-10', '10:00:00', 'pending', 'Pickup requested for this morning.', '2026-07-09 18:00:00');

-- ---------------------------------------------------------------------
-- Sample feedback
-- ---------------------------------------------------------------------
INSERT INTO feedback (user_id, rating, comment, created_at) VALUES
(1, 5, 'Amazing platform, made donating leftover food effortless!', '2026-06-03 10:00:00'),
(2, 4, 'Great initiative, tracking donations is very helpful.', '2026-06-20 09:30:00'),
(3, 5, 'Our restaurant loves being able to reduce waste this way.', '2026-07-05 17:00:00'),
(NULL, 3, 'App could use a dark mode.', '2026-07-08 12:15:00');

-- ---------------------------------------------------------------------
-- Sample issues
-- ---------------------------------------------------------------------
INSERT INTO issues (user_id, title, description, status, priority, created_at) VALUES
(2, 'OTP not received', 'I did not receive the OTP for delivery confirmation.', 'resolved', 'high', '2026-06-25 11:00:00'),
(4, 'Cannot upload proof image', 'The proof of delivery image upload fails on my browser.', 'in_progress', 'medium', '2026-07-06 16:00:00'),
(NULL, 'NGO list not loading', 'The NGO dropdown was empty on the food donation page.', 'new', 'low', '2026-07-09 08:45:00');

-- ---------------------------------------------------------------------
-- Sample contact_messages
-- ---------------------------------------------------------------------
INSERT INTO contact_messages (name, email, phone, subject, message, status, created_at) VALUES
('Karan Mehta', 'karan.mehta@example.com', '9812345678', 'Partnership Inquiry', 'We would like to explore a corporate CSR partnership with your platform.', 'new', '2026-07-02 09:00:00'),
('Sunita Rao', 'sunita.rao@example.com', '9812345679', 'Volunteer Opportunity', 'How can I sign up to volunteer for food pickups in Bengaluru?', 'read', '2026-07-04 14:30:00'),
('Vikram Joshi', 'vikram.joshi@example.com', NULL, 'Bug Report', 'The report leftover food form does not accept decimal values for plates.', 'responded', '2026-07-07 19:10:00');

-- ---------------------------------------------------------------------
-- Sample impact_stats
-- ---------------------------------------------------------------------
INSERT INTO impact_stats (user_id, total_food_saved, total_meals_donated, total_co2_saved, total_money_saved) VALUES
(1, 45.50, 136, 113.75, 6825.00),
(2, 12.00, 36,  30.00,  1800.00),
(3, 80.00, 240, 200.00, 12000.00),
(4, 60.00, 180, 150.00, 9000.00),
(5, 5.00,  15,  12.50,  750.00);

-- ---------------------------------------------------------------------
-- Sample composting_tips (for /composite page)
-- ---------------------------------------------------------------------
INSERT INTO composting_tips (title, description, category) VALUES
('Add Green Materials', 'Include vegetable peels, fruit scraps, and coffee grounds for nitrogen-rich content.', 'green'),
('Balance With Brown Materials', 'Add dry leaves, cardboard, or sawdust to balance moisture and carbon.', 'brown'),
('Avoid Meat and Dairy', 'Do not compost meat, dairy, or oily foods as they attract pests and slow decomposition.', 'avoid'),
('Turn the Pile Regularly', 'Turn your compost pile every 1-2 weeks to aerate it and speed up decomposition.', 'process'),
('Reduces Landfill Waste', 'Composting food scraps can divert up to 30% of household waste from landfills.', 'benefits'),
('Maintain Moisture Balance', 'Your compost should feel like a damp sponge — not soggy, not bone dry.', 'process'),
('Improves Soil Health', 'Finished compost adds nutrients and improves structure in garden soil.', 'benefits');

-- ---------------------------------------------------------------------
-- Sample eco_tips (for /eco page)
-- ---------------------------------------------------------------------
INSERT INTO eco_tips (title, description, category) VALUES
('Buy Only What You Need', 'Plan meals ahead and make a shopping list to avoid impulse buys that go to waste.', 'shopping'),
('Store Food Properly', 'Use airtight containers and correct refrigeration to extend the shelf life of produce.', 'storage'),
('Use Leftovers Creatively', 'Turn last night''s dinner into a new dish instead of throwing it away.', 'cooking'),
('Understand Date Labels', '"Best before" is about quality, not safety — food is often still good to eat after that date.', 'awareness'),
('Freeze Before It Spoils', 'Freeze bread, fruits, and cooked meals before they go bad to use later.', 'storage'),
('Donate Surplus Food', 'Partner with local NGOs to donate excess food from events instead of discarding it.', 'community'),
('Compost What You Cannot Eat', 'Turn unavoidable food scraps into nutrient-rich compost for your garden.', 'sustainability');

-- =====================================================================
--  DONE
-- =====================================================================
SELECT 'wastenofood database created and seeded successfully!' AS status;