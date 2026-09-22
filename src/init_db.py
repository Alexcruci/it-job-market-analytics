import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Find SQL schema file
project_root = Path(__file__).resolve().parent.parent
schema_path = project_root / "sql" / "schema.sql"

with open(schema_path, "r", encoding="utf-8") as file:
    schema_sql = file.read()

# Connect to PostgreSQL
connection = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

print("Database connection successful.")

cursor = connection.cursor()

for statement in schema_sql.split(";"):
    statement = statement.strip()

    if statement:
        cursor.execute(statement)

connection.commit()

print("Database schema initialized successfully.")

cursor.close()
connection.close()