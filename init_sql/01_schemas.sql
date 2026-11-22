-- ============================================
-- LEGACY HR SCHEMA (Source)
-- ============================================
CREATE SCHEMA IF NOT EXISTS legacy_hr;

CREATE TABLE legacy_hr.employees (
    emp_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    hire_date DATE,
    termination_date DATE,
    status_code CHAR(2),
    dept_code VARCHAR(10),
    job_code VARCHAR(10),
    salary_numeric NUMERIC(12,2),
    currency_cd CHAR(3),
    manager_emp_id VARCHAR(20),
    address_line1 VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    zip_code VARCHAR(10),
    country_cd CHAR(2),
    ssn VARCHAR(11),
    dob DATE,
    gender CHAR(1),
    created_ts TIMESTAMP,
    updated_ts TIMESTAMP
);

CREATE TABLE legacy_hr.departments (
    dept_code VARCHAR(10) PRIMARY KEY,
    dept_name VARCHAR(100),
    parent_dept_code VARCHAR(10),
    cost_center VARCHAR(20),
    location_code VARCHAR(10)
);

CREATE TABLE legacy_hr.jobs (
    job_code VARCHAR(10) PRIMARY KEY,
    job_title VARCHAR(100),
    grade_level VARCHAR(5),
    flsa_status CHAR(1),
    min_salary NUMERIC(12,2),
    max_salary NUMERIC(12,2)
);

-- ============================================
-- TARGET ADP HCM SCHEMA
-- ============================================
CREATE SCHEMA IF NOT EXISTS adp_hcm;

CREATE TABLE adp_hcm.hcm_employee (
    employee_id VARCHAR(20) PRIMARY KEY,
    person_id VARCHAR(20) UNIQUE,
    legal_first_name VARCHAR(50),
    legal_last_name VARCHAR(50),
    preferred_first_name VARCHAR(50),
    work_email VARCHAR(100),
    hire_date DATE,
    termination_date DATE,
    worker_status_cd VARCHAR(10),
    department_id VARCHAR(20),
    job_id VARCHAR(20),
    compensation_grade VARCHAR(10),
    annual_salary_usd NUMERIC(12,2),
    pay_frequency_cd VARCHAR(5),
    flsa_status_cd VARCHAR(1),
    manager_person_id VARCHAR(20),
    home_address_id VARCHAR(20),
    work_location_id VARCHAR(20),
    ssn_encrypted VARCHAR(255),
    date_of_birth DATE,
    gender_cd VARCHAR(1),
    original_hire_date DATE,
    adjusted_service_date DATE,
    created_by VARCHAR(50) DEFAULT 'MIGRATION',
    created_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    updated_dt TIMESTAMP
);

CREATE TABLE adp_hcm.hcm_department (
    department_id VARCHAR(20) PRIMARY KEY,
    department_name VARCHAR(100),
    parent_department_id VARCHAR(20),
    cost_center VARCHAR(20),
    location_id VARCHAR(20),
    effective_start_dt DATE,
    effective_end_dt DATE
);

CREATE TABLE adp_hcm.hcm_job (
    job_id VARCHAR(20) PRIMARY KEY,
    job_title VARCHAR(100),
    job_family VARCHAR(50),
    grade_level VARCHAR(10),
    flsa_status_cd VARCHAR(1),
    min_annual_salary NUMERIC(12,2),
    max_annual_salary NUMERIC(12,2)
);

CREATE TABLE adp_hcm.hcm_address (
    address_id VARCHAR(20) PRIMARY KEY,
    address_line1 VARCHAR(100),
    city VARCHAR(50),
    state_province VARCHAR(50),
    postal_code VARCHAR(20),
    country_cd CHAR(2),
    address_type_cd VARCHAR(10)
);

-- ============================================
-- LOOKUP / REFERENCE TABLES
-- ============================================
CREATE TABLE adp_hcm.ref_status_mapping (
    source_code CHAR(2) PRIMARY KEY,
    target_code VARCHAR(10) NOT NULL,
    description VARCHAR(100)
);

INSERT INTO adp_hcm.ref_status_mapping VALUES
('AC', 'ACTIVE', 'Active'),
('TM', 'TERMINATED', 'Terminated'),
('LO', 'LOA', 'Leave of Absence'),
('RE', 'REHIRE', 'Rehire');

CREATE TABLE adp_hcm.ref_currency_rate (
    from_currency CHAR(3),
    to_currency CHAR(3),
    rate NUMERIC(10,6),
    effective_date DATE,
    PRIMARY KEY (from_currency, to_currency, effective_date)
);

INSERT INTO adp_hcm.ref_currency_rate VALUES
('INR', 'USD', 0.012048, '2026-01-01'),
('USD', 'INR', 83.0, '2026-01-01');