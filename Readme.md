---

# 📨 Email Automation & Reminder System

## 🌾 Project Overview: Multilingual Mandi
This project is a high-performance, asynchronous backend system designed to handle automated email reminders. While built as a general-purpose tool, it is optimized for the **Multilingual Mandi** platform, allowing for localized communication with vendors and farmers regarding price updates, payment deadlines, and session starts.

The system uses **FastAPI** for the web interface, **SQLite** for persistent storage, and a dedicated **Background Scheduler** to process and dispatch emails.

---

## 🚀 Key Features
*   **Asynchronous API**: Built with FastAPI for high-speed request handling.
*   **Background Scheduler**: A decoupled worker that checks the database every 15-30 seconds to send "due" reminders.
*   **Data Integrity**: Uses UUIDs for unique identification and prevents duplicate contact registration (e.g., handling `409 Conflict` errors).
*   **Multilingual Support**: Supports UTF-8 encoding for templates in Hindi, Telugu, and other local languages[cite: 1].
*   **Comprehensive Analytics**: Endpoints to track sent messages and system health[cite: 1].

---

## 🛠️ Tech Stack
*   **Language**: Python 3.10+[cite: 1]
*   **Framework**: FastAPI (Web API)[cite: 1]
*   **Database**: SQLite (SQLAlchemy ORM)[cite: 1]
*   **Email Engine**: SMTP / Secure Mail Processing[cite: 1]
*   **Testing**: Requests library / Swagger UI[cite: 1]

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
To verify the system without manual curl commands, run the provided test script[cite: 1]:

PowerShell
python test_api.py
This script automates:

Creating a new Contact[cite: 1].

Handling UUID mapping[cite: 1].

Scheduling a Reminder for immediate dispatch[cite: 1].

📈 API Documentation
Once the server is running, access the interactive documentation at[cite: 1]:

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc