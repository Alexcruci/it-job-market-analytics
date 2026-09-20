import json
import os

import psycopg
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Load the transformed dataset
with open("data/processed/jobs.json", "r", encoding="utf-8") as file:
    jobs = json.load(file)

print("Jobs loaded:", len(jobs))


# Validate that fields mapped to scalar PostgreSQL columns
# do not contain nested Python objects.
scalar_fields = [
    "source_job_id",
    "source",
    "title",
    "company",
    "location",
    "city",
    "salary_min",
    "salary_max",
    "seniority",
    "work_mode",
    "published_date",
]

for job in jobs:
    for field in scalar_fields:
        value = job[field]

        if isinstance(value, (dict, list)):
            raise ValueError(
                f"Invalid value for PostgreSQL column '{field}': "
                f"{value!r} "
                f"(source={job['source']}, "
                f"source_job_id={job['source_job_id']})"
            )

print("Scalar field validation passed")


# Extract unique skills from the dataset
unique_skills = set()

for job in jobs:
    if job["skills"] is not None:
        for skill in job["skills"]:
            unique_skills.add(skill)

print("Unique skills:", len(unique_skills))


# Connect to PostgreSQL
connection = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

cursor = connection.cursor()


try:
    # Full refresh: clear existing data and reset generated IDs.
    # The TRUNCATE is part of the same transaction as the inserts,
    # so changes are only persisted after a successful commit.
    cursor.execute(
        "TRUNCATE job_skills, jobs, skills RESTART IDENTITY;"
    )


    # Insert unique skills
    for skill in unique_skills:
        cursor.execute(
            """
            INSERT INTO skills (skill_name)
            VALUES (%s);
            """,
            (skill,),
        )


    # Build a skill_name -> skill_id mapping.
    # PostgreSQL generates skill_id values, so the mapping is needed
    # to create the job-skill relationships later.
    cursor.execute(
        "SELECT skill_id, skill_name FROM skills;"
    )

    skill_rows = cursor.fetchall()

    skill_dict = {}

    for skill_row in skill_rows:
        skill_dict[skill_row[1]] = skill_row[0]

    print("Skill mapping:", len(skill_dict))


    # Insert jobs and create their many-to-many skill relationships
    for job in jobs:
        cursor.execute(
            """
            INSERT INTO jobs (
                source_job_id,
                source,
                title,
                company,
                location,
                city,
                salary_min,
                salary_max,
                seniority,
                work_mode,
                published_date
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING job_id;
            """,
            (
                job["source_job_id"],
                job["source"],
                job["title"],
                job["company"],
                job["location"],
                job["city"],
                job["salary_min"],
                job["salary_max"],
                job["seniority"],
                job["work_mode"],
                job["published_date"],
            ),
        )

        # Retrieve the PostgreSQL-generated job ID
        job_id = cursor.fetchone()[0]

        # Create job-skill relationships
        if job["skills"] is not None:
            for skill in job["skills"]:
                skill_id = skill_dict[skill]

                cursor.execute(
                    """
                    INSERT INTO job_skills (job_id, skill_id)
                    VALUES (%s, %s);
                    """,
                    (job_id, skill_id),
                )


    # Validate the loaded data before committing
    cursor.execute("SELECT COUNT(*) FROM jobs;")
    job_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM skills;")
    skills_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM job_skills;")
    job_skills_count = cursor.fetchone()[0]

    print("Jobs inserted:", job_count)
    print("Skills inserted:", skills_count)
    print(
        "Job-skill relationships inserted:",
        job_skills_count,
    )


    # Persist the complete load only after all operations succeed
    connection.commit()

    print("Database load completed successfully.")


except Exception:
    # Preserve the previous database state if the load fails
    connection.rollback()
    raise


finally:
    # Release database resources
    cursor.close()
    connection.close()