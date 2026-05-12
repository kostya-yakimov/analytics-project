WITH first_events AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        DATE(event_time) AS signup_date,
        platform
    FROM user_events
    ORDER BY user_id, event_time
),
activity AS (
    SELECT 
        e.user_id,
        f.platform,
        DATE(e.event_time) - f.signup_date AS day
    FROM user_events e
    JOIN first_events f ON e.user_id = f.user_id
    WHERE DATE(e.event_time) >= f.signup_date
),
cohort_size AS (
    SELECT 
        platform,
        COUNT(DISTINCT user_id) AS users
    FROM first_events
    GROUP BY platform
),
retention AS (
    SELECT 
        a.platform,
        a.day,
        COUNT(DISTINCT a.user_id) AS active_users
    FROM activity a
    WHERE a.day <= 30
    GROUP BY a.platform, a.day
)
SELECT 
    r.platform,
    r.day,
    r.active_users * 100.0 / c.users AS retention
FROM retention r
JOIN cohort_size c ON r.platform = c.platform
ORDER BY r.platform, r.day
