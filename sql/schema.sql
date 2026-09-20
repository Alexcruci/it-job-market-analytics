CREATE TABLE jobs (
    job_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_job_id TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    city TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    seniority TEXT,
    work_mode TEXT,
    published_date DATE NOT NULL,
    UNIQUE (source, source_job_id)
);

CREATE TABLE skills (
    skill_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE
);

CREATE TABLE job_skills (
    job_id INTEGER REFERENCES jobs(job_id),
    skill_id INTEGER REFERENCES skills(skill_id),
    PRIMARY KEY (job_id, skill_id)
);