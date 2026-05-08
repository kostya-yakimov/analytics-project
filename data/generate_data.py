import pandas as pd
import random
from datetime import datetime, timedelta
import os
from sqlalchemy import create_engine  # Добавили для связи с БД

# Считываем данные из Docker Compose
db_host = os.getenv("DB_HOST", "db")
db_name = os.getenv("DB_NAME", "analytics")
db_user = os.getenv("DB_USER", "analyst")
db_pass = os.getenv("DB_PASSWORD", "1234")

# Создаем строку подключения
conn_uri = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
engine = create_engine(conn_uri)

NUM_USERS = 1000
events = []
start_date = datetime(2026, 2, 1)

for user_id in range(1, NUM_USERS + 1):
    platform = random.choices(["ios", "Android", "Web"], weights=[0.4, 0.4, 0.2])[0]
    
    # login
    login_time = start_date + timedelta(days=random.randint(0, 30))
    events.append([user_id, "login", login_time, platform])
    
    # view_note
    if random.random() < 0.7:
        view_time = login_time + timedelta(days=random.randint(0, 5))
        events.append([user_id, "view_note", view_time, platform])
        
    # create_note
    if random.random() < 0.4:
        create_time = login_time + timedelta(days=random.randint(0, 5))
        events.append([user_id, "create_note", create_time, platform])

df = pd.DataFrame(events, columns=["user_id", "event_type", "event_time", "platform"])

# ЗАГРУЗКА В POSTGRES (Вместо CSV)
try:
    # if_exists='replace' создаст таблицу автоматически или перезапишет её
    df.to_sql("user_events", engine, if_exists='replace', index=False)
    print(f"✅ Успешно загружено {len(df)} событий в таблицу 'user_events'")
except Exception as e:
    print(f"❌ Ошибка при загрузке в БД: {e}")
