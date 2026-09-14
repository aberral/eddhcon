import os
import pandas as pd
from supabase import create_client, Client

# Configuración de variables de entorno (las provee GitHub Actions)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

EXCEL_PATH = "2026_2027_deudas_hermanos.xlsx"

def process_file():
    if not os.path.exists(EXCEL_PATH):
        print(f"El archivo {EXCEL_PATH} no se encuentra en el repositorio.")
        return

    xls = pd.ExcelFile(EXCEL_PATH)
    
    # 1. Traer mapeo de usuarios (user_id por email/nombre) desde Supabase
    users_resp = supabase.auth.admin.list_users()
    user_map = {u.user_metadata.get('full_name', u.email): u.id for u in users_resp}

    # 2. Parsear Hoja Resumen
    df_resumen = pd.read_excel(xls, sheet_name="Resumen", skiprows=1)
    df_resumen_clean = df_resumen.iloc[:, [0, 1, 2, 3]].dropna(subset=[df_resumen.columns[0]])
    df_resumen_clean.columns = ["nombre", "total", "domiciliado", "propiedad"]

    # 3. Limpiar tabla anterior en Supabase
    supabase.table("deudas").delete().neq("id", 0).execute()

    # 4. Parsear cada pestaña individual
    movimientos = []
    hojas_hermanos = [s for s in xls.sheet_names if s != "Resumen"]

    for hermano in hojas_hermanos:
        df_h = pd.read_excel(xls, sheet_name=hermano)
        header_row = None
        for idx, row in df_h.iterrows():
            if "Asunto" in row.values:
                header_row = idx
                break

        if header_row is not None:
            df_h_clean = pd.read_excel(xls, sheet_name=hermano, skiprows=header_row + 1).iloc[:, :4]
            df_h_clean.columns = ["asunto", "precio", "pagado", "debe"]
            df_h_clean = df_h_clean.dropna(subset=["asunto"])

            user_id = user_map.get(hermano)

            for _, r in df_h_clean.iterrows():
                movimientos.append({
                    "user_id": user_id,
                    "hermano": hermano,
                    "asunto": str(r["asunto"]),
                    "precio": float(r["precio"]) if pd.notnull(r["precio"]) else 0,
                    "pagado": float(r["pagado"]) if pd.notnull(r["pagado"]) else 0,
                    "debe": float(r["debe"]) if pd.notnull(r["debe"]) else 0
                })

    if movimientos:
        supabase.table("deudas").insert(movimientos).execute()
        print(f"✅ Se insertaron {len(movimientos)} movimientos en Supabase.")

if __name__ == "__main__":
    process_file()
