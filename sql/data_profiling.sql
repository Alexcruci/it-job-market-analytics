-- ============================================================
-- Project IT Market Analysis - Data Profiling
-- ============================================================


-- 1. Source composition

SELECT
    source,
    COUNT(*) AS job_count
FROM jobs
GROUP BY source;


-- 2. Missing value coverage by source

SELECT
    source,
    COUNT(*) AS total_jobs,
    COUNT(*) - COUNT(company) AS missing_company,
    COUNT(*) - COUNT(location) AS missing_location,
    COUNT(*) - COUNT(city) AS missing_city,
    COUNT(*) - COUNT(salary_min) AS missing_salary_min,
    COUNT(*) - COUNT(salary_max) AS missing_salary_max,
    COUNT(*) - COUNT(seniority) AS missing_seniority,
    COUNT(*) - COUNT(work_mode) AS missing_work_mode
FROM jobs
GROUP BY source;


-- 3. Duplicate source job IDs

SELECT
    source,
    source_job_id,
    COUNT(*) AS occurrence_count
FROM jobs
GROUP BY source, source_job_id
HAVING COUNT(*) > 1;


-- 4. Seniority distribution

SELECT
    seniority,
    COUNT(*) AS job_count
FROM jobs
WHERE seniority IS NOT NULL
GROUP BY seniority
ORDER BY job_count DESC;


-- 5. Work mode distribution

SELECT
    work_mode,
    COUNT(*) AS job_count
FROM jobs
WHERE work_mode IS NOT NULL
GROUP BY work_mode
ORDER BY job_count DESC;


-- 6. Publication date coverage by source

SELECT
    source,
    MIN(published_date) AS earliest_date,
    MAX(published_date) AS latest_date
FROM jobs
GROUP BY source;


-- 7. Monthly publication coverage for 2026

SELECT
    source,
    EXTRACT(MONTH FROM published_date) AS month,
    COUNT(*) AS job_count
FROM jobs
WHERE EXTRACT(YEAR FROM published_date) = 2026
GROUP BY
    source,
    EXTRACT(MONTH FROM published_date)
ORDER BY
    source,
    EXTRACT(MONTH FROM published_date);


-- 8. Salary minimum coverage by source

SELECT
    source,
    COUNT(*) AS total_jobs,
    COUNT(salary_min) AS jobs_with_salary_min,
    COUNT(salary_min) * 100.0 / COUNT(*) AS salary_min_coverage_pct
FROM jobs
GROUP BY source;


-- 9. Salary range by source

SELECT
    source,
    MIN(salary_min) AS lowest_salary_min,
    MAX(salary_max) AS highest_salary_max
FROM jobs
GROUP BY source;


-- 10. Suspiciously low salary values
-- Diagnostic threshold only; not used as a cleaning rule.

SELECT
    source,
    COUNT(*) AS suspicious_low_salary_count
FROM jobs
WHERE salary_min < 1000
GROUP BY source;


-- 11. Skills coverage by source

SELECT
    j.source,
    COUNT(DISTINCT j.job_id) AS total_jobs,
    COUNT(DISTINCT js.job_id) AS jobs_with_skills,
    COUNT(DISTINCT js.job_id) * 100.0
        / COUNT(DISTINCT j.job_id) AS skills_coverage_pct
FROM jobs AS j
LEFT JOIN job_skills AS js
    ON j.job_id = js.job_id
GROUP BY j.source;