-- Departments table
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- Employees table
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    salary NUMERIC(10,2) NOT NULL,
    hire_date DATE NOT NULL
);


-- Projects table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    start_date DATE NOT NULL,
    budget NUMERIC(12,2) NOT NULL
);

-- Seed departments
INSERT INTO departments (name) VALUES
('Engineering'),
('HR'),
('Marketing'),
('Finance');

-- Seed employees
INSERT INTO employees (name, department_id, salary, hire_date) VALUES
('Alice', 1, 125000, '2017-03-12'),
('Bob', 2, 80000, '2018-07-10'),
('Charlie', 1, 135000, '2019-01-15'),
('Diana', 3, 95000, '2020-09-20'),
('Edward', 4, 115000, '2016-12-02'),
('Fay', 1, 110000, '2022-11-05');
-- Seed projects
INSERT INTO projects (name, department_id, start_date, budget) VALUES
('People Analytics Platform', 1, '2021-02-01', 250000),
('Benefits Revamp', 2, '2020-05-15', 120000),
('Ad Campaign Q4', 3, '2022-09-01', 175000),
('ERP Migration', 4, '2019-11-20', 320000);

