
-- Vehicle Rental Management System - Full Database Script
-- Creates database, tables, constraints, triggers, procedure, and sample data

DROP DATABASE IF EXISTS VehicleRentalDB;
CREATE DATABASE VehicleRentalDB;
USE VehicleRentalDB;

-- =========================
-- 1. ROLE TABLE
-- =========================
CREATE TABLE Role (
    RoleID INT AUTO_INCREMENT PRIMARY KEY,
    RoleName VARCHAR(50) NOT NULL UNIQUE
);

-- =========================
-- 2. USER TABLE
-- =========================
CREATE TABLE User (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Phone VARCHAR(20),
    Password VARCHAR(100) NOT NULL,
    RoleID INT NOT NULL,
    CONSTRAINT fk_user_role
        FOREIGN KEY (RoleID)
        REFERENCES Role(RoleID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- =========================
-- 3. VEHICLE TABLE
-- =========================
CREATE TABLE Vehicle (
    VehicleID INT AUTO_INCREMENT PRIMARY KEY,
    VehicleType VARCHAR(50) NOT NULL,
    Model VARCHAR(100) NOT NULL,
    RegistrationNumber VARCHAR(50) NOT NULL UNIQUE,
    RentalPrice DECIMAL(10,2) NOT NULL,
    Status VARCHAR(30) NOT NULL
        CHECK (Status IN ('Available','Rented','Maintenance'))
);

-- =========================
-- 4. RENTAL TABLE
-- =========================
CREATE TABLE Rental (
    RentalID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    VehicleID INT NOT NULL,
    RentalDate DATE NOT NULL,
    ReturnDate DATE,
    TotalAmount DECIMAL(10,2) NOT NULL,
    Status VARCHAR(30) NOT NULL
        CHECK (Status IN ('Active','Completed','Cancelled')),
    CONSTRAINT fk_rental_user
        FOREIGN KEY (UserID) REFERENCES User(UserID)
        ON DELETE CASCADE,
    CONSTRAINT fk_rental_vehicle
        FOREIGN KEY (VehicleID) REFERENCES Vehicle(VehicleID)
        ON DELETE CASCADE
);

-- =========================
-- 5. PAYMENT TABLE
-- =========================
CREATE TABLE Payment (
    PaymentID INT AUTO_INCREMENT PRIMARY KEY,
    RentalID INT NOT NULL,
    PaymentDate DATE NOT NULL,
    Amount DECIMAL(10,2) NOT NULL,
    PaymentMode VARCHAR(20) NOT NULL,
    CONSTRAINT fk_payment_rental
        FOREIGN KEY (RentalID) REFERENCES Rental(RentalID)
        ON DELETE CASCADE
);

-- =========================
-- 6. SAMPLE DATA
-- =========================

-- Roles
INSERT INTO Role (RoleName) VALUES
('Admin'),
('Staff'),
('Customer');

-- Users (10 users: 1 admin, 1 staff, 8 customers)
INSERT INTO User (Name, Email, Phone, Password, RoleID) VALUES
('Admin One', 'admin1@vrms.com', '1112223333', 'pass', 1),
('Staff One', 'staff1@vrms.com', '2223334444', 'pass', 2),
('Alice Johnson', 'alice@vrms.com', '3334445555', 'pass', 3),
('Bob Smith', 'bob@vrms.com', '4445556666', 'pass', 3),
('Charlie Brown', 'charlie@vrms.com', '5556667777', 'pass', 3),
('David Miller', 'david@vrms.com', '6667778888', 'pass', 3),
('Eve Adams', 'eve@vrms.com', '7778889999', 'pass', 3),
('Frank Harris', 'frank@vrms.com', '8889990000', 'pass', 3),
('Grace Lee', 'grace@vrms.com', '1231231234', 'pass', 3),
('Henry Clark', 'henry@vrms.com', '4564564567', 'pass', 3);

-- Vehicles (10 vehicles)
INSERT INTO Vehicle (VehicleType, Model, RegistrationNumber, RentalPrice, Status) VALUES
('Car','Toyota Corolla','TX1001',50.00,'Available'),
('Car','Honda Civic','TX1002',55.00,'Available'),
('Car','Tesla Model 3','TX1003',120.00,'Available'),
('Bike','Yamaha MT-15','BK2001',25.00,'Available'),
('Bike','Royal Enfield Classic','BK2002',30.00,'Available'),
('SUV','Toyota Highlander','SUV3001',90.00,'Available'),
('SUV','Ford Explorer','SUV3002',95.00,'Available'),
('Van','Dodge Caravan','VN4001',80.00,'Available'),
('Truck','Ford F-150','TR5001',110.00,'Available'),
('Truck','Ram 1500','TR5002',115.00,'Available');

-- =========================
-- 7. TRIGGERS
-- =========================

DROP TRIGGER IF EXISTS trg_rental_insert_status;
DROP TRIGGER IF EXISTS trg_rental_update_status;

DELIMITER $$

CREATE TRIGGER trg_rental_insert_status
AFTER INSERT ON Rental
FOR EACH ROW
BEGIN
    IF NEW.Status = 'Active' THEN
        UPDATE Vehicle
        SET Status = 'Rented'
        WHERE VehicleID = NEW.VehicleID;
    END IF;
END$$

CREATE TRIGGER trg_rental_update_status
AFTER UPDATE ON Rental
FOR EACH ROW
BEGIN
    IF NEW.Status IN ('Completed','Cancelled') THEN
        UPDATE Vehicle
        SET Status = 'Available'
        WHERE VehicleID = NEW.VehicleID;
    END IF;
END$$

DELIMITER ;

-- =========================
-- 8. STORED PROCEDURE
-- =========================

DROP PROCEDURE IF EXISTS sp_book_vehicle;

DELIMITER $$

CREATE PROCEDURE sp_book_vehicle(
    IN p_UserID INT,
    IN p_VehicleID INT,
    IN p_Days INT
)
BEGIN
    DECLARE v_price DECIMAL(10,2);
    DECLARE v_total DECIMAL(10,2);

    IF p_Days IS NULL OR p_Days < 1 THEN
        SET p_Days = 1;
    END IF;

    SELECT RentalPrice INTO v_price
    FROM Vehicle
    WHERE VehicleID = p_VehicleID
      AND Status = 'Available';

    IF v_price IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Vehicle not available for booking';
    END IF;

    SET v_total = v_price * p_Days;

    INSERT INTO Rental (UserID, VehicleID, RentalDate, ReturnDate, TotalAmount, Status)
    VALUES (p_UserID, p_VehicleID, CURDATE(), DATE_ADD(CURDATE(), INTERVAL p_Days DAY), v_total, 'Active');
END$$

DELIMITER ;

-- =========================
-- 9. SAMPLE RENTALS & PAYMENTS (10 each)
-- =========================

-- Note: Some rentals are completed, one active
INSERT INTO Rental (UserID, VehicleID, RentalDate, ReturnDate, TotalAmount, Status) VALUES
(3,1,'2024-01-10','2024-01-12',100.00,'Completed'),
(4,2,'2024-01-12','2024-01-15',165.00,'Completed'),
(5,3,'2024-01-15','2024-01-17',240.00,'Completed'),
(6,4,'2024-01-20','2024-01-21',25.00,'Completed'),
(7,5,'2024-02-01','2024-02-03',60.00,'Completed'),
(8,6,'2024-02-05','2024-02-08',270.00,'Completed'),
(9,7,'2024-02-10','2024-02-11',95.00,'Completed'),
(10,8,'2024-02-15','2024-02-18',240.00,'Completed'),
(3,9,'2024-03-01','2024-03-04',330.00,'Completed'),
(4,10,'2024-03-05',NULL,115.00,'Active');

-- Payments for rentals
INSERT INTO Payment (RentalID, PaymentDate, Amount, PaymentMode) VALUES
(1,'2024-01-12',100.00,'Cash'),
(2,'2024-01-15',165.00,'Card'),
(3,'2024-01-17',240.00,'Cash'),
(4,'2024-01-21',25.00,'Card'),
(5,'2024-02-03',60.00,'Cash'),
(6,'2024-02-08',270.00,'Card'),
(7,'2024-02-11',95.00,'Cash'),
(8,'2024-02-18',240.00,'Card'),
(9,'2024-03-04',330.00,'Cash'),
(10,'2024-03-06',115.00,'Cash');
