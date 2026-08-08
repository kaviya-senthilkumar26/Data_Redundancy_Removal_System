# Data Redundancy Removal System

A web-based system developed using Python Flask to detect, prevent, and remove redundant records from a database.

## 🔗 Live Demo

https://data-redundancy-removal-system-u11l.onrender.com

## 📌 Project Overview

The Data Redundancy Removal System helps maintain clean and reliable data by identifying duplicate and potentially redundant records.

The system validates user input, prevents duplicate entries, scans existing records, calculates data quality, and allows redundant records to be removed.

## 🎯 Objectives

- Prevent duplicate records from being inserted.
- Detect exact duplicate records.
- Detect potential duplicate records.
- Search and manage stored records.
- Edit and delete records.
- Remove exact redundant records.
- Calculate data quality score.
- Calculate redundancy percentage.
- Provide a simple web-based interface.

## 🛠️ Technologies Used

- Python
- Flask
- PostgreSQL
- SQLite
- HTML
- CSS
- Bootstrap
- Gunicorn
- Render

## ⚙️ Main Features

### 1. Data Validation

The system validates:

- Name
- Email address
- Empty fields
- Invalid characters

### 2. Duplicate Prevention

Before inserting a record, the system checks whether the email or logical record already exists.

### 3. Duplicate Scanner

The scanner identifies:

- Exact duplicates
- Potential duplicates

The system normalizes text by ignoring:

- Capitalization
- Extra spaces

Example:

`Kaviya`

and

`KAVIYA`

can be detected as similar records.

### 4. Record Management

Users can:

- Add records
- Search records
- Edit records
- Delete records

### 5. Data Quality Score

The dashboard displays a data quality score based on the uniqueness of stored records.

### 6. Redundancy Percentage

The system calculates the percentage of redundant records in the database.

### 7. Redundant Record Removal

Exact duplicate records can be removed while keeping the oldest record.

## 🏗️ System Workflow

```text
                ┌──────────────────┐
                │      User        │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  Flask Web App   │
                └────────┬─────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      ┌───────────────┐     ┌────────────────┐
      │ Data          │     │ Duplicate      │
      │ Validation    │     │ Detection      │
      └───────┬───────┘     └───────┬────────┘
              │                     │
              └──────────┬──────────┘
                         ▼
                ┌──────────────────┐
                │    Database      │
                │ PostgreSQL /     │
                │ SQLite           │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Clean & Reliable │
                │      Data        │
                └──────────────────┘
