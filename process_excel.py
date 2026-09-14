import os
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def obtener_mapa_usuarios():
    # 1. Obtener la relación Hermano -> Email desde la tabla 'perfiles'
    res_perfiles = supabase.table("perfiles").select("hermano, email").execute()
    perfiles = res_perfiles.data if res_perfiles.data else []
    
    email_by_hermano = {p["hermano"].strip(): p["email"].strip().lower() for p in perfiles if p.get("email")}
    
    # 2. Obtener lista de usuarios de Auth mediante la Service Key
    users_resp = supabase.auth.admin.list_users()
    users = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
    
    user_id_by_email = {u.email.lower(): u.id for u in users}
    
    # 3. Mapear Hermano -> user_id (UUID)
    mapa_final = {}
    for hermano, email in email_by_hermano.items():
        if email in user_id_by_email:
            mapa_final[hermano] = user_id_by_email[email]
            
    return mapa_final

def procesar_y_subir():
    mapa_usuarios = obtener_mapa_usuarios()
    
    # Borrar los datos antiguos para reemplazar con los del nuevo Excel
    supabase.table("deudas").delete().neq("id", 0).execute()
    
    excel_file = "2026_2027_deudas_hermanos.xlsx"  # Ajusta al nombre exacto de tu archivo en GitHub
    xls = pd.ExcelFile(excel_file)
    
    filas_a_insertar = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.dropna(how='all')
        
        # Obtener el user_id del hermano dueño de esta pestaña
        user_id = mapa_usuarios.get(sheet_name.strip(), None)
        
        for _, row in df.iterrows():
            filas_a_insertar.append({
                "user_id": user_id,  # <-- EL SCRIPT AHORA ASIGNA EL ID AUTOMÁTICAMENTE
                "hermano": sheet_name.strip(),
                "asunto": str(row.get("Asunto", "")),
                "precio": float(row.get("Precio", 0)) if pd.notnull(row.get("Precio")) else 0,
                "pagado": float(row.get("Pagado", 0)) if pd.notnull(row.get("Pagado")) else 0,
                "debe": float(row.get("Debe", 0)) if pd.notnull(row.get("Debe")) else 0
            })
            
    if filas_a_insertar:
        supabase.table("deudas").insert(filas_a_insertar).execute()

if __name__ == "__main__":
    procesar_y_subir()
