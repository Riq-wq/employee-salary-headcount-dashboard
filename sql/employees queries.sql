select* from employees;

-- Count the total number of employees in the table
SELECT COUNT(*) AS TotalEmployees
FROM employees;
-- Retrieve employee names together with their salaries
SELECT Name, Salary
FROM employees;

-- Find the employee earning the highest salary

SELECT Name, Salary
FROM employees
ORDER BY Salary DESC
LIMIT 1;

-- Find the employee earning the lowest salary

SELECT Name, Salary
FROM employees
ORDER BY Salary ASC
LIMIT 1;

-- Calculate the average salary of all employees

SELECT AVG(Salary) AS AverageSalary
FROM employees;

-- Calculate the average age of employees

SELECT AVG(Age) AS AverageAge
FROM employees;

-- Display the youngest employee

SELECT Name, Age
FROM employees
ORDER BY Age ASC
LIMIT 1;
-- Display employees whose city is Nairobi
select * from employees where city="Nairobi";

-- Count how many employees are in each city

SELECT City,
       COUNT(*) AS NumberOfEmployees
FROM employees
GROUP BY City;

-- Calculate the average salary for each city

SELECT City,
       AVG(Salary) AS AverageSalary
FROM employees
GROUP BY City;

-- Find the highest salary in every city
select City, max(Salary) AS Maxsalarypercity
from employees group by City;

-- Display employees whose salary is greater than the company average

SELECT *
FROM employees
WHERE Salary >
(
    SELECT AVG(Salary)
    FROM employees
);
-- Find employees below the age of 30
select name,age from employees where age <30;

-- Display employees ordered from highest salary to lowest salary

SELECT *
FROM employees
ORDER BY Salary DESC;

-- Display employees who joined after 31 March 2025

SELECT *
FROM employees
WHERE JoinDate > '2025-03-31';

-- Count the number of employees hired in each month

SELECT MONTH(JoinDate) AS MonthJoined,
       COUNT(*) AS Employees
FROM employees
GROUP BY MONTH(JoinDate)
ORDER BY MonthJoined;

-- Calculate the total salary paid to all employees

SELECT SUM(Salary) AS TotalSalaryExpense
FROM employees;


