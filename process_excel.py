import os
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def obtener_mapa_usuarios():
    # 1. Lee las relaciones Hermano -> Email desde tu tabla 'perfiles'
    res_perfiles = supabase.table("perfiles").select("hermano, email").execute()
    perfiles = res_perfiles.data if res_perfiles.data else []
    
    email_by_hermano = {p["hermano"].strip(): p["email"].strip().lower() for p in perfiles if p.get("email")}
    
    # 2. Obtiene la lista de usuarios de Auth
    users_resp = supabase.auth.admin.list_users()
    users = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
    
    user_id_by_email = {u.email.lower(): u.id for u in users}
    
    # 3. Asocia la pestaña del Excel con el user_id final
    mapa_final = {}
    for hermano, email in email_by_hermano.items():
        if email in user_id_by_email:
            mapa_final[hermano] = user_id_by_email[email]
            
    return mapa_final
