# Text-to-SQL Agent System
> Built on the ClassicModels PostgreSQL database using LangChain + Google Gemini

---

## Project Overview

This project builds a **complete Text-to-SQL agentic system** on top of the ClassicModels database (orders, products, customers, employees, offices, payments, orderdetails, productlines). It covers:

- **1** — SQL Benchmark Dataset (ground truth queries)
- **2** — Evaluation Strategy design
- **3** — Text-to-SQL Agent (LangChain + Gemini)
- **4** — Agentic query execution with self-correction

---

## Folder Structure

```
text2sql_agent/
├── README.md                    ← This file
├── .env.example                 ← Environment variables template
├── requirements.txt             ← Python dependencies
│
├── app/
│   ├── agent.py                 ← Main Text-to-SQL agent
│   ├── chain.py                 ← LangChain SQL chain setup
│   ├── database.py              ← PostgreSQL connection + schema loader
│   ├── prompts.py               ← System prompts for Gemini
│   ├── ui.py                    ← Streamlit web UI
│   └── self_correct.py          ← Self-correction / retry loop
│
├── benchmark/
│   ├── questions.json           ← 20 NL questions benchmark dataset
│   └── ground_truth_queries.sql ← Verified ground truth SQL queries
│
├── evaluation/
│   ├── evaluator.py             ← Automated evaluation runner
│   ├── metrics.py               ← Evaluation metrics (EM, EX, F1, etc.)
│   └── report.py                ← Generate evaluation report
│
├── data/
│   └── schema.json              ← Database schema for context injection
│
└── docs/
    ├── benchmark_report.md      ← Task 1: Ground truth queries + results
    └── evaluation_strategy.md   ← Task 2: Evaluation framework design
```

---

## Quick Start

### 1. Clone / organize the project

```bash
# Create and enter project folder
mkdir text2sql_agent && cd text2sql_agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Run the agent

```bash
python app/agent.py
```

### 5. Run the web UI

```bash
streamlit run app/ui.py
```

Open the local Streamlit URL shown in your terminal, then ask a question about the ClassicModels database.

### 6. Run evaluation

```bash
python evaluation/evaluator.py
```

---

## Database Schema (ClassicModels)

| Table | Key Columns |
|-------|-------------|
| `productlines` | productLine, textDescription |
| `products` | productCode, productName, productLine, buyPrice, MSRP, quantityInStock |
| `offices` | officeCode, city, country, territory |
| `employees` | employeeNumber, firstName, lastName, jobTitle, officeCode, reportsTo |
| `customers` | customerNumber, customerName, country, salesRepEmployeeNumber, creditLimit |
| `payments` | customerNumber, checkNumber, paymentDate, amount |
| `orders` | orderNumber, orderDate, status, customerNumber |
| `orderdetails` | orderNumber, productCode, quantityOrdered, priceEach |
