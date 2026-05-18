import os
import pandas as pd
from sqlalchemy import create_engine, text

CSV_PATH = os.getenv(
    "CSV_PATH",
    r"C:\Users\zigur\OneDrive\Documentos\New project\outputs\sinisa_bi_ready\saneamento_sp_municipios_selecionados_long.csv",
)
DATABASE_URL = os.getenv("DATABASE_URL", "")
TABLE_NAME = os.getenv("TABLE_NAME", "saneamento_sp_municipios_selecionados")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "50000"))

if not DATABASE_URL:
    raise SystemExit("Defina DATABASE_URL antes de executar.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

df = pd.read_csv(CSV_PATH, low_memory=False)

with engine.begin() as conn:
    conn.execute(text(f'DROP TABLE IF EXISTS {TABLE_NAME}'))

for i in range(0, len(df), CHUNK_SIZE):
    chunk = df.iloc[i : i + CHUNK_SIZE]
    chunk.to_sql(TABLE_NAME, engine, if_exists="append", index=False, method="multi")
    print(f"loaded {min(i+CHUNK_SIZE, len(df))}/{len(df)}")

with engine.begin() as conn:
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_ano ON {TABLE_NAME}(ano_ref)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_modulo ON {TABLE_NAME}(modulo)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_municipio ON {TABLE_NAME}(municipio)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_indicador ON {TABLE_NAME}(codigo_indicador)"))

print("done")
