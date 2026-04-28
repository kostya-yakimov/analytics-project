import os
import streamlit as st
import pandas as pd
import psycopg2

# функция для загрузки SQL из файлов
def load_sql(filename):
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, '..', 'sql', filename)
    with open(path, 'r') as f:
        return f.read()

# --- подключение к базе ---
conn = psycopg2.connect(
   dbname="analytics", user="analyst", password="1234", host="localhost",
    port="5432"
)

# --- заголовок ---
st.title("📊 Product Analytics Dashboard")

# =========================
# DAU
# =========================
st.header("DAU (Daily Active Users)")

# dau_query = load_sql('dau.sql')
# dau_df = pd.read_sql(dau_query, conn)
# st.line_chart(dau_df.set_index("date"))

dau_platform = pd.read_sql("""
SELECT 
    DATE(event_time) as date,
    platform,
    COUNT(DISTINCT user_id) as dau
FROM events
GROUP BY date, platform
""", conn)

st.line_chart(dau_platform.pivot(index="date", columns="platform", values="dau"))


# =========================
# Retention
# =========================
#st.header("Retention")

# retention_query = load_sql('retention.sql')
# ret_df = pd.read_sql(retention_query, conn)
# st.dataframe(ret_df)
st.header("Retention by platform (daily)")

retention_platform_query = """
WITH first_events AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        DATE(event_time) AS signup_date,
        platform
    FROM events
    ORDER BY user_id, event_time
),

activity AS (
    SELECT 
        e.user_id,
        f.platform,
        DATE(e.event_time) - f.signup_date AS day
    FROM events e
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

days AS (
    SELECT generate_series(0, 30) AS day
),

retention AS (
    SELECT 
        f.platform,
        d.day,
        COUNT(DISTINCT f.user_id) FILTER (
            WHERE EXISTS (
                SELECT 1 
                FROM activity a 
                WHERE a.user_id = f.user_id 
                AND a.day >= d.day
            )
        ) AS retained_users
    FROM first_events f
    CROSS JOIN days d
    GROUP BY f.platform, d.day
)

SELECT 
    r.platform,
    r.day,
    r.retained_users * 100.0 / c.users AS retention
FROM retention r
JOIN cohort_size c ON r.platform = c.platform
ORDER BY r.platform, r.day
"""

retention_platform_df = pd.read_sql(retention_platform_query, conn)

pivot_df = retention_platform_df.pivot(
    index="day",
    columns="platform",
    values="retention"
)

st.line_chart(pivot_df)

# =========================
# Funnel
# =========================
st.header("Funnel")

# --- SQL ---
funnel_platform_query = """
SELECT 
    platform,
    COUNT(DISTINCT user_id) FILTER (WHERE event_type = 'login') as login,
    COUNT(DISTINCT user_id) FILTER (WHERE event_type = 'view_note') as view_note,
    COUNT(DISTINCT user_id) FILTER (WHERE event_type = 'create_note') as create_note
FROM events
GROUP BY platform;
"""

fp_df = pd.read_sql(funnel_platform_query, conn)

# --- конверсии ---
fp_df["conversion_to_view"] = fp_df["view_note"] / fp_df["login"] * 100
fp_df["conversion_to_create"] = fp_df["create_note"] / fp_df["login"] * 100
fp_df["view_to_create"] = fp_df["create_note"] / fp_df["view_note"] * 100

# --- таблица ---
st.subheader("Funnel table")
st.dataframe(fp_df)

# --- подготовка данных для графика ---
plot_df = fp_df.set_index("platform")[["login", "view_note", "create_note"]].T

# фикс порядка шагов (ВАЖНО)
plot_df = plot_df.reindex(["login", "view_note", "create_note"])

# (опционально — красивое название шагов)
plot_df.index = ["Login", "View Note", "Create Note"]

# --- график ---
import altair as alt

st.subheader("Funnel by platform")

# возвращаем в "длинный" формат
plot_long = plot_df.reset_index().melt(
    id_vars="index",
    var_name="platform",
    value_name="users"
)

plot_long = plot_long.rename(columns={"index": "step"})

# фикс порядка шагов
step_order = ["Login", "View Note", "Create Note"]

chart = alt.Chart(plot_long).mark_bar().encode(
    x=alt.X("step:N", sort=step_order),
    y="users:Q",
    color="platform:N"
)

st.altair_chart(chart, use_container_width=True)
# посмотреть датасет
st.header("Data")

df = pd.read_sql("SELECT * FROM events LIMIT 1000", conn)
st.dataframe(df)

# --- закрытие соединения ---
conn.close()
