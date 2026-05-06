---

# 📨 Email Automation & Reminder System

## 🌾 Project Overview: 
This project is a robust, asynchronous backend solution designed for the automated scheduling and dispatching of emails. It is built to solve the challenge of "set-and-forget" notifications, where a user can schedule an email via an API, and a background worker ensures it is delivered at the precise moment required.

The system architecture is divided into two main components:
The Producer (FastAPI): A high-performance REST API that receives contact information and schedules reminders.
The Consumer (Background Scheduler): A decoupled worker process that monitors the database and handles the actual SMTP email transmission.
---
## 🛠️ Tech Stack
*   **Language**: Python 3.14
*   **Framework**: FastAPI (Web API)
*   **Database**: SQLite (SQLAlchemy ORM)
*   **Email Engine**: SMTP / Secure Mail Processing
*   **Testing**: Requests library / Swagger UI

---

## 📁 Folder Structure
```text
EmailAutomationReminderSystem/
├── src/
│   ├── main.py          # FastAPI Server & API Endpoints
│   ├── scheduler.py     # Background Worker Logic
│   └── database.py      # SQLAlchemy Models & Connection
├── data/
│   ├── campaigns.json   # Email Templates & Variables
│   └── reminders.db     # SQLite Database File
├── venv/                # Virtual Environment
└── test_api.py          # Automated Test Script

⚙️ Installation & Setup
Activate Virtual Environment:


PowerShell
.\venv\Scripts\activate
Install Dependencies:


PowerShell
pip install fastapi uvicorn sqlalchemy requests
Run the API Server (Terminal 1):


PowerShell
python -m uvicorn src.main:app --reload
Run the Scheduler (Terminal 2):

PowerShell
python -m src.scheduler
🧪 Testing the Pipeline
To verify the system without manual curl commands, run the provided test script

PowerShell
python test_api.py
This script automates:

Creating a new Contact

Handling UUID mapping

Scheduling a Reminder for immediate dispatch

📈 API Documentation
Once the server is running, access the interactive documentation at

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc
