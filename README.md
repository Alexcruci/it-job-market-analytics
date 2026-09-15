# 💼 IT Job Market Data Pipeline

> **An end-to-end Data Engineering project exploring the IT job market through real-world API data.**

This project collects IT job postings from multiple sources, preserves the original API responses, transforms and integrates heterogeneous data, and will ultimately load the resulting dataset into PostgreSQL for SQL analysis and Power BI visualization.

The goal is not just to analyze a dataset, but to **build the pipeline that creates it**.

> 🚧 **Project Status — Work in Progress**
>
> The **extraction layer is complete** and currently collects data from Adzuna and FreeHire.
> **Transformation is the next development milestone**, followed by PostgreSQL, SQL analysis, and visualization.

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

These questions define the analytical scope of the project and will guide the transformation, data modelling, SQL analysis, and visualization stages.

> **Note:** Not every question is answerable yet.
> In particular, meaningful trend analysis will require data collected across multiple points in time. Final analyses will also depend on the quality and availability of fields exposed by the selected APIs.

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
│ Python Transformation│  🚧
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      PostgreSQL      │  📋
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

**Legend:** ✅ Implemented · 🚧 In progress / next milestone · 📋 Planned

The architecture will evolve only when new requirements justify it.

---

## 🌐 Data Sources

The current pipeline uses two job-market APIs:

### Adzuna

Adzuna is one of the primary sources used by the extraction layer.

The extractor currently handles:

* paginated HTTP requests;
* HTTP response validation;
* explicit request timeouts;
* retry handling;
* job ID tracking during pagination;
* raw JSON persistence.

A current extraction run produced:

| Metric                |    Result |
| --------------------- | --------: |
| Raw records           | **5,000** |
| Unique Adzuna job IDs | **4,613** |

That difference is important.

The extraction layer **does not silently remove duplicate records**. Raw data is intended to represent what was actually collected from the source; duplicate detection and handling will be an explicit responsibility of the transformation layer.

### FreeHire

FreeHire provides the second source of job-market data.

The current extraction targets technology-related job listings in Italy and handles:

* paginated API requests;
* batches of up to 100 records;
* HTTP response validation;
* request timeouts;
* retry handling;
* API pagination constraints;
* raw JSON persistence.

A current extraction run produced:

| Metric      |     Result |
| ----------- | ---------: |
| Raw records | **10,000** |

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

Adzuna and FreeHire can represent similar concepts using different fields, structures, pagination systems, and levels of completeness.

The transformation layer will therefore need to decide:

* which fields can be mapped across both sources;
* how missing values should be represented;
* how duplicates should be identified;
* which source-specific information should be preserved;
* how both APIs can be converted into a consistent analytical model.

This will also allow comparison of **completeness, duplication, field availability, and overall data quality** between providers.

### What Happened to Jooble?

Jooble was evaluated during the early development phase as a possible additional source.

After experimentation, it was **not retained in the current pipeline**.

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
extract.py
```

and currently produces:

```text
data/
└── raw/
    ├── adzuna_jobs.json
    └── freehire_jobs.json
```

### What extraction does — and does not do

| Extraction does          | Extraction does **not** do |
| ------------------------ | -------------------------- |
| Call external APIs       | Deduplicate records        |
| Handle pagination        | Normalize fields           |
| Validate HTTP responses  | Clean values               |
| Retry transient failures | Integrate schemas          |
| Preserve raw records     | Load PostgreSQL            |
| Save JSON files          | Perform analytics          |

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
  RAW       ← preserve what was collected
   │
   ▼
TRANSFORM   ← clean, normalize, integrate
   │
   ▼
DATABASE
   │
   ▼
ANALYTICS
```

This separation means that:

* transformations can be rerun without calling the APIs again;
* transformation bugs do not automatically require re-extraction;
* original source records remain available for debugging;
* differences between APIs can be inspected later;
* cleaning decisions remain separate from ingestion.

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

Those records are preserved intentionally. What counts as a duplicate — and which record should survive — will be decided during transformation.

---

## 🔎 A Problem We Hit Early: What Should We Search For?

The first extraction experiments searched specifically for:

```text
Data Engineer
```

The results were relevant, but the query was too restrictive for a project intended to analyze the broader IT job market.

That exposed a classic trade-off:

```text
              PRECISION
                 ▲
                 │
  Narrow query   │
                 │
─────────────────┼────────────────► COVERAGE
                 │
                 │   Broad query
                 │
```

A narrow query gives us **higher precision but lower coverage**.

A broader query increases **coverage**, but introduces more records that may later turn out to be irrelevant.

For this project, the extraction strategy evolved toward broader technology-job collection.

More detailed filtering and classification will happen downstream, where the logic can be inspected, tested, and changed without repeatedly querying the APIs.

---

## 🔄 Next Up: Transformation

> 🚧 **Current development milestone**

The next component will be:

```text
transform.py
```

This is where the two independent raw datasets begin becoming **one dataset**.

The first challenge will be understanding what Adzuna and FreeHire actually returned before deciding how to transform it.

Expected responsibilities include:

* inspecting both source schemas;
* selecting useful fields;
* defining a common representation;
* combining records from multiple APIs;
* identifying and handling duplicates;
* normalizing column names;
* handling missing values consistently;
* cleaning salary information where available;
* standardizing locations where appropriate;
* normalizing categorical fields where justified;
* validating transformed records.

> The transformation rules are deliberately **not fully defined yet**.
>
> They will be designed from the actual raw data rather than assuming in advance what the APIs should contain.

---

## 🐘 PostgreSQL

> 📋 **Planned**

Once the transformed model is stable, the resulting dataset will be loaded into PostgreSQL.

This stage will introduce persistent relational storage and data modelling.

It is expected to cover:

* database schema design;
* PostgreSQL data types;
* keys and constraints;
* table creation;
* loading transformed records;
* SQL validation;
* repeated pipeline executions;
* analytical queries.

The database schema has deliberately **not been finalized yet**.

Designing it before understanding the transformed data would mean designing around assumptions rather than around the data the pipeline can actually produce.

---

## 📊 Analysis & Visualization

> 📋 **Planned**

Once data is available in PostgreSQL, SQL will be used to investigate the analytical questions defined at the beginning of the project.

Areas of analysis may include:

**Roles & Skills**
Demand by IT role, commonly requested technologies, and relationships between skills and seniority.

**Geography**
Distribution of opportunities across locations and differences between geographical areas.

**Working Conditions**
Remote, hybrid, and on-site opportunities across roles and locations.

**Salary**
Salary distributions and relationships with role, location, seniority, and skills where sufficient salary information exists.

**Time**
Changes in demand across different collection periods once enough historical observations have been accumulated.

### Power BI

Power BI is planned as the final visualization layer.

The dashboard will be an interface over the dataset produced by the pipeline — **not the main purpose of the project**.

Potential outputs include role demand, technology demand, geographic distributions, salary analysis, seniority breakdowns, working-condition distributions, and selected job-market KPIs.

The final dashboard will be designed around what the completed dataset can genuinely support.

---

## 🧰 Technology Stack

|       | Technology        | Role                               |
| ----- | ----------------- | ---------------------------------- |
| 🐍    | **Python**        | Pipeline implementation            |
| 🌐    | **Requests**      | API communication                  |
| `{ }` | **JSON**          | Raw data persistence               |
| 🔐    | **python-dotenv** | Environment variables              |
| 🌿    | **Git**           | Version control                    |
| 🐙    | **GitHub**        | Repository & documentation         |
| 🐼    | **Pandas**        | Transformation — planned           |
| 🐘    | **PostgreSQL**    | Relational storage — planned       |
| 🗄️   | **SQL**           | Validation & analysis — planned    |
| 📊    | **Power BI**      | Visualization — planned            |
| 🐳    | **Docker**        | Reproducibility — under evaluation |

> Technologies are added when they solve a concrete engineering problem, not simply to make the stack longer.

---

## 🗺️ Roadmap

| Milestone                             | Status |
| ------------------------------------- | :----: |
| Define project objective              |    ✅   |
| Define analytical questions           |    ✅   |
| Investigate job-data APIs             |    ✅   |
| Experiment with extraction strategies |    ✅   |
| Implement Adzuna extraction           |    ✅   |
| Implement FreeHire extraction         |    ✅   |
| Add extraction error handling         |    ✅   |
| Persist raw JSON datasets             |    ✅   |
| **Design transformation rules**       | **🚧** |
| Implement `transform.py`              |   📋   |
| Validate transformed data             |   📋   |
| Design PostgreSQL schema              |   📋   |
| Load data into PostgreSQL             |   📋   |
| Write analytical SQL queries          |   📋   |
| Build Power BI analysis               |   📋   |
| Add automated tests                   |   📋   |
| Improve logging & observability       |   📋   |
| Evaluate Dockerization                |   📋   |
| Create final architecture diagram     |   📋   |
| Add screenshots & results             |   📋   |
| Finalize documentation                |   📋   |

---

## 🧠 Engineering Decisions So Far

This project is being built incrementally, and several design decisions have already emerged from actual implementation problems.

### Raw means raw

Source data is persisted before cleaning so that transformations remain reproducible and debuggable.

### Extraction ≠ transformation

Extraction retrieves data. Transformation changes its representation.

Keeping the two separate prevents `extract.py` from becoming responsible for every stage of the pipeline.

### Duplicates are not silently deleted

Repeated source IDs were observed during Adzuna extraction.

Instead of quietly removing them, the raw layer preserves them and makes deduplication an explicit downstream decision.

### Coverage won over an overly narrow search

Searching only for `"Data Engineer"` produced high relevance but insufficient coverage for the broader analytical objective.

The extraction strategy was widened accordingly.

### Different APIs deserve different ingestion logic

Adzuna and FreeHire have different schemas, constraints, and pagination behavior.

They are handled independently during extraction and will only converge into a common representation during transformation.

### Model the database after understanding the data

The PostgreSQL schema will be designed from the transformed dataset rather than prematurely imposing a relational structure on unknown source fields.

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
Document
   ↓
Repeat
```

That means the architecture is allowed to evolve.

A discarded API, a duplicated record, or a failed extraction strategy is not necessarily wasted work — each can reveal a constraint that improves the next version of the pipeline.

The objective is not simply to end with a working repository, but to understand **why it works and why it was designed this way**.

---

## 🔮 Future Improvements

Version 1 has one priority:

> **Finish a reliable end-to-end pipeline before making it more complex.**

After that milestone, possible improvements include:

* additional job-data sources;
* advanced role classification;
* improved skill extraction from descriptions;
* historical snapshots and richer trend analysis;
* scheduled ingestion;
* incremental database loading;
* stronger automated data-quality validation;
* improved logging and monitoring;
* pipeline orchestration;
* containerized execution.

These are **future possibilities, not currently implemented features**.

---

## 📍 Where the Project Is Now

```text
                        YOU ARE HERE
                             │
                             ▼
API ──► EXTRACT ──► RAW ──► TRANSFORM ──► POSTGRESQL ──► ANALYZE
        ████████     ████████     ░░░░░░░░      ░░░░░░░░      ░░░░░░░░
           ✅           ✅           🚧             📋             📋
```

### Next milestone

**Inspect the raw Adzuna and FreeHire datasets, compare their schemas, and design the first transformation rules for `transform.py`.**

---

> **Note:** This README documents the project as it actually exists today. It will evolve alongside the pipeline as new components are implemented and new engineering decisions are made.
