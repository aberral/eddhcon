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
    
    # 2. Obtener lista de usuarios de Auth
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
    
    # Buscar el archivo Excel en la carpeta del repositorio
    excel_file = None
    for file in os.listdir("."):
        if file.endswith(".xlsx") or file.endswith(".xls"):
            excel_file = file
            break
            
    if not excel_file:
        print("ERROR: No se ha encontrado ningún archivo Excel en el repositorio.")
        return

    print(f"Procesando archivo: {excel_file}")
    xls = pd.ExcelFile(excel_file)
    
    # Limpiar la tabla antes de reinsertar
    supabase.table("deudas").delete().neq("id", 0).execute()
    
    filas_a_insertar = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.dropna(how='all')
        
        nombre_pestana = str(sheet_name).strip()
        user_id = mapa_usuarios.get(nombre_pestana, None)
        
        for _, row in df.iterrows():
            # Convertir todas las llaves de la fila a minúsculas
            row_dict = {str(k).strip().lower(): v for k, v in row.items()}
            
            # Buscar el valor de asunto probando varias posibilidades comunes
            asunto_val = row_dict.get("asunto") or row_dict.get("concepto") or row_dict.get("descripcion") or ""
            asunto_str = str(asunto_val).strip()
            
            # Ignorar filas totalmente vacías o sin asunto válido
            if not asunto_str or asunto_str.lower() in ["nan", "none", ""]:
                continue
                
            precio = float(row_dict.get("precio", 0)) if pd.notnull(row_dict.get("precio")) else 0.0
            pagado = float(row_dict.get("pagado", 0)) if pd.notnull(row_dict.get("pagado")) else 0.0
            debe = float(row_dict.get("debe", 0)) if pd.notnull(row_dict.get("debe")) else 0.0
            
            filas_a_insertar.append({
                "user_id": user_id,
                "hermano": nombre_pestana,
                "asunto": asunto_str,
                "precio": precio,
                "pagado": pagado,
                "debe": debe
            })
            
    if filas_a_insertar:
        supabase.table("deudas").insert(filas_a_insertar).execute()
        print(f"¡Insertadas {len(filas_a_insertar)} filas con éxito!")
    else:
        print("Atención: No se han encontrado filas válidas para insertar.")

if __name__ == "__main__":
    procesar_y_subir()
