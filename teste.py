import psycopg2

DB_URL = "postgresql://postgres:Novembro2016@db.pryqscahyzdbuhochvkh.supabase.co:5432/postgres?sslmode=require"

try:
    conn = psycopg2.connect(DB_URL)
    print("Ligação OK!")
    conn.close()
except Exception as e:
    print(e)