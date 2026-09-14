import os
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def obtener_mapa_usuarios():
    # 1. Obtener relación Hermano -> Email desde 'perfiles'
    res_perfiles = supabase.table("perfiles").select("hermano, email").execute()
    perfiles = res_perfiles.data if res_perfiles.data else []
    
    email_by_hermano = {
        str(p["hermano"]).strip(): str(p["email"]).strip().lower() 
        for p in perfiles if p.get("email")
    }
    
    # 2. Obtener usuarios de Auth
    users_resp = supabase.auth.admin.list_users()
    users = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
    
    user_id_by_email = {u.email.lower().strip(): u.id for u in users}
    
    # 3. Mapear Hermano -> UUID
    mapa_final = {}
    for hermano, email in email_by_hermano.items():
        if email in user_id_by_email:
            mapa_final[hermano] = user_id_by_email[email]
            
    return mapa_final

def procesar_y_subir():
    mapa_usuarios = obtener_mapa_usuarios()
    
    excel_file = "2026_2027_deudas_hermanos.xlsx"
    if not os.path.exists(excel_file):
        print(f"ERROR: No existe el archivo {excel_file}")
        return

    xls = pd.ExcelFile(excel_file)
    filas_a_insertar = []
    
    for sheet_name in xls.sheet_names:
        # 1. Cargar la hoja completa sin asumiendo encabezados aún
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        # 2. Encontrar la fila donde están las columnas reales (buscando la palabra 'Asunto')
        header_row_idx = None
        for idx, row in df_raw.iterrows():
            row_values = [str(val).strip().lower() for val in row.values if pd.notnull(val)]
            if any("asunto" in val or "concepto" in val for val in row_values):
                header_row_idx = idx
                break
                
        if header_row_idx is None:
            # Si no encuentra la palabra clave, intenta asumir la fila 0
            header_row_idx = 0

        # 3. Recargar el DataFrame usando la fila correcta como encabezado
        df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row_idx)
        df = df.dropna(how='all')

        nombre_pestana = str(sheet_name).strip()
        user_id = mapa_usuarios.get(nombre_pestana, None)
        
        for _, row in df.iterrows():
            row_dict = {str(k).strip().lower(): v for k, v in row.items() if pd.notnull(v)}
            
            asunto_val = row_dict.get("asunto") or row_dict.get("concepto") or row_dict.get("descripcion")
            asunto_str = str(asunto_val).strip() if asunto_val else ""
            
            # Omitir filas que no sean movimientos reales o subtotales
            if not asunto_str or asunto_str.lower() in ["nan", "none", "total", "subtotal", "asunto"]:
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
        supabase.table("deudas").delete().neq("id", 0).execute()
        supabase.table("deudas").insert(filas_a_insertar).execute()
        print(f"¡ÉXITO! Insertadas {len(filas_a_insertar)} filas omitiendo los títulos superiores.")
    else:
        print("Atención: No se han encontrado filas válidas para insertar.")

if __name__ == "__main__":
    procesar_y_subir()
