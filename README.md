# Project Zero — IT Job Market Data Pipeline

An end-to-end Data Engineering project that collects technology job postings relevant to the Italian market, transforms heterogeneous API data into a shared schema, validates data quality, loads the resulting dataset into PostgreSQL, analyzes it with SQL, and presents selected findings through Power BI.

The project was built from scratch as a portfolio project to practice the complete lifecycle of a data pipeline rather than analyzing a pre-existing dataset.

The completed Version 2 provides a reproducible local Docker environment and a validated Azure deployment: a manually triggered Azure Container Apps Job pulls the ETL image from Azure Container Registry and populates Azure Database for PostgreSQL directly from the APIs. The final cloud run was validated on September 22, 2026.

---

## Contents

- [Project status](#project-status)
- [Dashboard](#dashboard)
- [Architecture](#architecture)
- [Data sources](#data-sources), [extraction](#extraction), and [transformation](#transformation)
- [Data quality findings](#data-quality-findings)
- [PostgreSQL data model](#postgresql-data-model) and [loading strategy](#loading-strategy)
- [Pipeline failure safety](#pipeline-failure-safety)
- [SQL profiling](#sql-profiling) and [analysis](#sql-analysis)
- [Project structure](#project-structure)
- [Run locally with Docker](#running-the-project)
- [Run without Docker](#local-execution-without-docker)
- [Run on Azure](#running-on-azure)
- [End-to-end validation](#end-to-end-validation)
- [Technology stack](#technology-stack) and [engineering decisions](#key-engineering-decisions)
- [Lessons learned](#what-i-learned--challenges-and-solutions)
- [Limitations](#current-limitations) and [version history](#version-history)

---
## Project Status

### Version 1 — Complete

Version 1 implements the complete local pipeline:

```text
External APIs
      ↓
Python Extraction
      ↓
Raw JSON
      ↓
Transformation & Validation
      ↓
Processed JSON
      ↓
PostgreSQL
      ↓
SQL Profiling & Analysis
      ↓
Power BI
```

The Version 1 reference database contains:

| Metric | Value |
| --- | ---: |
| Job postings | 13,161 |
| Adzuna jobs | 3,161 |
| FreeHire jobs | 10,000 |
| Unique skills | 774 |
| Job-skill relationships | 82,262 |

Because the APIs expose live data, new pipeline runs can produce different record counts.

### Version 2 — Complete

Version 2 focuses on making the pipeline reproducible and deployable.

The Docker milestone is complete:

- Python ETL containerized;
- PostgreSQL containerized;
- multi-service orchestration with Docker Compose;
- persistent PostgreSQL storage;
- automatic schema initialization;
- PostgreSQL health checks;
- environment-based configuration;
- reproducible dependency versions;
- automatic `extract → transform → load` execution;
- safe failure propagation;
- validated fresh-clone execution.

The Azure milestone is also complete:

- ETL image published to Azure Container Registry (ACR);
- manual Azure Container Apps Job in a Workload Profiles environment;
- user-assigned managed identity with `AcrPull` for the private image;
- API credentials and database password supplied through Job secrets;
- repeatable schema bootstrap through `src/init_db.py`;
- full cloud execution against Azure Database for PostgreSQL;
- final SQL checks confirming both sources and populated relational tables.

| Final Azure validation — September 22, 2026 | Rows |
| --- | ---: |
| `jobs` | 12,718 |
| Adzuna jobs | 2,718 |
| FreeHire jobs | 10,000 |
| `skills` | 775 |
| `job_skills` | 86,395 |

These are observed results from one run, not fixed expected counts. The Version 1 findings and dashboard below refer to the earlier snapshot. The cloud validation did not establish that the Power BI report had been refreshed from Azure.

---

## Dashboard

The Version 1 dataset is explored through a two-page Power BI report.

### Overview

The first page provides a high-level view of the dataset, including:

- job-posting count;
- source composition;
- seniority distribution;
- work-mode distribution;
- most frequent structured skills;
- most frequent derived cities.

![Power BI dashboard overview](docs/images/overview.jpg)

### Junior vs Senior

The second page compares Junior and Senior postings across:

- work-mode distribution;
- structured skill prevalence.

![Junior vs Senior analysis](docs/images/junior_vs_senior.jpg)

The report is stored in:

```text
powerbi/it_job_market_dashboard.pbix
```

Analyses involving skills, seniority, or work mode use only records where the relevant structured fields are available.

The dashboard should therefore be interpreted as an analysis of the collected dataset rather than a statistically representative estimate of the entire Italian technology labour market.

---

## Architecture

### Data Pipeline

```text
                 External APIs
                /             \
               /               \
          Adzuna              FreeHire
               \               /
                \             /
                 ▼           ▼
                   Extraction
                       │
                       ▼
                    Raw JSON
                       │
                       ▼
             Transformation Layer
                       │
              Cleaning & Validation
                       │
                       ▼
                 Processed JSON
                       │
                       ▼
                   PostgreSQL
                  /          \
                 /            \
                ▼              ▼
         SQL Profiling     SQL Analysis
                                │
                                ▼
                             Power BI
```

The pipeline separates ingestion, transformation, storage, analysis, and visualization so that each stage can be inspected and executed independently.

---

### Docker Architecture

Version 2 packages the runtime environment with Docker.

```text
                         Docker Compose
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
         ETL Container                 PostgreSQL Container
       Python 3.14.7                     PostgreSQL 18.6
               │                               │
               │        Docker Network         │
               └──────────────────────────────►│
                                               │
                                               ▼
                                      PostgreSQL Volume
                                       persistent state

               ▲
               │
         Bind Mount
               │
               ▼
        Host ./data/
```

The ETL and database run as separate services.

The ETL container is temporary and can be recreated for every pipeline run.

PostgreSQL state is stored in a Docker-managed named volume so that destroying and recreating the database container does not destroy the database.

Raw and processed JSON files remain accessible on the host through a bind mount.

---

### Azure Architecture

```text
Build and publish                       Cloud execution (manual trigger)

Repository + Dockerfile                 Azure Container Apps Job
          │                               │ pulls private image
          ▼                               ▼
Docker ETL image ──push──► Azure Container Registry
                                          │
                                 ETL container starts
                                          │
                                    init_db.py
                                          │
Adzuna + FreeHire APIs ───────────────► extract.py
                                          │
                                       Raw JSON
                                          │
                                     transform.py
                                          │
                                    Processed JSON
                                          │
                                       load.py
                                          │
                                          ▼
                              Azure Database for PostgreSQL
                                  jobs / skills / job_skills
```

ACR stores the executable image; it is not a data-processing stage. The Job runs the Python pipeline, while PostgreSQL stores the final relational dataset. A user-assigned managed identity authorizes image pulls. Database access uses PostgreSQL credentials supplied separately through Job secrets.

The validated environment used Workload Profiles with Consumption, in Spain Central. Azure PostgreSQL reported version 16.15 during validation; the local Compose database uses PostgreSQL 18.6. These are distinct deployments of the same project schema, not identical database runtimes.

Unlike local Compose, the cloud Job has no host bind mount for `data/`. Raw and processed JSON are intermediate files inside its container. No durable cloud archive of those files was configured. The final database is persisted by the managed PostgreSQL service.

The final ETL ran in Azure without a local database dump or a locally executed Python pipeline. Power BI remains a separate desktop analytical layer.

---
## Data Sources

### Adzuna

Adzuna provides a broad sample of IT job postings from the Italian market.

The extraction layer handles:

- API authentication;
- pagination;
- request timeouts;
- retries;
- HTTP response validation;
- transient HTTP failures;
- repeated job IDs across pages;
- pagination saturation.

Transient responses currently retried include:

```text
429
502
503
504
```

If extraction still fails after the configured retry attempts, the script terminates with an error.

This behavior is important because an incomplete extraction must not silently continue into transformation and database loading.

Adzuna can also return repeated records across pages. Source job IDs are therefore tracked during extraction.

If a page contains no previously unseen IDs, extraction stops rather than continuing indefinitely through duplicated pages.

---

### FreeHire

FreeHire provides technology-related job postings associated with Italy and exposes additional structured information such as:

- skills;
- seniority;
- work mode;
- city information.

The current extraction collects records in batches of 100 up to the first 10,000 records supported by the API's deep-pagination constraint.

---

### Heterogeneous Source Schemas

The two APIs describe similar concepts using different structures and different levels of completeness.

The extraction layer preserves each source independently.

The transformation layer is responsible for converting both sources into a common schema.

---

## Extraction

Extraction is implemented in:

```text
src/extract.py
```

The extraction layer is responsible for:

- requesting data from each API;
- handling source-specific pagination;
- retrying temporary failures;
- validating HTTP responses;
- detecting repeated source IDs;
- preserving API responses as raw JSON.

Generated raw files are stored in:

```text
data/raw/
├── adzuna_jobs.json
└── freehire_jobs.json
```

Raw records are preserved before cleaning.

This allows transformation logic to be rerun without repeatedly calling external APIs and keeps the original collected data available for debugging.

If the required data directories do not exist, the pipeline creates them automatically.

---

## Transformation

Transformation is implemented in:

```text
src/transform.py
```

Both sources are mapped to the following common representation:

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
- publication-date parsing;
- salary-range validation;
- categorical validation;
- city derivation and normalization;
- required-field validation;
- known non-job record filtering;
- integration of both sources.

The final processed dataset is written to:

```text
data/processed/jobs.json
```

---

### Source Identity

Each job retains the pair:

```text
(source, source_job_id)
```

as its source-level identity.

External IDs are not assumed to be globally unique because different providers operate in separate namespaces.

The pipeline performs deduplication within each source.

Cross-source entity resolution is intentionally not performed because determining whether two postings from different APIs represent the same real-world vacancy would require additional matching logic and assumptions.

---

## Data Quality Findings

Data profiling is treated as part of the pipeline development process rather than only as a final analytical step.

Several transformation rules were introduced only after anomalies were discovered in the loaded dataset.

---

### Non-job Adzuna Records

SQL profiling revealed an unexpected historical concentration of Adzuna records associated with a company named:

```text
Ernesto
```

Investigation showed that these records were customer service requests rather than employment vacancies.

They shared both:

```text
company = "Ernesto"
```

and titles beginning with:

```text
"I nostri clienti hanno richiesto"
```

A conservative filter was introduced using both conditions.

The rule deliberately avoids broader keyword-based filtering that could accidentally remove legitimate jobs.

This issue was discovered after the data had already been loaded and profiled, producing the feedback loop:

```text
ETL
 ↓
PostgreSQL
 ↓
Profiling
 ↓
Data-quality anomaly
 ↓
Transformation fix
 ↓
Reload
 ↓
Validation
```

---

### Location and City

Location values have inconsistent granularity across providers.

The pipeline therefore preserves the raw:

```text
location
```

while deriving a separate:

```text
city
```

field for analysis.

FreeHire exposes structured city information.

A city is accepted only when exactly one usable city is available.

Adzuna does not expose an equivalent structured city field, so a conservative heuristic is applied to the displayed location.

Ambiguous values are kept missing rather than guessed.

---

### BI Validation Feedback Loop

Power BI validation exposed a discrepancy between a dashboard city count and an exact PostgreSQL query.

Further profiling identified case variants such as:

```text
Torino
torino
```

Rather than correcting the visualization, city normalization was fixed upstream in the transformation layer.

The pipeline was then rerun and both PostgreSQL and Power BI produced matching results.

This reinforced a general project rule:

> Data-quality problems should be corrected as far upstream as reasonably possible rather than hidden in downstream analysis.

---

### Salary

Salary values are preserved when available.

However, coverage is limited and the available source fields do not always provide enough information to determine the meaning or periodicity of the values safely.

Salary analysis is therefore intentionally excluded from the Version 1 dashboard rather than applying arbitrary normalization assumptions.

---

### Uneven Field Coverage

Structured fields are not available uniformly across sources.

In particular:

- structured skill coverage differs significantly between providers;
- seniority is available only for a subset of records;
- work mode is available only for a subset of records;
- salary coverage is incomplete;
- geographic precision varies between sources.

Analyses involving these fields describe only the subset for which usable data exists.

---

## PostgreSQL Data Model

The relational schema is defined in:

```text
sql/schema.sql
```

The database contains three tables:

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

Jobs and skills form a many-to-many relationship.

A job can contain multiple skills and the same skill can appear in multiple jobs.

The relationship is therefore represented through the junction table:

```text
job_skills
```

rather than storing skill arrays directly in the `jobs` table.

The pair:

```text
(source, source_job_id)
```

is constrained to be unique.

---

## Database Initialization

When using Docker Compose, the PostgreSQL schema is initialized automatically.

The repository file:

```text
sql/schema.sql
```

is mounted inside the PostgreSQL container at:

```text
/docker-entrypoint-initdb.d/01-schema.sql
```

The official PostgreSQL image executes initialization scripts in this directory when a new empty database volume is created.

This allows a fresh project environment to create its database schema without manually entering PostgreSQL or executing SQL commands.

Initialization scripts are not rerun when an existing PostgreSQL volume is reused.

For Azure and standalone image execution, `src/init_db.py` reads the same `sql/schema.sql` from the image and applies it to the database selected by environment variables. The schema uses `CREATE TABLE IF NOT EXISTS`; running initialization twice was verified successfully. This bootstraps tables in an existing database; it does not provision an Azure server, create the database itself, or provide a schema-migration system.

---

## Loading Strategy

Loading is implemented in:

```text
src/load.py
```

The project currently uses a full-refresh strategy.

Before loading the processed dataset, PostgreSQL executes:

```sql
TRUNCATE job_skills, jobs, skills RESTART IDENTITY;
```

The refresh and subsequent inserts execute inside the same database transaction.

The transaction is committed only after the load completes successfully.

If an exception occurs, the transaction is rolled back.

This prevents the database from being left in a partially refreshed state.

The loader also validates fields mapped to scalar PostgreSQL columns before insertion.

---

## Pipeline Failure Safety

The local Compose command executes:

```text
extract
   &&
transform
   &&
load
```

The shell `&&` operator means that each stage runs only when the previous stage exits successfully.

Extraction errors therefore propagate as non-zero process exit codes.

The resulting behavior is:

```text
Successful extraction
        ↓
Transformation
        ↓
Load
```

while:

```text
Failed extraction
        ↓
Pipeline stops
        ↓
Transformation not executed
        ↓
Load not executed
        ↓
Existing database remains unchanged
```

This behavior was explicitly tested using invalid API credentials.

The standalone image used by Azure adds schema initialization before the same ETL sequence:

```dockerfile
CMD ["sh", "-c", "python src/init_db.py && python src/extract.py && python src/transform.py && python src/load.py"]
```

Compose overrides this default because its PostgreSQL service handles first-time schema initialization. In either path, later stages run only if preceding stages return success. This protects against reported process failures; it does not prove that a successful process produced correct data. SQL validation is still required.

---

## SQL Profiling

Profiling queries are stored in:

```text
sql/data_profiling.sql
```

Profiling covers areas including:

| Area | Purpose |
| --- | --- |
| Source composition | Understand dataset balance |
| Missing values | Measure field coverage |
| Duplicate IDs | Validate source identity |
| Seniority | Inspect available categories |
| Work mode | Inspect available categories |
| Publication dates | Inspect temporal coverage |
| Salary | Measure coverage and suspicious values |
| Skills | Measure structured skill coverage |

Profiling is kept separate from analytical SQL.

Its purpose is to understand what the dataset can reliably support before drawing conclusions from it.

---

## SQL Analysis

Analytical queries are stored in:

```text
sql/analysis.sql
```

The analysis includes:

| Analysis | Question |
| --- | --- |
| Top cities | Where are the most postings located? |
| Top skills | Which structured skills appear most frequently? |
| Work-mode distribution | How are hybrid, onsite, and remote postings distributed? |
| Seniority distribution | How are available seniority categories distributed? |
| Junior skills | Which skills appear most frequently in junior postings? |
| Junior vs Senior skills | How does skill prevalence differ by seniority? |
| Work mode by seniority | Does work-mode distribution differ between junior and senior jobs? |
| Skill co-occurrence | Which skill pairs most frequently appear together? |

The SQL layer exercises:

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

---

### Selected Version 1 Findings

The frozen Version 1 snapshot produced the following results:

| Finding | Result |
| --- | ---: |
| Most frequent derived city | Milano — 2,845 postings |
| Most frequent structured skill | AI — 3,410 postings |
| Cloud | 2,928 postings |
| Java | 2,359 postings |
| SQL | 2,304 postings |
| Python | 2,259 postings |
| Most frequent skill pair | AI + Cloud — 1,436 postings |
| Python + AI | 1,175 postings |

The available Junior and Senior subsets also showed different work-mode distributions:

| Seniority | Hybrid | Onsite | Remote |
| --- | ---: | ---: | ---: |
| Junior | 54.43% | 42.41% | 3.16% |
| Senior | 46.98% | 28.87% | 24.15% |

These percentages refer only to records where both seniority and work-mode information were available.

They are not population-level estimates of the Italian job market.

---

## Power BI

Power BI uses the PostgreSQL relational model as its analytical source.

The model imports:

```text
jobs
skills
job_skills
```

with one-to-many relationships from both `jobs` and `skills` to the `job_skills` junction table.

The current report contains two pages.

### Overview

Includes:

- job-posting count;
- number of sources;
- number of unique structured skills;
- seniority distribution;
- work-mode distribution;
- top structured skills;
- top derived cities.

### Junior vs Senior

Compares:

- work-mode distribution;
- structured skill prevalence.

Power BI is intentionally not used to compensate for data-quality issues that can be corrected upstream.

---

## Project Structure

```text
it-job-market-analytics/
│
├── src/
│   ├── init_db.py
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── sql/
│   ├── schema.sql
│   ├── data_profiling.sql
│   └── analysis.sql
│
├── powerbi/
│   └── it_job_market_dashboard.pbix
│
├── docs/
│   └── images/
│       ├── overview.jpg
│       └── junior_vs_senior.jpg
│
├── data/
│   ├── raw/
│   └── processed/
│
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

Raw and processed datasets are generated at runtime and are not committed to Git.

The real `.env` file is also excluded from version control.

`.env.example` documents the required configuration without exposing credentials.

---

## Running the Project

### Recommended Method — Docker Compose

Docker Compose is the recommended way to run the project.

#### Requirements

You need:

```text
Git
Docker
Docker Compose
Adzuna API credentials
```

A local Python installation and local PostgreSQL installation are not required.

---

### 1. Clone the Repository

The completed Docker/Azure work was developed on `v2-docker-azure`:

```bash
git clone --branch v2-docker-azure https://github.com/Alexcruci/it-job-market-analytics.git
cd it-job-market-analytics
```

---

### 2. Create the Environment File

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure `.env`:

```env
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=it_job_market
DB_USER=postgres
DB_PASSWORD=your_password
```

`DB_HOST` and `DB_PORT` describe host-side access.

Inside the Docker network, Compose overrides them for the ETL service so that PostgreSQL is reached through:

```text
postgres:5432
```

---

### 3. Run the Complete Pipeline

```bash
docker compose run --rm etl
```

On the first execution Docker Compose will:

```text
build ETL image
      ↓
create Docker network
      ↓
create PostgreSQL volume
      ↓
start PostgreSQL
      ↓
initialize schema
      ↓
wait for PostgreSQL health check
      ↓
run extract.py
      ↓
run transform.py
      ↓
run load.py
```

The project has been validated using this procedure from a fresh repository clone with:

- no project virtual environment;
- no existing project database;
- no existing project Docker volume;
- no manually created Docker network;
- no local PostgreSQL setup.

---

### Running Individual Pipeline Stages

Extraction only:

```bash
docker compose run --rm etl python src/extract.py
```

Transformation only:

```bash
docker compose run --rm etl python src/transform.py
```

Loading only:

```bash
docker compose run --rm etl python src/load.py
```

These commands are useful while developing or debugging individual stages. Transformation requires the raw files from extraction; loading requires `data/processed/jobs.json` and the database schema. Running loading directly replaces the current dataset.

---

### Stopping the Environment

Stop and remove the Compose containers and network:

```bash
docker compose down
```

The PostgreSQL volume is preserved.

---

### Resetting the Database

To also delete the persistent PostgreSQL volume and its stored data (destructive reset):

```bash
docker compose down -v
```

The next run will create a new database volume and execute:

```text
sql/schema.sql
```

again automatically.

---

## Local Execution Without Docker

The pipeline can still be run directly on the host.

Requirements:

```text
Python
PostgreSQL
Adzuna API credentials
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using:

```text
.env.example
```

as the template.

Create the PostgreSQL database and apply:

```text
sql/schema.sql
```

Alternatively, apply the schema with `python src/init_db.py` after creating the database and configuring its connection.

Then execute each stage only after the previous one succeeds:

```bash
python src/extract.py
python src/transform.py
python src/load.py
```

---

## Running on Azure

The following documents the deployment used for the completed cloud milestone. Local Compose is the quickest reproduction path. Azure additionally requires a subscription, permission to create resources and role assignments, Azure CLI with the Container Apps extension, and Docker for building and publishing the image.

### 1. Prepare the Cloud Resources

Provision and configure the following resources in a region permitted by your subscription. The project used Spain Central after encountering Azure for Students region restrictions.

| Resource | Required configuration |
| --- | --- |
| Resource group | Contains the project resources |
| Azure Container Registry | Private registry for `project-zero-etl`; demonstrated setup used standard registry RBAC |
| Azure Database for PostgreSQL Flexible Server | Existing `it_job_market` database; network access from the Job and any SQL client used for validation |
| Container Apps environment | `WorkloadProfiles` mode with Consumption; verify the actual mode after creation |
| User-assigned managed identity | Assigned to the Job, with `AcrPull` scoped to the registry and selected for registry authentication |
| Container Apps Job | Manual trigger; configuration below; uses the image's default command |

Register the resource providers required by the selected Azure services before provisioning them. Subscription policy, resource-provider registration, registry authorization, and database networking are separate prerequisites: successfully creating one resource does not verify the others.

The original deployment used a client-IP firewall rule for SQL validation and an Azure-services firewall rule for Job connectivity. The latter permits a broader set of Azure origins than this project alone. Database authentication remains required. Recreating this demonstration does not establish private networking or production security hardening.

### 2. Build, Publish, and Inspect the Image

Run these PowerShell commands from the repository root, replacing the placeholders with your own resource names. Azure resource names in a new subscription need not match the original deployment.

```powershell
$registryName = "<your-acr-name>"
$registryHost = "$registryName.azurecr.io"
$resourceGroup = "<your-resource-group>"
$jobName = "<your-job-name>"
$imageRef = "${registryHost}/project-zero-etl:v2-azure"

az login
az acr login --name $registryName

docker build -t project-zero-etl:v2-azure .
docker tag project-zero-etl:v2-azure $imageRef
docker push $imageRef
docker pull $imageRef
docker inspect $imageRef --format '{{json .Config.Cmd}}'
```

Check that the inspected command contains all four scripts in order: `init_db.py`, `extract.py`, `transform.py`, and `load.py`. Stop if a build or publication step fails. Use a new explicit tag for subsequent builds; publishing source code to GitHub does not update ACR.

The final verified deployment used `project-zero-etl:v2-azure`. Local development bind mounts are not present in Azure: all required code and SQL must be included in the image.

### 3. Configure the Manual Job

Create the Job against the prepared environment and image, using these settings in the Azure portal or CLI:

| Setting | Validated value |
| --- | --- |
| Trigger | Manual |
| Container name | `etl` |
| CPU / memory | 0.5 vCPU / 1.0 GiB |
| Replica timeout | 3,600 seconds |
| Replica retry limit | 0 |
| Replica completion count | 1 |
| Parallelism | 1 |
| Command / arguments overrides | Unset; use the image's `CMD` |
| Registry authentication | User-assigned managed identity with `AcrPull` |

Set the following runtime environment variables. Configure the three sensitive values as Job secrets and reference them from environment variables; do not bake them into the image or commit them to Git.

| Environment variable | Cloud value |
| --- | --- |
| `ADZUNA_APP_ID` | Secret reference for the Adzuna application ID |
| `ADZUNA_APP_KEY` | Secret reference for the Adzuna application key |
| `DB_HOST` | Your Azure PostgreSQL server hostname |
| `DB_PORT` | `5432` |
| `DB_NAME` | `it_job_market` |
| `DB_USER` | Your PostgreSQL user |
| `DB_PASSWORD` | Secret reference for the database password |

Schema initialization runs inside the Job. The PostgreSQL server and target database must already exist and be reachable. An ACR managed identity authorizes image pulls; it does not replace the database username and password.

For an existing configured Job, update and inspect the image reference:

```powershell
az containerapp job update --name $jobName --resource-group $resourceGroup --image $imageRef
az containerapp job show --name $jobName --resource-group $resourceGroup --query "properties.template.containers[0].image" -o tsv
```

### 4. Start One Execution and Validate Its Output

First inspect existing executions. Do not start a second full refresh while another execution is running.

```powershell
az containerapp job execution list --name $jobName --resource-group $resourceGroup -o table
az containerapp job start --name $jobName --resource-group $resourceGroup
az containerapp job execution list --name $jobName --resource-group $resourceGroup -o table
```

Record the execution name returned by `start` and follow that execution. If the client reports an error or takes longer than expected, inspect the execution list before retrying: a request may already have started a Job.

After it succeeds, connect to your Azure database with a PostgreSQL client. For example, replacing both placeholders:

```powershell
psql "host=<your-server>.postgres.database.azure.com port=5432 dbname=it_job_market user=<your-db-user> sslmode=require"
```

Run the validation SQL below. A `Succeeded` execution is necessary, but the final check is whether the intended dataset was loaded.

---

## End-to-End Validation

The project was validated through manual execution, failure testing, SQL profiling, and dashboard reconciliation. There is no automated test suite.

| Check performed | Evidence / scope |
| --- | --- |
| Fresh-clone Docker execution | Image, network, volume, schema, directories, and full ETL created from the repository |
| Invalid API credentials | Extraction failed and downstream transformation/loading did not run |
| Repeatable schema bootstrap | `init_db.py` succeeded on repeated runs and from the Docker image against Azure |
| Database / BI reconciliation | City case normalization corrected upstream and matching counts verified |
| Cloud image inspection | Incorrect published image identified; corrected image inspected and deployed with `v2-azure` |
| Final cloud execution | Job succeeded; SQL returned populated tables and both API sources |

Use these queries against the database you intend to validate:

```sql
SELECT COUNT(*) AS job_count FROM jobs;
SELECT COUNT(*) AS skill_count FROM skills;
SELECT COUNT(*) AS job_skill_count FROM job_skills;

SELECT source, COUNT(*) AS job_count
FROM jobs
GROUP BY source
ORDER BY source;
```

The final Azure run returned 12,718 jobs, 775 skills, and 86,395 job-skill relationships, with 2,718 Adzuna jobs and 10,000 FreeHire jobs. The source counts sum to the total job count.

Counts establish that the tables are populated and both sources are represented; they do not prove that every record is semantically correct. Continue with `sql/data_profiling.sql` to inspect coverage, categories, dates, and source identity. Live API counts can change, so the recorded numbers are reference evidence rather than assertions for every future run.

The initial unsuccessful deployment illustrates why these checks matter: the Job reported `Succeeded`, but all three tables were empty. Inspecting the registry image revealed a build without the intended ETL command. The corrected deployment was accepted only after checking the resulting database.

---
## SQL and Power BI

Once PostgreSQL has been populated, the profiling and analytical queries can be executed from:

```text
sql/data_profiling.sql
sql/analysis.sql
```

The Power BI report can be opened from:

```text
powerbi/it_job_market_dashboard.pbix
```

Power BI Desktop may require the PostgreSQL connection to be configured for the machine running the report.

---

## Docker Implementation Details

### ETL Image

The ETL image is built from:

```text
Dockerfile
```

using:

```text
Python 3.14.7
```

The image contains:

- Python;
- project dependencies;
- ETL source code, including `init_db.py`;
- `sql/schema.sql`;
- the default initialization and ETL command.

The dependency versions used by the project are pinned in:

```text
requirements.txt
```

to improve reproducibility.

---

### PostgreSQL Service

PostgreSQL runs using:

```text
PostgreSQL 18.6
```

The database service exposes PostgreSQL to the host while also being reachable internally through the Compose network.

The ETL service accesses it using:

```text
DB_HOST=postgres
DB_PORT=5432
```

---

### PostgreSQL Health Check

The PostgreSQL service includes a health check based on:

```text
pg_isready
```

The ETL service depends on PostgreSQL reaching the:

```text
healthy
```

state.

This avoids relying on arbitrary sleep times before database operations.

---

### Persistent Database Storage

PostgreSQL uses a Docker named volume.

This separates database state from the lifecycle of an individual container.

A PostgreSQL container can therefore be removed and recreated while keeping the existing database.

---

### Bind-mounted Pipeline Data

The host directory:

```text
./data
```

is mounted inside the ETL container at:

```text
/app/data
```

This keeps raw and processed JSON files outside temporary ETL containers.

During development:

```text
./src
```

is also mounted read-only into the ETL container so that source-code changes can be tested without rebuilding the image for every modification.

---

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python 3.14.7 | ETL implementation |
| Requests | API ingestion |
| Pandas | Transformation and validation |
| JSON | Raw and processed persistence |
| PostgreSQL | Relational storage: 18.6 in Compose; Azure server reported 16.15 |
| Psycopg | Python/PostgreSQL integration |
| SQL | Profiling and analysis |
| Power BI | Visualization |
| python-dotenv | Environment configuration |
| Docker | Containerized runtime |
| Docker Compose | Local multi-service orchestration |
| Azure Container Registry | Private ETL image distribution |
| Azure Container Apps Jobs | Manual cloud batch execution |
| Azure Database for PostgreSQL | Managed cloud database |
| Managed identity and Azure RBAC | Authorize the Job to pull its image |
| Git | Version control |
| GitHub | Repository and documentation |

---

## Key Engineering Decisions

| Decision | Reason |
| --- | --- |
| Preserve raw API responses | Keep ingestion traceable and transformations rerunnable |
| Separate extraction and transformation | Maintain explicit pipeline responsibilities |
| Use source-specific extraction logic | APIs expose different schemas and pagination models |
| Track IDs during extraction and deduplicate during transformation | Stop repeated pagination and enforce within-source identity |
| Preserve `(source, source_job_id)` | Provider IDs belong to separate namespaces |
| Avoid cross-source entity resolution | Reliable matching would require additional assumptions |
| Normalize skills relationally | Jobs and skills form a genuine many-to-many relationship |
| Preserve missing data | Missing information is preferable to invented information |
| Derive cities conservatively | Location values have inconsistent granularity |
| Correct data-quality problems upstream | Downstream visualization should not hide pipeline problems |
| Exclude unreliable salary analysis | Available salary semantics are insufficient for safe normalization |
| Use a full-refresh load | Current dataset size does not require incremental loading |
| Use database transactions | Prevent partially refreshed database states |
| Separate ETL and PostgreSQL containers | Application execution and persistent database state have different lifecycles |
| Use a PostgreSQL named volume | Database data must survive container recreation |
| Use bind mounts for pipeline outputs | Raw and processed files should remain accessible on the host |
| Initialize the schema automatically | Fresh environments should not require manual SQL setup |
| Use PostgreSQL health checks | Container startup does not necessarily mean database readiness |
| Propagate extraction failures | Partial extractions must not overwrite a valid database |
| Pin runtime versions | Rebuilds should use known working versions |
| Avoid fixed container names | Reduce naming collisions; concurrent copies still require distinct host ports |
| Run a batch Job in Azure | The ETL runs to completion and does not need a continuously serving web application |
| Use managed identity for ACR | Separate image-pull permissions from database credentials |
| Deploy an explicit image tag | Make the intended build easier to inspect than a reused `latest` tag |
| Validate database outputs after execution | A successful exit code alone does not establish data correctness |
| Avoid unnecessary technologies | Tools are added only when they solve a concrete project problem |

---

## Docker Validation

The Docker setup was tested from a separate fresh clone of the repository.

The test started without:

```text
project database
project PostgreSQL volume
project Docker network
local virtual environment
generated data directories
```

Running:

```bash
docker compose run --rm etl
```

successfully:

1. built the ETL image;
2. created the Docker network;
3. created the PostgreSQL volume;
4. initialized the PostgreSQL schema;
5. waited for PostgreSQL to become healthy;
6. created the required data directories;
7. extracted API data;
8. transformed and validated the dataset;
9. loaded the data into PostgreSQL.

This test is used as the reproducibility check for the Docker milestone.

---

## What I Learned — Challenges and Solutions

This project developed from a local ETL into a reproducible containerized pipeline and a working cloud batch deployment. The most useful lessons came from discrepancies between what appeared to work and what the data or runtime actually showed.

### 1. Data Quality Rules Need Evidence

SQL profiling exposed Adzuna records from Ernesto that were service requests rather than job vacancies. I used the combination of company name and the specific title prefix to filter the known pattern instead of removing records based on broad keywords. Power BI later exposed city case variants such as `Torino` and `torino`; I corrected normalization in transformation and checked the results again in PostgreSQL and Power BI.

I learned to treat profiling and visualization as feedback into pipeline development. Preserving raw values and using conservative rules makes cleaning decisions easier to explain. Missing or ambiguous information should remain missing when there is no defensible derivation.

### 2. API Pagination and Failure Handling Are Part of Correctness

Adzuna could repeat IDs across pages and return temporary HTTP errors. Tracking previously seen IDs allowed extraction to stop when a page added no new records. Bounded retries handled selected transient responses, while exhausted retries produced an error. FreeHire's deep-pagination boundary limited extraction to 10,000 records rather than a complete inventory.

The key lesson was to distinguish a source limitation from a successful complete-market collection, and a failed extraction from an acceptable dataset. Chaining stages with `&&` and testing invalid credentials demonstrated that an extraction failure would not silently continue into a database refresh. Retry handling still does not provide checkpoint recovery between runs.

### 3. Relational Modeling and Transactions Solve Different Problems

The `(source, source_job_id)` pair preserves provider-specific identity. The `skills` table and `job_skills` junction represent a many-to-many relationship without duplicating skill definitions in each job row. A transactional full refresh keeps the replacement dataset consistent if loading fails.

I learned that these choices have separate trade-offs: source identity does not resolve duplicates across providers, and a full refresh does not preserve historical observations. The design is appropriate for the project's snapshot analysis, but it would need changes for historical or incremental ingestion.

### 4. Containers Need Explicit Networking, Readiness, and Storage

The ETL container connects to `postgres:5432` through Compose, while a host client connects through the published host port. A container's `localhost` refers to that container, so the host connection settings cannot simply be reused internally. A PostgreSQL health check establishes readiness before ETL starts.

A named volume preserves database state across container recreation; a bind mount preserves local JSON outputs. Testing from a separate fresh clone exposed whether the project depended on an existing database, virtual environment, network, or generated directory. Reproducibility means rebuilding the required environment, not merely rerunning code successfully on the development machine.

### 5. Cloud Bootstrap Must Come from the Repository

Managed PostgreSQL does not execute the local Compose initialization mount. I added `init_db.py` to read the repository schema and initialize tables in the configured database. Repeated execution and a test from inside the Docker image verified that bootstrap did not depend on a database dump or local Python.

One intermediate connection test still targeted the local database because its environment settings had not changed. Explicitly checking the target host separated “the connection works” from “the intended Azure connection works.” Runtime configuration is part of the behavior being tested.

### 6. Azure Failures Belong to Different Layers

Deployment involved Azure for Students region policies, resource-provider registration, database firewall configuration, and private-registry permissions. These required different fixes: use a permitted region, register the required providers, enable the intended database connectivity, and authorize the Job's identity to pull from ACR.

An environment was initially created in Express mode and Job creation failed with `ExpressEnvironmentResourceNotSupported`. Recreating the environment explicitly in Workload Profiles mode resolved that blocker. The lesson was to inspect the actual resource properties and error code instead of repeatedly changing unrelated ETL code.

Local `az acr login` and the cloud Job's managed identity also solve different authentication problems. Refreshing local registry authentication permits local image operations; assigning `AcrPull` to the Job's identity authorizes cloud pulls.

### 7. The Deployed Image Is a Separate Artifact

Passing the shell command through Azure CLI arguments encountered parsing errors. Defining the four-stage command in the Dockerfile gave the image an explicit default behavior and let the Job run without command overrides.

A later Job still reported success with an empty database. Comparing the local image with the image pulled from ACR showed that the registry contained an older build without that command. The fix was to tag and publish the corrected image as `v2-azure`, pull it back, inspect its command, and verify the Job's configured image before running again.

I learned that a source-code push, a local Docker rebuild, a registry push, and a Job update are separate steps. An explicit tag makes deployment easier to audit, although it is not inherently immutable. Runtime status must be checked against output data.

### 8. Operational Simplicity Has Visible Limits

A client-side start error was followed by overlapping Job executions. Because each execution can refresh the same database, the incident highlighted the need to inspect existing executions before retrying a manual trigger. One-replica parallelism does not provide a lock across separate executions.

Persistent cloud logs were disabled in the demonstrated environment. When a completed execution no longer had a replica available, logs could not provide the desired diagnostic history. This made the observability trade-off concrete: retained logs and run-level coordination would be meaningful operational improvements, even though they are outside the completed portfolio scope.

These experiences gave me concrete design choices and debugging evidence to discuss: how data is preserved, where validation happens, what makes a run reproducible, how failures propagate, and what remains outside the system's guarantees.

---
## Current Limitations

The dataset and pipeline still have several known limitations.

#### Data

- The two APIs provide different field coverage.
- Structured skills are not uniformly available.
- Seniority and work mode are incomplete.
- Salary coverage and semantics remain unreliable.
- Geographic values have inconsistent source granularity.
- Cross-source entity resolution is not implemented.
- FreeHire extraction is limited to the first 10,000 records supported by its deep-pagination behavior.
- The dataset represents pipeline snapshots rather than a historical time series.

#### Pipeline

- There is currently no automated test suite.
- Adzuna can occasionally return temporary HTTP failures.
- Retry logic mitigates temporary API errors but does not persist extraction checkpoints between runs.
- The pipeline currently performs full-refresh loading rather than incremental ingestion.
- Execution is manually triggered rather than scheduled.

#### Deployment

- Local Compose and Azure are separate execution environments; the cloud deployment was validated as a portfolio batch workload.
- Azure provisioning and deployment were performed manually; there is no documented automated infrastructure provisioning or CI/CD workflow.
- Persistent cloud log collection was disabled (`--logs-destination none`), limiting post-run debugging.
- Cloud intermediate JSON files have no configured durable storage.
- The demonstrated PostgreSQL network setup used public access and firewall rules, including access from Azure services. It is not a private-network deployment.
- The Azure-services firewall rule is broader than this project's Job or subscription; managed identity for ACR does not restrict database networking.
- The database credentials used for the demonstration were administrator credentials; a dedicated least-privilege runtime database role was not established in the validated setup.
- Multiple manually started executions can overlap. `parallelism=1` within a Job execution does not prevent separate executions from loading the same database.
- The versioned image tag identifies the intended release more clearly than `latest`, but tags can be overwritten; digest-pinned deployment was not established.
- Power BI is not containerized and remains a desktop analytical layer.

---

## Version History

### Version 1 — Complete

Version 1 established the full end-to-end data workflow.

| Milestone | Status |
| --- | :---: |
| API investigation | ✅ |
| Multi-source extraction | ✅ |
| Raw JSON persistence | ✅ |
| Transformation | ✅ |
| Data validation | ✅ |
| Data-quality filtering | ✅ |
| PostgreSQL relational model | ✅ |
| Transactional database loading | ✅ |
| SQL profiling | ✅ |
| SQL analysis | ✅ |
| Power BI dashboard | ✅ |
| Documentation | ✅ |

---

### Version 2 — Complete

#### Docker Milestone

| Milestone | Status |
| --- | :---: |
| ETL Docker image | ✅ |
| PostgreSQL container | ✅ |
| Persistent database volume | ✅ |
| Container networking | ✅ |
| Docker Compose orchestration | ✅ |
| Environment configuration | ✅ |
| Automatic schema initialization | ✅ |
| PostgreSQL health check | ✅ |
| Complete ETL command | ✅ |
| Pipeline failure propagation | ✅ |
| Runtime version pinning | ✅ |
| Fresh-clone reproducibility test | ✅ |

#### Azure Milestone

| Milestone | Status |
| --- | :---: |
| Azure architecture design | ✅ |
| Cloud resource selection | ✅ |
| Cloud deployment | ✅ |
| Cloud execution and SQL validation | ✅ |

---

## Future Improvements

Potential future iterations include:

- automated unit and integration tests;
- historical snapshot collection;
- extraction checkpointing and resume support;
- incremental loading;
- cross-source entity resolution;
- improved geographic normalization;
- improved salary normalization if source semantics allow it;
- automated scheduling;
- CI/CD;
- monitoring and structured logging;
- durable cloud intermediate storage and retained execution logs.

These are possible extensions, not implemented features or requirements for completion. The final project scope is complete: multi-source ETL, relational analytics, Power BI, reproducible Docker execution, and validated Azure execution. Version 2 completion describes the implemented milestone; it does not assert that a GitHub `v2.0.0` tag or release has already been published.