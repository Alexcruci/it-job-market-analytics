import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Adzuna extraction

# Define API parameters
adzuna_app_id = os.getenv("ADZUNA_APP_ID")
adzuna_app_key = os.getenv("ADZUNA_APP_KEY")

params = {
    "app_id": adzuna_app_id,
    "app_key": adzuna_app_key,
    "results_per_page": 200,
    "what": "Data Engineer",
}

adzuna_jobs = [] # Stores all jobs extracted from the API
page = 1
while True:
    url = f"https://api.adzuna.com/v1/api/jobs/it/search/{page}"
    response = requests.get(url, params=params)
    if response.status_code != 200:
        break
    adzuna_data = response.json()
    if len(adzuna_data["results"]) == 0:
        break
    print(f"Page {page}: {len(adzuna_data['results'])} jobs")
    adzuna_jobs.extend(adzuna_data["results"]) # Add the jobs from the current page to the list
    page+=1

print("Adzuna data obtained!")
with open("data/raw/adzuna_jobs.json", "w") as file:
    json.dump(adzuna_jobs, file)
print("Adzuna JSON file created")

# Jooble extraction

# Define API parameters
jooble_app_key = os.getenv("JOOBLE_API_KEY")
jooble_url = f"https://jooble.org/api/{jooble_app_key}"

headers = {"Content-type": "application/json"}
body = {
    "keywords": "IT",
    "location": "Italy",
    "page": 1
}

jooble_jobs = [] # Stores all jobs extracted from the API

while True:
    response = requests.post(
        jooble_url,
        headers=headers,
        json=body
    )
    jooble_data = response.json()
    if len(jooble_data["jobs"]) == 0: # Stop pagination when the API returns no jobs
        break
    jooble_jobs.extend(jooble_data["jobs"]) 
    body["page"]+= 1

print("Jooble data obtained!")
with open("data/raw/jooble_jobs.json", "w") as file:
    json.dump(jooble_jobs, file)
print("Jooble JSON file created")