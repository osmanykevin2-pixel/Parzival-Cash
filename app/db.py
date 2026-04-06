from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user(telegram_user_id: int):
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_user(data: dict):
    result = (
        supabase.table("users")
        .upsert(data, on_conflict="telegram_user_id")
        .execute()
    )
    print("UPSERT RESULT:", result.data)
    return result