# Task 1: SQL Benchmark Dataset — Ground Truth Queries

**Database:** ClassicModels (PostgreSQL)  
**Schema:** productlines, products, offices, employees, customers, payments, orders, orderdetails

---

## Question 1
**Question:** How many customers are there in total?  
**Difficulty:** Easy | **Category:** COUNT

```sql
SELECT COUNT(*) AS total_customers
FROM customers;
```

**Explanation:** Simple row count on the customers table. No joins needed.

**Expected result:** A single row with the integer count (e.g., `122`).

---

## Question 2
**Question:** List all customers from France.  
**Difficulty:** Easy | **Category:** Filter

```sql
SELECT "customerNumber", "customerName", city
FROM customers
WHERE country = 'France'
ORDER BY "customerName";
```

**Explanation:** Filter customers table on `country = 'France'`. Double-quoted identifiers are required in PostgreSQL because column names use camelCase.

**Expected result:** ~12 rows of French customers.

---

## Question 3
**Question:** What are the top 5 customers by credit limit?  
**Difficulty:** Easy | **Category:** Sorting

```sql
SELECT "customerName", "creditLimit"
FROM customers
ORDER BY "creditLimit" DESC
LIMIT 5;
```

**Explanation:** Sort descending on `creditLimit` and take the top 5. No joins required.

---

## Question 4
**Question:** How many products are in each product line?  
**Difficulty:** Easy | **Category:** GROUP BY

```sql
SELECT "productLine", COUNT(*) AS product_count
FROM products
GROUP BY "productLine"
ORDER BY product_count DESC;
```

**Explanation:** Groups by productLine and counts products in each group.

---

## Question 5
**Question:** What is the total revenue from all orders?  
**Difficulty:** Medium | **Category:** Aggregation

```sql
SELECT ROUND(SUM("priceEach" * "quantityOrdered"), 2) AS total_revenue
FROM orderdetails;
```

**Explanation:** Revenue = priceEach × quantityOrdered per line item. SUM gives total across all orders. ROUND to 2 decimal places.

---

## Question 6
**Question:** List the top 10 best-selling products by total quantity ordered.  
**Difficulty:** Medium | **Category:** JOIN + Aggregation

```sql
SELECT p."productName",
       SUM(od."quantityOrdered") AS total_qty
FROM products p
JOIN orderdetails od ON p."productCode" = od."productCode"
GROUP BY p."productCode", p."productName"
ORDER BY total_qty DESC
LIMIT 10;
```

**Explanation:** Join products to orderdetails on productCode, then sum quantities per product. Alias `p` and `od` prevent ambiguity.

---

## Question 7
**Question:** How many orders were placed each year?  
**Difficulty:** Medium | **Category:** Date Aggregation

```sql
SELECT EXTRACT(YEAR FROM "orderDate") AS year,
       COUNT(*) AS order_count
FROM orders
GROUP BY year
ORDER BY year;
```

**Explanation:** EXTRACT(YEAR FROM ...) pulls the year component from the date. Groups and counts per year.

---

## Question 8
**Question:** Which customers have never placed an order?  
**Difficulty:** Medium | **Category:** LEFT JOIN / NOT EXISTS

```sql
SELECT c."customerNumber", c."customerName"
FROM customers c
LEFT JOIN orders o ON c."customerNumber" = o."customerNumber"
WHERE o."orderNumber" IS NULL
ORDER BY c."customerName";
```

**Explanation:** LEFT JOIN keeps all customers. Customers without orders will have NULL for orderNumber. Filter WHERE IS NULL finds those customers.

---

## Question 9
**Question:** What is the total payment received from each customer, sorted by highest first?  
**Difficulty:** Medium | **Category:** JOIN + Aggregation

```sql
SELECT c."customerName",
       ROUND(SUM(p.amount), 2) AS total_paid
FROM customers c
JOIN payments p ON c."customerNumber" = p."customerNumber"
GROUP BY c."customerNumber", c."customerName"
ORDER BY total_paid DESC;
```

**Explanation:** Join customers to payments, sum amounts per customer, sort descending. Include customerNumber in GROUP BY to avoid ambiguity.

---

## Question 10
**Question:** List all employees and their managers.  
**Difficulty:** Medium | **Category:** Self JOIN

```sql
SELECT e."firstName" || ' ' || e."lastName" AS employee,
       m."firstName" || ' ' || m."lastName" AS manager
FROM employees e
LEFT JOIN employees m ON e."reportsTo" = m."employeeNumber"
ORDER BY manager NULLS FIRST;
```

**Explanation:** Self-join on the employees table using `reportsTo → employeeNumber`. LEFT JOIN keeps the President (who has no manager). Concatenation builds full names.

---

## Question 11
**Question:** How many orders are in each status category?  
**Difficulty:** Easy | **Category:** GROUP BY

```sql
SELECT status, COUNT(*) AS order_count
FROM orders
GROUP BY status
ORDER BY order_count DESC;
```

**Explanation:** Simple group-by on the status column. Shows distribution across Shipped/Cancelled/On Hold/etc.

---

## Question 12
**Question:** What products have a buy price higher than their MSRP?  
**Difficulty:** Easy | **Category:** Column Comparison

```sql
SELECT "productName", "buyPrice", "MSRP"
FROM products
WHERE "buyPrice" > "MSRP";
```

**Explanation:** Compare two numeric columns directly in the WHERE clause. "MSRP" must be double-quoted in PostgreSQL.

---

## Question 13
**Question:** Which office has the most employees?  
**Difficulty:** Medium | **Category:** JOIN + Aggregation

```sql
SELECT o.city, o.country, COUNT(e."employeeNumber") AS employee_count
FROM offices o
JOIN employees e ON o."officeCode" = e."officeCode"
GROUP BY o."officeCode", o.city, o.country
ORDER BY employee_count DESC
LIMIT 1;
```

**Explanation:** Join offices to employees, count employees per office, return the top 1.

---

## Question 14
**Question:** What is the average order value per customer?  
**Difficulty:** Hard | **Category:** Subquery + Multi-JOIN

```sql
SELECT c."customerName",
       ROUND(AVG(order_total), 2) AS avg_order_value
FROM customers c
JOIN orders o ON c."customerNumber" = o."customerNumber"
JOIN (
    SELECT "orderNumber",
           SUM("priceEach" * "quantityOrdered") AS order_total
    FROM orderdetails
    GROUP BY "orderNumber"
) od ON o."orderNumber" = od."orderNumber"
GROUP BY c."customerNumber", c."customerName"
ORDER BY avg_order_value DESC
LIMIT 20;
```

**Explanation:** The subquery first computes each order's total value. Then join customers → orders → subquery, averaging per customer. Three-level query requires careful alias management.

---

## Question 15
**Question:** List all products with quantity in stock below 500.  
**Difficulty:** Easy | **Category:** Filter

```sql
SELECT "productName", "productLine", "quantityInStock"
FROM products
WHERE "quantityInStock" < 500
ORDER BY "quantityInStock";
```

**Explanation:** Simple numeric filter on quantityInStock.

---

## Question 16
**Question:** How many customers does each sales representative manage?  
**Difficulty:** Medium | **Category:** JOIN + Aggregation

```sql
SELECT e."firstName" || ' ' || e."lastName" AS sales_rep,
       COUNT(c."customerNumber") AS customer_count
FROM employees e
JOIN customers c ON e."employeeNumber" = c."salesRepEmployeeNumber"
GROUP BY e."employeeNumber", e."firstName", e."lastName"
ORDER BY customer_count DESC;
```

**Explanation:** Join employees to customers via salesRepEmployeeNumber, count customers per rep.

---

## Question 17
**Question:** What is the profit margin percentage for each product?  
**Difficulty:** Medium | **Category:** Calculated Column

```sql
SELECT "productName",
       "buyPrice",
       "MSRP",
       ROUND(("MSRP" - "buyPrice") / "MSRP" * 100, 2) AS margin_pct
FROM products
ORDER BY margin_pct DESC;
```

**Explanation:** Margin = (MSRP - buyPrice) / MSRP × 100. Computed inline. No joins needed.

---

## Question 18
**Question:** Which customers placed orders in both 2003 and 2004?  
**Difficulty:** Hard | **Category:** Subquery / Set Intersection

```sql
SELECT c."customerName"
FROM customers c
WHERE c."customerNumber" IN (
    SELECT "customerNumber" FROM orders
    WHERE EXTRACT(YEAR FROM "orderDate") = 2003
)
AND c."customerNumber" IN (
    SELECT "customerNumber" FROM orders
    WHERE EXTRACT(YEAR FROM "orderDate") = 2004
)
ORDER BY c."customerName";
```

**Explanation:** Two subqueries find customers who ordered in each year respectively. The AND condition means both must be true — effectively an intersection.

---

## Question 19
**Question:** What is the total revenue generated by each sales representative?  
**Difficulty:** Hard | **Category:** Multi-JOIN + Aggregation

```sql
SELECT e."firstName" || ' ' || e."lastName" AS sales_rep,
       ROUND(SUM(od."priceEach" * od."quantityOrdered"), 2) AS total_revenue
FROM employees e
JOIN customers c ON e."employeeNumber" = c."salesRepEmployeeNumber"
JOIN orders o ON c."customerNumber" = o."customerNumber"
JOIN orderdetails od ON o."orderNumber" = od."orderNumber"
GROUP BY e."employeeNumber", e."firstName", e."lastName"
ORDER BY total_revenue DESC;
```

**Explanation:** 4-table join chain: employees → customers → orders → orderdetails. Revenue computed per line item and summed per employee.

---

## Question 20
**Question:** Find the month with the highest number of orders placed.  
**Difficulty:** Medium | **Category:** Date + Aggregation

```sql
SELECT TO_CHAR("orderDate", 'YYYY-MM') AS month,
       COUNT(*) AS order_count
FROM orders
GROUP BY month
ORDER BY order_count DESC
LIMIT 1;
```

**Explanation:** TO_CHAR formats the date to 'YYYY-MM' string for grouping by month. Returns only the busiest month.

---

## Summary Table

| # | Question | Tables | Difficulty |
|---|---------|--------|-----------|
| 1 | Total customer count | customers | Easy |
| 2 | Customers from France | customers | Easy |
| 3 | Top 5 by credit limit | customers | Easy |
| 4 | Products per product line | products | Easy |
| 5 | Total revenue all orders | orderdetails | Medium |
| 6 | Top 10 products by qty | products, orderdetails | Medium |
| 7 | Orders per year | orders | Medium |
| 8 | Customers with no orders | customers, orders | Medium |
| 9 | Total payments per customer | customers, payments | Medium |
| 10 | Employees and their managers | employees | Medium |
| 11 | Orders by status | orders | Easy |
| 12 | Products where buyPrice > MSRP | products | Easy |
| 13 | Office with most employees | offices, employees | Medium |
| 14 | Average order value per customer | customers, orders, orderdetails | Hard |
| 15 | Low stock products (<500) | products | Easy |
| 16 | Customers per sales rep | employees, customers | Medium |
| 17 | Profit margin per product | products | Medium |
| 18 | Customers ordering in both 2003 & 2004 | customers, orders | Hard |
| 19 | Revenue per sales rep | employees, customers, orders, orderdetails | Hard |
| 20 | Busiest order month | orders | Medium |
