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
