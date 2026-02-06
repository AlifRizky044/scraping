import jaydebeapi
import psycopg2
import jpype
import jpype.imports
from jpype import java

jvm_path = jpype.getDefaultJVMPath()
print(jvm_path)  # Verify path to libjvm.dylib

# --- Connect to HSQLDB ---
hsqldb_conn = jaydebeapi.connect(
    "org.hsqldb.jdbcDriver",
    "jdbc:hsqldb:hsql://localhost/dispenda",
    ["scbd_medan", "d15pend@"],
    "/Users/nevv/Documents/JavaBridgeDispenda/_setup-project/hsqldb.jar",
    jvm_path
)
hsqldb_cur = hsqldb_conn.cursor()

# --- Read data from HSQLDB ---
hsqldb_cur.execute("SELECT * FROM WAJIB_PAJAK")
rows = hsqldb_cur.fetchall()

print(f"Fetched {len(rows)} rows from HSQLDB.")

# # --- Connect to PostgreSQL ---
# pg_conn = psycopg2.connect(
#     host="localhost",
#     database="your_pg_db",
#     user="your_pg_user",
#     password="your_pg_pass"
# )
# pg_cur = pg_conn.cursor()



# # --- Get column names for dynamic insert ---
# col_names = [desc[0] for desc in hsqldb_cur.description]
# cols_str = ",".join(col_names)
# placeholders = ",".join(["%s"] * len(col_names))

# # --- Insert into PostgreSQL ---
# for row in rows:
#     # Convert booleans/integers/etc. here
#     fixed_row = []
#     for value in row:
#         if isinstance(value, int) and value in (0, 1):
#             fixed_row.append(bool(value))  # fix boolean type
#         elif value is None or str(value).lower() == "null":
#             fixed_row.append(None)  # real NULL
#         else:
#             fixed_row.append(value)
#     pg_cur.execute(f"INSERT INTO WAJIB_PAJAK ({cols_str}) VALUES ({placeholders})", fixed_row)

# pg_conn.commit()

# # --- Close connections ---
# hsqldb_cur.close()
# hsqldb_conn.close()
# pg_cur.close()
# pg_conn.close()


# source venv/bin/activate  
# python hsqlmigration.py 
