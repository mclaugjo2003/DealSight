"""
Supabase client helper – auth + CRUD for properties/analyses
"""
import os
from typing import Optional
from supabase import create_client, Client
import streamlit as st


# ─────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────

def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in secrets.toml")
    return create_client(url, key)


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: str = "") -> dict:
    sb = get_supabase()
    res = sb.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}},
    })
    return {"user": res.user, "session": res.session, "error": None}


def sign_in(email: str, password: str) -> dict:
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["supabase_session"] = res.session
        st.session_state["supabase_user"]    = res.user
        return {"user": res.user, "session": res.session, "error": None}
    except Exception as e:
        return {"user": None, "session": None, "error": str(e)}


def sign_out():
    sb = get_supabase()
    sb.auth.sign_out()
    for key in ["supabase_session", "supabase_user"]:
        st.session_state.pop(key, None)


def current_user():
    return st.session_state.get("supabase_user")


def is_authenticated() -> bool:
    return current_user() is not None


def get_profile() -> Optional[dict]:
    user = current_user()
    if not user:
        return None
    sb = get_supabase()
    res = sb.table("profiles").select("*").eq("id", user.id).single().execute()
    return res.data


def can_analyze() -> bool:
    profile = get_profile()
    if not profile:
        return False
    limits = {"free": 3, "pro": 100, "team": 9999}
    return profile.get("analyses_used", 0) < limits.get(profile.get("plan", "free"), 3)


# ─────────────────────────────────────────────
# Properties CRUD
# ─────────────────────────────────────────────

def save_property(data: dict) -> dict:
    user = current_user()
    if not user:
        return {"error": "Not authenticated"}
    sb = get_supabase()
    data["user_id"] = user.id
    res = sb.table("properties").upsert(data).execute()
    return res.data[0] if res.data else {}


def get_properties(status: str = None) -> list:
    user = current_user()
    if not user:
        return []
    sb = get_supabase()
    q = sb.table("properties").select("*").eq("user_id", user.id)
    if status:
        q = q.eq("status", status)
    res = q.order("created_at", desc=True).execute()
    return res.data or []


def get_property(property_id: str) -> Optional[dict]:
    user = current_user()
    if not user:
        return None
    sb = get_supabase()
    res = (sb.table("properties")
             .select("*, analyses(*)")
             .eq("id", property_id)
             .eq("user_id", user.id)
             .single()
             .execute())
    return res.data


def delete_property(property_id: str) -> bool:
    user = current_user()
    if not user:
        return False
    sb = get_supabase()
    sb.table("properties").delete().eq("id", property_id).eq("user_id", user.id).execute()
    return True


# ─────────────────────────────────────────────
# Analyses CRUD
# ─────────────────────────────────────────────

def save_analysis(property_id: str, inputs: dict, metrics: dict,
                  grades: dict = None, analysis_type: str = "standard") -> dict:
    user = current_user()
    if not user:
        return {}
    sb = get_supabase()

    data = {
        "property_id":   property_id,
        "user_id":       user.id,
        "inputs":        inputs,
        "metrics":       metrics,
        "grades":        grades or {},
        "analysis_type": analysis_type,
    }
    res = sb.table("analyses").insert(data).execute()

    # Increment usage counter
    sb.rpc("increment_analyses_used", {"uid": user.id}).execute()

    return res.data[0] if res.data else {}


def get_analyses(property_id: str) -> list:
    user = current_user()
    if not user:
        return []
    sb = get_supabase()
    res = (sb.table("analyses")
             .select("*")
             .eq("property_id", property_id)
             .eq("user_id", user.id)
             .order("created_at", desc=True)
             .execute())
    return res.data or []


# ─────────────────────────────────────────────
# Rent Comps
# ─────────────────────────────────────────────

def save_comps(property_id: str, comps: list, source: str = "rentcast"):
    sb = get_supabase()
    rows = [
        {
            "property_id":    property_id,
            "source":         source,
            "comp_address":   c.get("address"),
            "comp_rent":      c.get("rent"),
            "comp_beds":      c.get("beds"),
            "comp_baths":     c.get("baths"),
            "comp_sqft":      c.get("sqft"),
            "days_on_market": c.get("days_on"),
            "distance_miles": c.get("distance"),
            "raw_data":       c,
        }
        for c in (comps or [])
    ]
    if rows:
        sb.table("rent_comps").insert(rows).execute()


def get_comps(property_id: str) -> list:
    sb = get_supabase()
    res = (sb.table("rent_comps")
             .select("*")
             .eq("property_id", property_id)
             .order("fetched_at", desc=True)
             .limit(20)
             .execute())
    return res.data or []
