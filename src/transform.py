import json

import pandas as pd

from pathlib import Path

Path("data/processed").mkdir(parents=True, exist_ok=True)

ITALIAN_REGIONS = {
    "abruzzo",
    "basilicata",
    "calabria",
    "campania",
    "emilia-romagna",
    "emilia romagna",
    "friuli-venezia giulia",
    "friuli venezia giulia",
    "lazio",
    "liguria",
    "lombardia",
    "marche",
    "molise",
    "piemonte",
    "puglia",
    "sardegna",
    "sicilia",
    "toscana",
    "trentino-alto adige",
    "trentino alto adige",
    "umbria",
    "valle d'aosta",
    "veneto",
}

CITY_ALIASES = {
    "milan": "Milano",
    "rome": "Roma",
    "turin": "Torino",
    "florence": "Firenze",
    "naples": "Napoli",
    "padua": "Padova",
    "genoa": "Genova",
    "perm": "Parma",
    "torino": "Torino",
    "trento": "Trento",
    "gallicano nel lazio": "Gallicano nel Lazio",
    "rimini": "Rimini",
    "caldaro sulla strada del vino": "Caldaro sulla Strada del Vino",
}


def derive_freehire_city(job):
    cities = job.get("cities") or []

    if not cities:
        return None

    if len(cities) > 1:
        return None

    city = cities[0].strip()

    if not city:
        return None

    city_lower = city.lower()

    if city_lower in ITALIAN_REGIONS:
        return None

    if city_lower in {"italy", "italia"}:
        return None

    if city_lower in CITY_ALIASES:
        return CITY_ALIASES[city_lower]

    return city


def derive_adzuna_city(job):
    location = (job.get("location") or {}).get("display_name")

    if not location:
        return None

    city = location.split(",")[0].strip()

    if not city:
        return None

    city_lower = city.lower()

    if city_lower in {"italy", "italia"}:
        return None

    if city_lower in ITALIAN_REGIONS:
        return None

    if city_lower.startswith("provincia di "):
        return None

    if city_lower in CITY_ALIASES:
        return CITY_ALIASES[city_lower]

    return city


# Load raw Adzuna jobs
with open(
    "data/raw/adzuna_jobs.json",
    "r",
    encoding="utf-8",
) as file:
    adzuna_jobs = json.load(file)

print("Adzuna jobs loaded:", len(adzuna_jobs))


# Load raw FreeHire jobs
with open(
    "data/raw/freehire_jobs.json",
    "r",
    encoding="utf-8",
) as file:
    freehire_jobs = json.load(file)

print("FreeHire jobs loaded:", len(freehire_jobs))


# Transform Adzuna jobs to the common schema
transformed_adzuna_jobs = []

for job in adzuna_jobs:
    transformed_job = {
        "source_job_id": job["id"],
        "source": "adzuna",
        "title": job["title"],
        "company": job["company"].get("display_name"),
        "location": (job.get("location") or {}).get("display_name"),
        "city": derive_adzuna_city(job),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "skills": None,
        "seniority": None,
        "work_mode": None,
        "published_date": job["created"],
    }

    transformed_adzuna_jobs.append(transformed_job)


# Remove non-job Ernesto service requests identified during SQL profiling
filtered_adzuna_jobs = []

for job in transformed_adzuna_jobs:
    if not (
        job["company"] == "Ernesto"
        and job["title"].startswith(
            "I nostri clienti hanno richiesto"
        )
    ):
        filtered_adzuna_jobs.append(job)


# Deduplicate Adzuna jobs by source job ID
seen_jobs = {}

for job in filtered_adzuna_jobs:
    job_id = job["source_job_id"]

    if job_id not in seen_jobs:
        seen_jobs[job_id] = job
    elif job != seen_jobs[job_id]:
        print("Different records with same ID:")
        print(seen_jobs[job_id])
        print(job)

deduplicated_adzuna_jobs = list(seen_jobs.values())

print("Transformed Adzuna jobs:", len(transformed_adzuna_jobs))
print("Filtered Adzuna jobs:", len(filtered_adzuna_jobs))
print(
    "Adzuna service requests removed:",
    len(transformed_adzuna_jobs) - len(filtered_adzuna_jobs),
)
print("Deduplicated Adzuna jobs:", len(deduplicated_adzuna_jobs))


# Transform FreeHire jobs to the common schema
transformed_freehire_jobs = []

for job in freehire_jobs:
    transformed_job = {
        "source_job_id": job["external_id"],
        "source": "freehire",
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "city": derive_freehire_city(job),
        "salary_min": job["enrichment"].get("salary_min"),
        "salary_max": job["enrichment"].get("salary_max"),
        "skills": job.get("skills"),
        "seniority": job["enrichment"].get("seniority"),
        "work_mode": job.get("work_mode"),
        "published_date": job["posted_at"],
    }

    transformed_freehire_jobs.append(transformed_job)


# Deduplicate FreeHire jobs by source job ID
seen_freehire_jobs = {}

for job in transformed_freehire_jobs:
    job_id = job["source_job_id"]

    if job_id not in seen_freehire_jobs:
        seen_freehire_jobs[job_id] = job
    elif job != seen_freehire_jobs[job_id]:
        print("Different records with same ID:")
        print(seen_freehire_jobs[job_id])
        print(job)

deduplicated_freehire_jobs = list(
    seen_freehire_jobs.values()
)

print(
    "Transformed FreeHire jobs:",
    len(transformed_freehire_jobs),
)
print(
    "Deduplicated FreeHire jobs:",
    len(deduplicated_freehire_jobs),
)


# Combine both sources into a single dataset
clean_dataset = []
clean_dataset.extend(deduplicated_adzuna_jobs)
clean_dataset.extend(deduplicated_freehire_jobs)

print("\nFinal dataset records:", len(clean_dataset))


# Create DataFrame
df = pd.DataFrame(clean_dataset)


# Normalize empty locations as missing values
df["location"] = df["location"].replace(
    r"^\s*$",
    None,
    regex=True,
)


# Validate schema
expected_columns = [
    "source_job_id",
    "source",
    "title",
    "company",
    "location",
    "city",
    "salary_min",
    "salary_max",
    "skills",
    "seniority",
    "work_mode",
    "published_date",
]

if list(df.columns) == expected_columns:
    print("Schema validation passed")
else:
    print("Schema validation failed")


# Check missing values
print("Missing values:\n", df.isna().sum())


# Check duplicate source IDs
duplicated_records = df.duplicated(
    subset=["source", "source_job_id"]
).sum()

print("Duplicated records:", duplicated_records)


# Validate salary ranges
invalid_salary = df["salary_min"] > df["salary_max"]

print(
    "Records with invalid salary range:",
    invalid_salary.sum(),
)


# Validate source values
invalid_sources = (
    ~df["source"].isin(["adzuna", "freehire"])
).sum()

print("Records with invalid source:", invalid_sources)


# Validate work mode values when present
invalid_work_mode = (
    ~df["work_mode"].isin(["hybrid", "remote", "onsite"])
    & df["work_mode"].notna()
).sum()

print(
    "Records with invalid work mode:",
    invalid_work_mode,
)


# Validate seniority values when present
invalid_seniority = (
    ~df["seniority"].isin(
        [
            "senior",
            "junior",
            "lead",
            "staff",
            "intern",
            "middle",
            "c_level",
            "principal",
        ]
    )
    & df["seniority"].notna()
).sum()

print(
    "Records with invalid seniority:",
    invalid_seniority,
)


# Parse and validate publication dates
parsed_dates = pd.to_datetime(
    df["published_date"],
    errors="coerce",
    utc=True,
)

df["published_date"] = parsed_dates

invalid_dates = parsed_dates.isna().sum()

print(
    "Records with invalid publication date:",
    invalid_dates,
)


# Check required string fields for empty values
required_string_columns = [
    "source_job_id",
    "source",
    "title",
]

for column in required_string_columns:
    empty_values = (
        df[column]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    print(
        f"Empty values in {column}: "
        f"{empty_values}"
    )


# Report missing locations after normalization
missing_locations = df["location"].isna().sum()

print("Missing locations:", missing_locations)


# Report final record count by source
print(
    "Records by source:\n",
    df["source"].value_counts(),
)


# Save processed dataset
df.to_json(
    "data/processed/jobs.json",
    orient="records",
    date_format="iso",
    force_ascii=False,
    indent=4,
)

print("Processed dataset saved: data/processed/jobs.json")