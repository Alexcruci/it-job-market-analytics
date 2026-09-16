# 💼 IT Job Market Data Pipeline

> **An end-to-end Data Engineering project exploring the IT job market through real-world API data.**

This project collects IT job postings from multiple sources, preserves the original API responses, transforms and integrates heterogeneous data, and will ultimately load the resulting dataset into PostgreSQL for SQL analysis and Power BI visualization.

The goal is not just to analyze a dataset, but to **build the pipeline that creates it**.

> 🚧 **Project Status — Work in Progress**
>
> The **extraction and transformation layers are complete**.
>
> The pipeline currently collects data from Adzuna and FreeHire, preserves the raw API responses, transforms both sources into a common schema, validates the resulting dataset, and produces a processed JSON dataset.
>
> **PostgreSQL integration is the next development milestone**, followed by SQL analysis and visualization.

---

## 🎯 What Are We Trying to Find Out?

### Core Question

> **Which skills, technologies, roles, working conditions, salaries, and locations are most in demand in the IT job market, and how do these factors vary over time?**

The project is built around seven analytical questions:

1. Which IT roles have the highest demand?
2. Which skills and technologies are most requested for each role?
3. How do required skills change with seniority?
4. How does demand vary by geographic location?
5. How common are **Remote, Hybrid, and On-site** positions across roles and locations?
6. When salary data is available, what relationships exist between **salary, role, seniority, skills, and location**?
7. How does the IT job market evolve over time?

These questions define the analytical scope of the project and guide the transformation, data modelling, SQL analysis, and visualization stages.

> **Note:** Not every question is fully answerable with the current dataset.
>
> Some fields, such as skills, seniority, work mode, and salary information, have different levels of coverage across the two APIs. Meaningful trend analysis will also require data collected across multiple points in time.

---

## 🏗️ Pipeline Architecture

The project follows a layered architecture where each stage has a clearly defined responsibility:

```text
┌──────────────────────┐
│   External Job APIs  │
│ Adzuna  │  FreeHire  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Python Extraction   │  ✅
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     Raw JSON Data    │  ✅
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Python Transformation│  ✅
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Processed JSON Data │  ✅
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      PostgreSQL      │  🚧
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     SQL Analysis     │  📋
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       Power BI       │  📋
└──────────────────────┘
```

**Legend:** ✅ Implemented · 🚧 Next milestone · 📋 Planned

The architecture evolves only when new requirements justify it.

---

## 🌐 Data Sources

The current pipeline uses two job-market APIs.

### Adzuna

Adzuna is one of the primary sources used by the extraction layer.

The extractor handles:

- paginated HTTP requests;
- HTTP response validation;
- explicit request timeouts;
- retry handling;
- job ID tracking during pagination;
- raw JSON persistence.

A current extraction run produced:

| Metric | Result |
| --- | ---: |
| Raw records | **5,000** |
| Unique Adzuna job IDs | **4,613** |

That difference is important.

The extraction layer **does not silently remove duplicate records**. Raw data represents what was actually collected from the source. Duplicate handling is performed explicitly during transformation.

### FreeHire

FreeHire provides the second source of job-market data.

The current extraction targets technology-related job listings in Italy and handles:

- paginated API requests;
- batches of up to 100 records;
- HTTP response validation;
- request timeouts;
- retry handling;
- API pagination constraints;
- raw JSON persistence.

A current extraction run produced:

| Metric | Result |
| --- | ---: |
| Raw records | **10,000** |
| Unique source job IDs | **10,000** |

### Why Two Sources?

Using two APIs is not simply about collecting more rows.

It creates a real **data integration problem**:

```text
         ADZUNA
            │
            │ different schema
            │
            ▼
      ┌──────────┐
      │  Common  │
      │   Data   │ ─────► PostgreSQL
      │  Model   │
      └──────────┘
            ▲
            │
            │ different schema
            │
         FREEHIRE
```

Adzuna and FreeHire represent similar concepts using different fields, structures, pagination systems, and levels of completeness.

The transformation layer converts both representations into a shared schema while preserving source identity and missing information where a reliable mapping is not available.

### What Happened to Jooble?

Jooble was evaluated during the early development phase as a possible additional source.

After experimentation, it was **not retained in the current pipeline** because the returned results did not provide sufficient reliability for the intended analytical scope.

Temporary Jooble test files were subsequently removed so that the repository reflects the architecture actually being developed rather than keeping abandoned experiments as production components.

> **Engineering principle:** another API is useful only when the value it provides justifies the additional ingestion and normalization complexity.

---

## 📥 Extraction Layer

The extraction layer is the first completed component of the pipeline.

Its responsibility is deliberately narrow:

```text
API Request
    │
    ▼
Validate Response
    │
    ▼
Handle Pagination
    │
    ▼
Collect Records
    │
    ▼
Persist Raw JSON
```

The extraction logic is implemented in:

```text
src/extract.py
```

and produces:

```text
data/
└── raw/
    ├── adzuna_jobs.json
    └── freehire_jobs.json
```

### What extraction does — and does not do

| Extraction does | Extraction does **not** do |
| --- | --- |
| Call external APIs | Deduplicate records |
| Handle pagination | Normalize fields |
| Validate HTTP responses | Clean values |
| Retry transient failures | Integrate schemas |
| Preserve raw records | Load PostgreSQL |
| Save JSON files | Perform analytics |

Keeping those responsibilities separate makes each pipeline stage easier to reason about, debug, test, and modify.

---

## 🛡️ Making Extraction More Reliable

Real APIs are less predictable than local CSV files.

Requests can fail. Servers can respond slowly. Pagination rules differ between providers. Rate limits and source constraints need to be respected.

The current extraction layer therefore includes several defensive mechanisms.

**Timeouts** prevent the pipeline from waiting indefinitely for an external service.

**Retries** allow transient request failures to be attempted again instead of immediately terminating extraction.

**HTTP validation** ensures unsuccessful responses are detected before their contents are processed.

**Source-specific pagination** prevents the pipeline from assuming that every API exposes data in the same way.

These mechanisms are intentionally implemented at the ingestion boundary, where external failures first enter the pipeline.

---

## 🗃️ Why Keep Raw Data?

The project persists API responses **before transformation**:

```text
SOURCE
   │
   ▼
  RAW        ← preserve what was collected
   │
   ▼
TRANSFORM    ← clean, normalize, integrate
   │
   ▼
DATABASE
   │
   ▼
ANALYTICS
```

This separation means that:

- transformations can be rerun without calling the APIs again;
- transformation bugs do not automatically require re-extraction;
- original source records remain available for debugging;
- differences between APIs can be inspected later;
- cleaning decisions remain separate from ingestion.

It also explains why duplicates may legitimately exist in `data/raw/`.

For example:

```text
Adzuna extraction
────────────────────────────
5,000 raw records
4,613 unique source IDs
────────────────────────────
387 repeated IDs observed
```

Those records are preserved intentionally and deduplicated explicitly during transformation.

---

## 🔎 A Problem We Hit Early: What Should We Search For?

The first extraction experiments searched specifically for:

```text
Data Engineer
```

The results were relevant, but the query was too restrictive for a project intended to analyze the broader IT job market.

That exposed a classic trade-off between **precision and coverage**.

A narrow query provides higher precision but lower coverage. A broader query increases coverage but also introduces records that may later require additional filtering or classification.

For this project, the extraction strategy evolved toward broader technology-job collection.

More detailed filtering and classification can happen downstream, where the logic can be inspected, tested, and changed without repeatedly querying the APIs.

---

## 🔄 Transformation Layer

The transformation layer is implemented in:

```text
src/transform.py
```

Its purpose is to convert the two heterogeneous raw API datasets into a consistent representation suitable for downstream storage and analysis.

The transformation currently performs:

- source-specific field mapping;
- schema normalization;
- within-source deduplication using source job IDs;
- integration of Adzuna and FreeHire records;
- missing-value normalization;
- publication-date parsing and validation;
- salary-range validation;
- categorical validation;
- required-field validation;
- final dataset persistence.

### Common Schema

Both APIs are mapped to the following representation:

```text
source_job_id
source
title
company
location
salary_min
salary_max
skills
seniority
work_mode
published_date
```

The `source` field preserves the origin of each record, while `source_job_id` preserves the identifier provided by that source.

Together:

```text
(source, source_job_id)
```

form the source-level identity used by the current pipeline.

### Transformation Results

A current transformation run produces:

| Stage | Records |
| --- | ---: |
| Adzuna raw records | **5,000** |
| Adzuna after deduplication | **4,613** |
| FreeHire raw records | **10,000** |
| FreeHire after deduplication | **10,000** |
| **Final integrated dataset** | **14,613** |

The final dataset contains no duplicate `(source, source_job_id)` pairs.

### Data Validation

The transformation layer performs several sanity and data-quality checks before saving the processed dataset.

The current dataset passes validation for:

- expected schema;
- duplicate source identifiers;
- salary ranges where both bounds are available;
- allowed source values;
- allowed work-mode values;
- allowed seniority values;
- publication-date parsing;
- required identifiers and titles.

Empty or whitespace-only locations are normalized to missing values rather than being represented as valid strings.

### Source Coverage Is Not Uniform

Not every API exposes the same information.

FreeHire provides structured information for fields such as skills, seniority, and work mode, while equivalent structured fields are not consistently available from Adzuna.

The pipeline therefore **does not fabricate missing information simply to make the schemas look complete**.

For example, Adzuna skills are currently stored as missing rather than attempting unvalidated extraction from free-text descriptions.

This means downstream analyses must take field coverage into account when interpreting results.

### Salary Data

Salary values are currently preserved as provided by each source.

Exploratory validation showed values with potentially different salary periodicities or semantics. Without sufficient source metadata to normalize these values reliably, the pipeline deliberately avoids applying arbitrary transformations.

Salary normalization is therefore a documented future improvement rather than an assumption embedded in version 1.

### Deduplication Scope

Deduplication currently happens **within each source** using its source job identifier.

The pipeline does not attempt to determine whether an Adzuna posting and a FreeHire posting represent the same real-world vacancy.

That would require cross-source record linkage or entity-resolution logic based on combinations of fields such as title, company, location, and potentially description.

This additional complexity is intentionally outside the current version 1 scope.

### Processed Output

The transformed dataset is persisted as:

```text
data/
└── processed/
    └── jobs.json
```

JSON is retained for the processed layer because some fields, particularly `skills`, contain structured lists that can be represented naturally without flattening them into strings.

The current processed dataset contains:

```text
14,613 records
```

---

## 🐘 PostgreSQL

> 🚧 **Next development milestone**

The next stage is to load the transformed dataset into PostgreSQL.

This stage will introduce persistent relational storage and explicit data modelling.

The next tasks will include:

- designing the database schema;
- selecting appropriate PostgreSQL data types;
- defining primary and unique keys;
- defining constraints;
- creating the required table or tables;
- loading transformed records;
- validating loaded data with SQL.

An internal database identifier can be separated from the source-level identity represented by `(source, source_job_id)`.

The PostgreSQL model will be designed from the transformed dataset that now actually exists rather than from assumptions about the original APIs.

---

## 📊 Analysis & Visualization

> 📋 **Planned**

Once data is available in PostgreSQL, SQL will be used to investigate the analytical questions defined at the beginning of the project.

Potential areas of analysis include:

**Roles & Skills**

Demand by IT role, commonly requested technologies, and relationships between skills and seniority where data coverage supports the analysis.

**Geography**

Distribution of opportunities across locations and differences between geographical areas.

**Working Conditions**

Remote, hybrid, and on-site opportunities across roles and locations.

**Salary**

Salary distributions and relationships with role, location, seniority, and skills where sufficient and comparable salary information exists.

**Time**

Changes in demand across different collection periods once enough historical observations have been accumulated.

### Power BI

Power BI is planned as the final visualization layer.

The dashboard will be an interface over the dataset produced by the pipeline — **not the main purpose of the project**.

The final dashboard will be designed around what the completed dataset can genuinely support.

---

## 🧰 Technology Stack

| | Technology | Role |
| --- | --- | --- |
| 🐍 | **Python** | Pipeline implementation |
| 🌐 | **Requests** | API communication |
| `{ }` | **JSON** | Raw and processed data persistence |
| 🔐 | **python-dotenv** | Environment variables |
| 🐼 | **Pandas** | Transformation and data validation |
| 🌿 | **Git** | Version control |
| 🐙 | **GitHub** | Repository & documentation |
| 🐘 | **PostgreSQL** | Relational storage — next milestone |
| 🗄️ | **SQL** | Validation & analysis — planned |
| 📊 | **Power BI** | Visualization — planned |
| 🐳 | **Docker** | Reproducibility — under evaluation |

> Technologies are added when they solve a concrete engineering problem, not simply to make the stack longer.

---

## 🗺️ Roadmap

| Milestone | Status |
| --- | :---: |
| Define project objective | ✅ |
| Define analytical questions | ✅ |
| Investigate job-data APIs | ✅ |
| Experiment with extraction strategies | ✅ |
| Implement Adzuna extraction | ✅ |
| Implement FreeHire extraction | ✅ |
| Add extraction error handling | ✅ |
| Persist raw JSON datasets | ✅ |
| Design transformation rules | ✅ |
| Implement `transform.py` | ✅ |
| Deduplicate source records | ✅ |
| Integrate source schemas | ✅ |
| Validate transformed data | ✅ |
| Persist processed dataset | ✅ |
| **Design PostgreSQL schema** | **🚧** |
| Load data into PostgreSQL | 📋 |
| Write analytical SQL queries | 📋 |
| Build Power BI analysis | 📋 |
| Add automated tests | 📋 |
| Improve logging & observability | 📋 |
| Evaluate Dockerization | 📋 |
| Create final architecture diagram | 📋 |
| Add screenshots & results | 📋 |
| Finalize documentation | 📋 |

---

## 🧠 Engineering Decisions So Far

### Raw means raw

Source data is persisted before cleaning so that transformations remain reproducible and debuggable.

### Extraction ≠ transformation

Extraction retrieves data. Transformation changes its representation.

Keeping the two separate prevents `extract.py` from becoming responsible for every stage of the pipeline.

### Deduplication is explicit

Repeated source IDs were observed during Adzuna extraction.

Raw records remain untouched, while duplicates are explicitly handled during transformation.

### Source identity is preserved

Every transformed record retains both its source and its source-specific identifier.

This allows records from different providers to coexist without assuming their identifiers belong to the same namespace.

### Cross-source deduplication is a different problem

Two records from different APIs may represent the same real-world vacancy, but determining this reliably requires entity-resolution logic.

Version 1 therefore performs only within-source deduplication.

### Missing data is better than invented data

When one source does not provide a reliable equivalent for a field exposed by another source, the pipeline preserves the missing value instead of deriving information through unvalidated assumptions.

### Salary values are not normalized without evidence

The current sources expose salary information with incomplete or potentially different semantics.

Version 1 preserves those values rather than applying arbitrary normalization rules.

### Coverage won over an overly narrow search

Searching only for `"Data Engineer"` produced high relevance but insufficient coverage for the broader analytical objective.

The extraction strategy was widened accordingly.

### Different APIs deserve different ingestion logic

Adzuna and FreeHire have different schemas, constraints, and pagination behavior.

They are handled independently during extraction and converge into a common representation during transformation.

### Model the database after understanding the data

The PostgreSQL schema is being designed from the transformed dataset rather than prematurely imposing a relational structure on unknown source fields.

### No technology for technology's sake

Docker, orchestration tools, additional APIs, and other components will only be introduced when the project has a concrete reason to use them.

---

## 🧪 Development Approach

This repository is also a record of the engineering process behind the final pipeline.

The project is being developed through small milestones:

```text
Problem
   ↓
Design
   ↓
Implement
   ↓
Run
   ↓
Inspect
   ↓
Find problems
   ↓
Improve
   ↓
Validate
   ↓
Document
   ↓
Repeat
```

That means the architecture is allowed to evolve.

A discarded API, duplicated record, unexpected API behavior, or failed extraction strategy is not necessarily wasted work — each can reveal a constraint that improves the next version of the pipeline.

The objective is not simply to end with a working repository, but to understand **why it works and why it was designed this way**.

---

## 🔮 Future Improvements

Version 1 has one priority:

> **Finish a reliable end-to-end pipeline before making it more complex.**

After that milestone, possible improvements include:

- additional job-data sources;
- advanced role classification;
- improved skill extraction from descriptions;
- salary-period and currency normalization;
- cross-source entity resolution;
- historical snapshots and richer trend analysis;
- scheduled ingestion;
- incremental database loading;
- stronger automated data-quality validation;
- improved logging and monitoring;
- pipeline orchestration;
- containerized execution.

These are **future possibilities, not currently implemented features**.

---

## 📍 Where the Project Is Now

```text
                              YOU ARE HERE
                                   │
                                   ▼
API ──► EXTRACT ──► RAW ──► TRANSFORM ──► PROCESSED ──► POSTGRESQL ──► ANALYZE
        ████████     ████████     ████████      ████████       ░░░░░░░░      ░░░░░░░░
           ✅           ✅           ✅             ✅             🚧             📋
```

### Next milestone

**Design the PostgreSQL model for the transformed dataset and implement the first loading stage.**

---

> **Note:** This README documents the project as it actually exists today. It will evolve alongside the pipeline as new components are implemented and new engineering decisions are made.