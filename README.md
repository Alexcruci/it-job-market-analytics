# IT Job Market Data Pipeline

An end-to-end Data Engineering project that collects technology job postings relevant to the Italian market, integrates heterogeneous API data, validates and transforms it, loads it into PostgreSQL, and analyzes the resulting dataset with SQL.

The main goal of the project is not simply to analyze an existing dataset, but to build the pipeline that creates it.

## Project Status

**Core data pipeline and SQL analysis complete. Power BI visualization is the next milestone.**

Current database snapshot:

| Metric | Value |
| --- | ---: |
| Job postings | 13,161 |
| Adzuna jobs | 3,161 |
| FreeHire jobs | 10,000 |
| Unique skills | 774 |
| Job-skill relationships | 82,262 |

---

## Architecture

```text
External APIs
     │
     ▼
Python Extraction
     │
     ▼
Raw JSON
     │
     ▼
Python / Pandas Transformation
     │
     ▼
Processed JSON
     │
     ▼
PostgreSQL
     │
     ├── Data Profiling
     │
     └── SQL Analysis
              │
              ▼
           Power BI
           (planned)
```

The pipeline separates ingestion, transformation, storage, and analysis so that each stage can be rerun and debugged independently.

---

## Data Sources

### Adzuna

Adzuna is used to collect a broad sample of IT job postings from Italy.

The extraction layer handles pagination, request timeouts, retries, HTTP response validation, and detection of repeated pages through source job IDs.

A current extraction collected:

| Stage | Records |
| --- | ---: |
| Raw API records | 5,000 |
| Unique source IDs before service-request filtering | 4,613 |
| Final jobs after filtering and deduplication | 3,161 |

### FreeHire

FreeHire provides technology-related job postings associated with Italy and exposes additional structured fields such as skills, seniority, work mode, and city information.

The current extraction collects the first 10,000 records allowed by the API's deep-pagination constraint.

| Stage | Records |
| --- | ---: |
| Raw API records | 10,000 |
| Final records after deduplication | 10,000 |

The two APIs expose similar concepts through different schemas and levels of completeness. The transformation layer maps them into a shared representation.

---

## Extraction

Implemented in:

```text
src/extract.py
```

The extraction layer is responsible for:

- calling the external APIs;
- handling source-specific pagination;
- applying request timeouts and retry logic;
- validating HTTP responses;
- detecting Adzuna pagination saturation through job IDs;
- preserving the collected API records as raw JSON.

Raw data is stored before transformation:

```text
data/raw/
├── adzuna_jobs.json
└── freehire_jobs.json
```

Raw data is intentionally preserved rather than cleaned during ingestion. This allows transformation logic to be rerun without repeatedly calling the APIs and keeps source data available for debugging.

---

## Transformation

Implemented in:

```text
src/transform.py
```

Both sources are mapped into the following common schema:

```text
source_job_id
source
title
company
location
city
salary_min
salary_max
skills
seniority
work_mode
published_date
```

The transformation layer performs:

- source-specific field mapping;
- within-source deduplication;
- missing-value normalization;
- conservative city derivation;
- publication-date parsing;
- salary-range validation;
- categorical validation;
- required-field validation;
- integration of both sources into one processed dataset.

The resulting dataset is stored in:

```text
data/processed/jobs.json
```

### Source Identity

Each record retains:

```text
(source, source_job_id)
```

as its source-level identity.

Version 1 performs deduplication within each source only. It does not attempt cross-source entity resolution because determining whether two postings from different providers represent the same real-world vacancy would require additional matching logic and assumptions.

---

## Data Quality Findings

### Non-job Adzuna Records

SQL profiling revealed an unexpected concentration of historical Adzuna records from a company named `Ernesto`.

Investigation showed that 1,452 unique records were customer service requests rather than job vacancies. They shared both:

```text
company = "Ernesto"
```

and titles beginning with:

```text
"I nostri clienti hanno richiesto"
```

A conservative filtering rule was added to the transformation layer using both conditions.

This rule was introduced only after the anomaly was discovered through post-load SQL profiling.

### Location and City

Raw location values have inconsistent granularity across the two sources.

The pipeline therefore preserves the original `location` field and derives a separate `city` field for geographic analysis.

FreeHire exposes a structured `cities` list. A city is accepted only when exactly one usable city is available.

Adzuna does not expose an equivalent structured city field, so the first component of its location display value is used only when it does not represent a country, region, or province.

Known source inconsistencies are normalized conservatively, while ambiguous locations remain missing rather than being guessed.

After normalization, 3,824 of the 13,161 records do not have a derived city.

### Salary

Salary data is preserved as provided by each source.

Profiling showed both limited coverage and values whose periodicity or semantics cannot be reliably inferred from the available fields.

For that reason, salary analysis is intentionally excluded from version 1 rather than applying arbitrary normalization rules.

### Uneven Field Coverage

Structured fields are not available uniformly across sources.

In the current dataset:

- Adzuna does not provide structured skills, seniority, or work-mode data used by the analytical layer;
- FreeHire provides structured skills for 9,036 of its 10,000 records;
- seniority and work-mode data are available only for subsets of FreeHire records.

Analyses using these fields therefore describe the subset where the relevant structured data is available, not the entire Italian IT job market.

---

## PostgreSQL Data Model

The database schema is defined in:

```text
sql/schema.sql
```

and loaded by:

```text
src/load.py
```

The relational model contains three tables:

```text
jobs
 ├── job_id (PK)
 ├── source_job_id
 ├── source
 ├── title
 ├── company
 ├── location
 ├── city
 ├── salary_min
 ├── salary_max
 ├── seniority
 ├── work_mode
 └── published_date

skills
 ├── skill_id (PK)
 └── skill_name (UNIQUE)

job_skills
 ├── job_id (PK, FK)
 └── skill_id (PK, FK)
```

A job can contain many skills and the same skill can belong to many jobs.

This is represented as a many-to-many relationship through the `job_skills` junction table rather than storing skill lists directly inside `jobs`.

The pair:

```text
(source, source_job_id)
```

is also constrained to be unique.

---

## Loading Strategy

Version 1 uses a full-refresh load.

Before loading the processed dataset, PostgreSQL executes:

```sql
TRUNCATE job_skills, jobs, skills RESTART IDENTITY;
```

The refresh and all subsequent inserts execute inside the same transaction.

The transaction is committed only after the complete load succeeds and row counts have been validated. If an exception occurs, the transaction is rolled back.

The loader also validates that fields mapped to scalar PostgreSQL columns do not contain nested Python objects before inserting data.

Current load result:

| Table | Rows |
| --- | ---: |
| `jobs` | 13,161 |
| `skills` | 774 |
| `job_skills` | 82,262 |

---

## SQL Profiling

Data profiling is stored in:

```text
sql/data_profiling.sql
```

Profiling covers:

| Area | Purpose |
| --- | --- |
| Source composition | Understand dataset balance |
| Missing values | Measure field coverage by source |
| Duplicate IDs | Validate source-level uniqueness |
| Seniority | Inspect available categories |
| Work mode | Inspect available categories |
| Publication dates | Understand temporal coverage |
| Salary | Measure coverage and inspect suspicious values |
| Skills | Measure structured skill coverage by source |

Profiling is treated separately from analytical SQL.

Its purpose is to understand what the dataset can reliably support before drawing conclusions from it.

---

## SQL Analysis

Analytical queries are stored in:

```text
sql/analysis.sql
```

The current analytical layer includes:

| Analysis | Question |
| --- | --- |
| Top cities | Where are the most postings located? |
| Top skills | Which structured skills appear most frequently? |
| Work-mode distribution | How are hybrid, onsite, and remote postings distributed? |
| Seniority distribution | How are available seniority categories distributed? |
| Junior skills | Which skills appear most frequently in junior postings? |
| Junior vs Senior skills | How does skill prevalence differ by seniority? |
| Work mode by seniority | Does work-mode distribution differ between junior and senior postings? |
| Skill co-occurrence | Which skill pairs most frequently appear in the same posting? |

The queries use relational and analytical SQL techniques including:

```text
JOIN
many-to-many relationships
COUNT(DISTINCT ...)
FILTER
CTEs
window functions
PARTITION BY
CROSS JOIN
self-joins
```

### Selected Findings

The current snapshot shows:

| Finding | Result |
| --- | --- |
| Most frequent derived city | Milano — 2,845 postings |
| Most frequent structured skill | AI — 3,410 postings |
| Other frequent skills | Cloud 2,928 · Java 2,359 · SQL 2,304 · Python 2,259 |
| Most frequent skill pair | AI + Cloud — 1,436 postings |
| Python + AI co-occurrence | 1,175 postings |

Work mode also differs substantially between the available Junior and Senior subsets:

| Seniority | Hybrid | Onsite | Remote |
| --- | ---: | ---: | ---: |
| Junior | 54.43% | 42.41% | 3.16% |
| Senior | 46.98% | 28.87% | 24.15% |

These percentages are calculated only from postings where both seniority and work-mode data are available: 158 Junior postings and 530 Senior postings.

They should therefore be interpreted as characteristics of the available dataset, not as estimates for the entire Italian job market.

---

## Project Structure

```text
it-job-market-analytics/
│
├── src/
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── sql/
│   ├── schema.sql
│   ├── data_profiling.sql
│   └── analysis.sql
│
├── data/
│   ├── raw/
│   └── processed/
│
├── requirements.txt
├── .gitignore
└── README.md
```

Raw and processed datasets are excluded from Git because they are generated pipeline outputs.

---

## Running the Project

### Requirements

The project requires:

```text
Python
PostgreSQL
Adzuna API credentials
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file containing:

```env
ADZUNA_APP_ID=
ADZUNA_APP_KEY=

DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=it_job_market
DB_USER=postgres
DB_PASSWORD=
```

Create the PostgreSQL database and apply:

```text
sql/schema.sql
```

Then execute the pipeline in order:

```bash
python src/extract.py
python src/transform.py
python src/load.py
```

The SQL profiling and analytical queries can then be executed against the populated PostgreSQL database.

---

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Pipeline implementation |
| Requests | API ingestion |
| Pandas | Transformation and validation |
| JSON | Raw and processed persistence |
| PostgreSQL | Relational storage |
| Psycopg | Python/PostgreSQL integration |
| SQL | Profiling and analysis |
| python-dotenv | Environment configuration |
| Git / GitHub | Version control and documentation |
| Power BI | Visualization — next milestone |

---

## Key Engineering Decisions

| Decision | Reason |
| --- | --- |
| Preserve raw API responses | Keep ingestion reproducible and transformations debuggable |
| Separate extraction and transformation | Keep pipeline responsibilities explicit |
| Use source-specific ingestion logic | The APIs expose different schemas and pagination behavior |
| Deduplicate after extraction | Raw data should represent what was actually collected |
| Preserve `(source, source_job_id)` | External IDs belong to separate source namespaces |
| Avoid cross-source deduplication in v1 | Reliable entity resolution requires additional assumptions |
| Normalize skills relationally | Jobs and skills form a genuine many-to-many relationship |
| Preserve missing data | Missing information is preferable to fabricated values |
| Derive city conservatively | Raw location values have inconsistent granularity |
| Exclude salary analysis | Current salary coverage and semantics are not reliable enough |
| Avoid temporal trend claims | The dataset is a current snapshot with uneven historical coverage |
| Use full-refresh loading | The dataset is small enough that incremental state is unnecessary in v1 |
| Use a transaction for loading | Prevent partially refreshed database states |
| Avoid unnecessary technologies | New tools are added only when they solve a concrete problem |

---

## Current Limitations

The current dataset is a practical engineering dataset, not a statistically representative sample of the entire Italian IT labour market.

Important limitations include:

- different field coverage between Adzuna and FreeHire;
- structured skill data primarily coming from FreeHire;
- incomplete seniority and work-mode coverage;
- incomplete and semantically inconsistent salary data;
- conservative city derivation with missing values retained when location is ambiguous;
- no cross-source entity resolution;
- FreeHire extraction limited to the first 10,000 records allowed by its deep-pagination constraint;
- no historical snapshot collection yet.

These limitations are treated as part of the analytical context rather than hidden through aggressive cleaning.

---

## Roadmap

| Milestone | Status |
| --- | :---: |
| API investigation | ✅ |
| Multi-source extraction | ✅ |
| Raw data persistence | ✅ |
| Transformation and validation | ✅ |
| Data-quality filtering | ✅ |
| PostgreSQL relational model | ✅ |
| Transactional database loading | ✅ |
| SQL data profiling | ✅ |
| SQL analysis | ✅ |
| Power BI dashboard | 🚧 |
| Final screenshots and documentation | 📋 |
| Automated tests | 📋 |
| Docker evaluation | 📋 |

---

## Next Step

The next milestone is **Power BI**.

The dashboard will visualize the analytical questions already validated through SQL rather than introducing new claims that the underlying dataset cannot support.

The project will then receive a final documentation and reproducibility pass before version 1 is considered complete.