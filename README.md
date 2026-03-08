# Autonomous IT Service Desk Intelligence & Resolution Automation Platform

## Overview

The **Autonomous IT Service Desk Intelligence & Resolution Automation Platform** is a web-based system designed to improve IT support operations by automating ticket handling and providing intelligent resolution suggestions.

Modern organizations handle thousands of IT support requests daily. Many of these issues are repetitive and require manual triage by IT teams. This project aims to simplify that process by integrating **machine learning-based issue analysis with a ticket management system**.

The platform allows users to submit IT issues, track support tickets, and receive automated suggestions for possible solutions.

---

# Key Features

## User Authentication System

* User registration
* Secure login and logout
* User profile management

## Ticket Management System

* Create and submit support tickets
* Track ticket details
* Store ticket information in a database
* Associate tickets with specific users

## Dashboard

* Central interface for system monitoring
* Displays ticket statistics
* Shows user ticket information

## AI-Based Suggestion Engine

The system includes a machine learning model that analyzes user issues and recommends potential solutions.

Workflow:

```
User submits ticket
        ↓
AI analyzes issue text
        ↓
System retrieves similar past issues
        ↓
Suggested resolution is generated
```

---

# Project Architecture

```
User Interface (Django Templates)
            ↓
Django Backend (Views & APIs)
            ↓
Ticket Management System
            ↓
Machine Learning Suggestion Engine
            ↓
Database Storage
```

---

# Project Structure

```
Autonomous-IT-Service-Desk-Intelligence-Resolution-Automation-Platform/

config/                 # Django project configuration
dashboard/              # Dashboard functionality
tickets/                # Ticket management system
users/                  # Authentication and user profiles
templates/              # HTML templates

manage.py               # Django management script
requirements.txt        # Project dependencies
.gitignore              # Git ignore rules
README.md               # Project documentation
```

---

# Technologies Used

Backend:

* Python
* Django

Machine Learning:

* scikit-learn
* pandas
* NumPy
* joblib

Frontend:

* HTML
* CSS
* Bootstrap

Database:

* SQLite (development)

---

# Machine Learning Model

The AI model is trained on a dataset of IT troubleshooting cases.

Dataset structure:

| issue_text            | resolution                               |
| --------------------- | ---------------------------------------- |
| wifi not connecting   | restart router and check network adapter |
| laptop not turning on | check power supply and battery           |
| printer not printing  | reinstall printer drivers                |

Model pipeline:

```
Text preprocessing
        ↓
TF-IDF vectorization
        ↓
Cosine similarity search
        ↓
Best matching solution returned
```

This approach allows the system to suggest solutions even for issues that are phrased differently but have similar meaning.

---

# Development Status

The project is currently under development.

Completed modules:

* Django backend setup
* User authentication
* Ticket management system

Planned improvements:

* Integration of ML predictions with ticket creation
* Improved UI design
* Advanced analytics dashboard
* Automated ticket prioritization
* Monitoring and anomaly detection

---

# Team Information

Team Members:

* Kakul Gautam
* Akshata Chaudhary
* Khushi Singh
---