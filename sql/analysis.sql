-- ============================================================
-- Project IT Market Analysis - SQL Analysis
-- ============================================================


-- 1. Top 20 cities by number of job postings

SELECT
    city,
    COUNT(*) AS job_count
FROM jobs
WHERE city IS NOT NULL
GROUP BY city
ORDER BY job_count DESC
LIMIT 20;


-- 2. Top 20 skills by number of job postings

SELECT
    s.skill_name,
    COUNT(*) AS job_count
FROM skills AS s
JOIN job_skills AS js
    ON s.skill_id = js.skill_id
GROUP BY s.skill_name
ORDER BY job_count DESC
LIMIT 20;


-- 3. Work mode distribution for jobs with available work mode data

SELECT
    work_mode,
    COUNT(*) AS job_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM jobs
WHERE work_mode IS NOT NULL
GROUP BY work_mode
ORDER BY job_count DESC;


-- 4. Seniority distribution for jobs with available seniority data

SELECT
    seniority,
    COUNT(*) AS job_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM jobs
WHERE seniority IS NOT NULL
GROUP BY seniority
ORDER BY job_count DESC;


-- 5. Top 20 skills in junior job postings

SELECT
    s.skill_name,
    COUNT(*) AS job_count
FROM jobs AS j
JOIN job_skills AS js
    ON j.job_id = js.job_id
JOIN skills AS s
    ON s.skill_id = js.skill_id
WHERE j.seniority = 'junior'
GROUP BY s.skill_name
ORDER BY job_count DESC
LIMIT 20;


-- 6. Top skills comparison: junior vs senior job postings

WITH denominators AS (
    SELECT
        COUNT(DISTINCT j.job_id)
            FILTER (WHERE j.seniority = 'junior') AS junior_total,
        COUNT(DISTINCT j.job_id)
            FILTER (WHERE j.seniority = 'senior') AS senior_total
    FROM jobs AS j
    JOIN job_skills AS js
        ON j.job_id = js.job_id
    WHERE j.seniority IN ('junior', 'senior')
),
skill_counts AS (
    SELECT
        s.skill_name,
        COUNT(DISTINCT j.job_id)
            FILTER (WHERE j.seniority = 'junior') AS junior_jobs,
        COUNT(DISTINCT j.job_id)
            FILTER (WHERE j.seniority = 'senior') AS senior_jobs
    FROM jobs AS j
    JOIN job_skills AS js
        ON j.job_id = js.job_id
    JOIN skills AS s
        ON js.skill_id = s.skill_id
    WHERE j.seniority IN ('junior', 'senior')
    GROUP BY s.skill_name
)
SELECT
    sc.skill_name,
    sc.junior_jobs,
    ROUND(
        sc.junior_jobs * 100.0 / d.junior_total,
        2
    ) AS junior_percentage,
    sc.senior_jobs,
    ROUND(
        sc.senior_jobs * 100.0 / d.senior_total,
        2
    ) AS senior_percentage,
    ROUND(
        (sc.senior_jobs * 100.0 / d.senior_total)
        - (sc.junior_jobs * 100.0 / d.junior_total),
        2
    ) AS percentage_point_difference,
    sc.junior_jobs + sc.senior_jobs AS total_jobs
FROM skill_counts AS sc
CROSS JOIN denominators AS d
ORDER BY total_jobs DESC
LIMIT 20;


-- 7. Work mode distribution: junior vs senior job postings

SELECT
    seniority,
    work_mode,
    COUNT(*) AS job_count,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (PARTITION BY seniority),
        2
    ) AS percentage
FROM jobs
WHERE seniority IN ('junior', 'senior')
    AND work_mode IS NOT NULL
GROUP BY
    seniority,
    work_mode
ORDER BY
    seniority,
    job_count DESC;


-- 8. Top skill pairs by job co-occurrence

SELECT
    s1.skill_name AS skill_1,
    s2.skill_name AS skill_2,
    COUNT(*) AS jobs_together
FROM job_skills AS js1
JOIN job_skills AS js2
    ON js1.job_id = js2.job_id
    AND js1.skill_id < js2.skill_id
JOIN skills AS s1
    ON js1.skill_id = s1.skill_id
JOIN skills AS s2
    ON js2.skill_id = s2.skill_id
GROUP BY
    s1.skill_name,
    s2.skill_name
ORDER BY jobs_together DESC
LIMIT 20;