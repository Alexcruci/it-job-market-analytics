import json
import os

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

from pathlib import Path

Path("data/raw").mkdir(parents=True, exist_ok=True)

# Adzuna extraction
# Define API parameters
adzuna_app_id = os.getenv("ADZUNA_APP_ID")
adzuna_app_key = os.getenv("ADZUNA_APP_KEY")

params = {
    "app_id": adzuna_app_id,
    "app_key": adzuna_app_key,
    "results_per_page": 200,
    "category": "it-jobs",
}

page = 1
adzuna_jobs = []
max_retries = 3
seen_ids = set()
adzuna_reported_count = None

while True:
    url = f"https://api.adzuna.com/v1/api/jobs/it/search/{page}"

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=10,
            )
            break
        except requests.exceptions.Timeout:
            print(
                f"Timeout on page {page} - "
                f"Attempt {attempt + 1}/{max_retries}"
            )
    else:
        print(
            f"Failed to retrieve page {page}. "
            f"Stopping extraction."
        )
        break

    if response.status_code != 200:
        print(
            f"Request failed on page {page}: "
            f"HTTP {response.status_code}"
        )
        break

    adzuna_data = response.json()
    adzuna_reported_count = adzuna_data["count"]
    results = adzuna_data["results"]

    if len(results) == 0:
        print(f"No results returned on page {page}.")
        break

    new_ids = 0

    for job in results:
        job_id = job["id"]

        if job_id not in seen_ids:
            seen_ids.add(job_id)
            new_ids += 1

    print(
        f"Page {page}: {len(results)} jobs - "
        f"{new_ids} new IDs"
    )

    if new_ids == 0:
        print("No new job IDs found. Stopping extraction.")
        break

    adzuna_jobs.extend(results)
    page += 1

print("Jobs downloaded:", len(adzuna_jobs))
print("Unique job IDs:", len(seen_ids))

if adzuna_reported_count is not None:
    print(
        "Total available jobs reported by Adzuna:",
        adzuna_reported_count,
    )

with open(
    "data/raw/adzuna_jobs.json",
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        adzuna_jobs,
        file,
        ensure_ascii=False,
        indent=4,
    )

print("Adzuna JSON file created.")


# FreeHire extraction
# Define API parameters
url = "https://freehire.me/api/v1/jobs/search"

params = {
    "countries": "IT",
    "is_tech": "tech",
    "limit": 100,
    "offset": 0,
}

freehire_jobs = []
max_retries = 3

while params["offset"] < 10000:
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=10,
            )
            break
        except requests.exceptions.Timeout:
            print(
                f"Timeout on offset {params['offset']} - "
                f"Attempt {attempt + 1}/{max_retries}"
            )
    else:
        print(
            f"Failed to retrieve offset {params['offset']}. "
            f"Stopping extraction."
        )
        break

    if response.status_code != 200:
        print(
            f"Request failed on offset {params['offset']}: "
            f"HTTP {response.status_code}"
        )
        break

    freehire_data = response.json()
    results = freehire_data["data"]

    print(
        f"Offset: {params['offset']}, "
        f"Jobs: {len(results)}"
    )

    # Stop pagination when the API returns no jobs
    if len(results) == 0:
        break

    freehire_jobs.extend(results)
    params["offset"] += params["limit"]

print("Total FreeHire jobs downloaded:", len(freehire_jobs))

with open(
    "data/raw/freehire_jobs.json",
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        freehire_jobs,
        file,
        indent=4,
        ensure_ascii=False,
    )

print("FreeHire JSON file created.")