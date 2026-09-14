import os
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def obtener_mapa_usuarios():
    # 1. Obtener la relación Hermano -> Email desde 'perfiles'
    res_perfiles = supabase.table("perfiles").select("hermano, email").execute()
    perfiles = res_perfiles.data if res_perfiles.data else []
    
    email_by_hermano = {
        str(p["hermano"]).strip(): str(p["email"]).strip().lower() 
        for p in perfiles if p.get("email")
    }
    
    # 2. Obtener lista de usuarios de Auth mediante Service Role Key
    users_resp = supabase.auth.admin.list_users()
    users = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
    
    user_id_by_email = {u.email.lower().strip(): u.id for u in users}
    
    # 3. Mapear Nombre Hermano -> UUID
    mapa_final = {}
    for hermano, email in email_by_hermano.items():
        if email in user_id_by_email:
            mapa_final[hermano] = user_id_by_email[email]
            
    print("Mapa de usuarios encontrado:", mapa_final)
    return mapa_final

def procesar_y_subir():
    mapa_usuarios = obtener_mapa_usuarios()
    
    # Limpiar la tabla antes de reinsertar
    supabase.table("deudas").delete().neq("id", 0).execute()
    
    excel_file = "2026_2027_deudas_hermanos.xlsx"  # Nombre de tu archivo Excel
    xls = pd.ExcelFile(excel_file)
    
    filas_a_insertar = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.dropna(how='all')
        
        # Mapear columnas a minúsculas para ignorar mayúsculas/minúsculas en el Excel
        nombre_pestana = str(sheet_name).strip()
        user_id = mapa_usuarios.get(nombre_pestana, None)
        
        for _, row in df.iterrows():
            # Crear diccionario case-insensitive para las filas
            row_dict = {str(k).strip().lower(): v for k, v in row.items()}
            
            # Extraer valores numéricos de forma segura
            precio = float(row_dict.get("precio", 0)) if pd.notnull(row_dict.get("precio")) else 0.0
            pagado = float(row_dict.get("pagado", 0)) if pd.notnull(row_dict.get("pagado")) else 0.0
            debe = float(row_dict.get("debe", 0)) if pd.notnull(row_dict.get("debe")) else 0.0
            asunto = str(row_dict.get("asunto", "")).strip()
            
            # Solo insertar filas que tengan asunto válido
            if asunto and asunto.lower() != "nan":
                filas_a_insertar.append({
                    "user_id": user_id,
                    "hermano": nombre_pestana,
                    "asunto": asunto,
                    "precio": precio,
                    "pagado": pagado,
                    "debe": debe
                })
            
    if filas_a_insertar:
        supabase.table("deudas").insert(filas_a_insertar).execute()
        print(f"¡Insertadas {len(filas_a_insertar)} filas con éxito!")

if __name__ == "__main__":
    procesar_y_subir()
