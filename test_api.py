import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. Use a DIFFERENT email and ID to bypass the 409 error
contact_data = {
    "id": "TEST_USER_99",
    "name": "Manisha",
    "email": "kodurumanisha8@gmail.com", # Changed this!
    "timezone": "Asia/Kolkata"
}

response = requests.post(f"{BASE_URL}/contacts", json=contact_data)
contact_result = response.json()
print(f"Contact Response: {response.status_code} - {contact_result}")

# 2. Get the ID the server actually generated
actual_id = contact_result.get("id")

# 3. Add the Reminder using that exact ID
if actual_id:
    reminder_data = {
        "title": "Mandi Price Alert",
        "contact_id": actual_id, 
        "campaign_id": "camp001",
        "start_at_utc": "2026-05-06 14:00:00" # A time in the past sends it immediately
    }

    response = requests.post(f"{BASE_URL}/reminders", json=reminder_data)
    print(f"Reminder Response: {response.status_code} - {response.json()}")
else:
    print("Could not create reminder because contact creation failed.")