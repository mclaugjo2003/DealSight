"""
python_core/listings.py
========================
Fetches active local rental listings (RentCast) and attaches
Google Street View Static API photos to each listing.
"""

import os
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

RENTCAST_KEY  = os.getenv("RENTCAST_API_KEY", "")
GMAPS_KEY     = os.getenv("GOOGLE_MAPS_API_KEY", "")
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "")


def _get(url: str, headers: dict = None,
         params: dict = None, timeout: int = 12) -> Optional[dict | list]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"Request failed: {url} → {e}")
        return None


# ─────────────────────────────────────────────
# Street View photo URL builder
# ─────────────────────────────────────────────

def street_view_url(address: str, api_key: str,
                    width: int = 640, height: int = 380,
                    pitch: int = 5, fov: int = 80) -> str:
    """
    Returns a Google Street View Static API image URL.
    Completely free up to $200/mo credit (~28k images).
    No API key = returns a placeholder SVG data URI.
    """
    if not api_key:
        return _placeholder_svg(address)

    import urllib.parse
    base = "https://maps.googleapis.com/maps/api/streetview"
    params = {
        "size":     f"{width}x{height}",
        "location": address,
        "pitch":    pitch,
        "fov":      fov,
        "key":      api_key,
        "return_error_code": "true",
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


def street_view_metadata(address: str, api_key: str) -> dict:
    """Check if Street View imagery exists before rendering."""
    if not api_key:
        return {"status": "ZERO_RESULTS"}
    import urllib.parse
    url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    params = {"location": address, "key": api_key}
    data = _get(url, params=params)
    return data or {"status": "UNKNOWN"}


def _placeholder_svg(address: str) -> str:
    """Dark placeholder card when no photo is available."""
    short = address[:22] + "…" if len(address) > 22 else address
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='640' height='380'
        viewBox='0 0 640 380'>
        <rect width='640' height='380' fill='%230d0d14'/>
        <rect x='280' y='140' width='80' height='60' rx='4' fill='%231e1e2e'
              stroke='%23c8a96e' stroke-width='1.5'/>
        <path d='M260 170 L320 130 L380 170' stroke='%23c8a96e'
              stroke-width='1.5' fill='none'/>
        <circle cx='320' cy='165' r='8' fill='%23c8a96e' opacity='.4'/>
        <text x='320' y='230' text-anchor='middle'
              font-family='monospace' font-size='12'
              fill='rgba(200,190,170,0.35)'>{short}</text>
        <text x='320' y='250' text-anchor='middle'
              font-family='monospace' font-size='10'
              fill='rgba(200,190,170,0.2)'>No photo available</text>
    </svg>"""
    import base64
    encoded = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


# ─────────────────────────────────────────────
# RentCast — active rental listings
# ─────────────────────────────────────────────

class ListingsFetcher:

    RENTCAST_BASE = "https://api.rentcast.io/v1"

    def __init__(self, rentcast_key: str = RENTCAST_KEY,
                 gmaps_key: str = GMAPS_KEY):
        self.rc_headers = {
            "X-Api-Key": rentcast_key,
            "Accept":    "application/json",
        }
        self.gmaps_key    = gmaps_key
        self.rentcast_key = rentcast_key

    # ── RentCast long-term rental listings ────

    def fetch_by_zip(self, zip_code: str, bedrooms: int | None = None,
                     max_rent: int | None = None, limit: int = 9) -> list[dict]:
        params: dict = {
            "zipCode": zip_code,
            "status":  "Active",
            "limit":   limit,
        }
        if bedrooms:
            params["bedrooms"] = bedrooms
        if max_rent:
            params["maxRent"] = max_rent

        data = _get(
            f"{self.RENTCAST_BASE}/listings/rental/long-term",
            headers=self.rc_headers,
            params=params,
        )
        return self._normalize(data, limit)

    def fetch_by_city(self, city: str, state: str,
                      bedrooms: int = None, limit: int = 9) -> list[dict]:
        params: dict = {
            "city":   city,
            "state":  state,
            "status": "Active",
            "limit":  limit,
        }
        if bedrooms:
            params["bedrooms"] = bedrooms

        data = _get(
            f"{self.RENTCAST_BASE}/listings/rental/long-term",
            headers=self.rc_headers,
            params=params,
        )
        return self._normalize(data, limit)

    def fetch_nearby(self, latitude: float, longitude: float,
                     radius: float = 5.0, limit: int = 9) -> list[dict]:
        params = {
            "latitude":  latitude,
            "longitude": longitude,
            "radius":    radius,
            "status":    "Active",
            "limit":     limit,
        }
        data = _get(
            f"{self.RENTCAST_BASE}/listings/rental/long-term",
            headers=self.rc_headers,
            params=params,
        )
        return self._normalize(data, limit)

    # ── RentCast for-sale listings ────────────

    def fetch_for_sale_by_zip(self, zip_code: str, bedrooms: int | None = None,
                              max_price: int | None = None, limit: int = 9) -> list[dict]:
        params: dict = {"zipCode": zip_code, "status": "Active", "limit": limit}
        if bedrooms:
            params["bedrooms"] = bedrooms
        if max_price:
            params["maxPrice"] = max_price
        data = _get(
            f"{self.RENTCAST_BASE}/listings/sale",
            headers=self.rc_headers,
            params=params,
        )
        return self._normalize(data, limit, is_sale=True)

    def fetch_for_sale_by_city(self, city: str, state: str,
                               bedrooms: int | None = None, limit: int = 9) -> list[dict]:
        params: dict = {"city": city, "state": state, "status": "Active", "limit": limit}
        if bedrooms:
            params["bedrooms"] = bedrooms
        data = _get(
            f"{self.RENTCAST_BASE}/listings/sale",
            headers=self.rc_headers,
            params=params,
        )
        return self._normalize(data, limit, is_sale=True)

    # ── Normalize RentCast response ────────────

    def _normalize(self, data: Optional[dict | list],
                   limit: int, is_sale: bool = False) -> list[dict]:
        if not data:
            return []
        items = data if isinstance(data, list) else data.get("data", [])
        results = []
        for item in items[:limit]:
            addr = (item.get("formattedAddress")
                    or item.get("addressLine1", "Unknown"))
            city  = item.get("city", "")
            state = item.get("state", "")
            full_addr = f"{addr}, {city}, {state}".strip(", ")

            # Collect all listing photos; fall back to Street View only when none exist
            rc_photos = [p for p in (item.get("photoUrls") or item.get("photos") or []) if p]
            photo_urls = rc_photos if rc_photos else [street_view_url(full_addr, self.gmaps_key)]

            results.append({
                "id":            item.get("id") or item.get("listingId", ""),
                "address":       addr,
                "city":          city,
                "state":         state,
                "zip":           item.get("zipCode", ""),
                "full_address":  full_addr,
                "rent":          item.get("price") or item.get("listPrice", 0),
                "beds":          item.get("bedrooms",  0),
                "baths":         item.get("bathrooms", 0),
                "sqft":          item.get("squareFootage", 0),
                "property_type": item.get("propertyType", ""),
                "days_on":       item.get("daysOnMarket", 0),
                "year_built":    item.get("yearBuilt"),
                "latitude":      item.get("latitude"),
                "longitude":     item.get("longitude"),
                "listing_url":   item.get("listingUrl", ""),
                "photo_urls":    photo_urls,           # all photos
                "photo_url":     photo_urls[0],        # primary (backwards-compat)
                "has_rc_photo":  bool(rc_photos),
                "is_sale":       is_sale,
            })
        return results

    # ── Attach Street View to existing listings ─

    def attach_photos(self, listings: list[dict]) -> list[dict]:
        """Backfill Street View for listings that have no listing photos."""
        for listing in listings:
            if not listing.get("has_rc_photo"):
                sv = street_view_url(listing["full_address"], self.gmaps_key)
                listing["photo_url"] = sv
                listing["photo_urls"] = [sv]
        return listings


# ─────────────────────────────────────────────
# Demo listings — shown when no API key set
# ─────────────────────────────────────────────

def _demo(id_, addr, city, state, zip_, rent, beds, baths, sqft, ptype, days, yr, lat, lon):
    full = f"{addr}, {city}, {state}"
    ph = _placeholder_svg(addr)
    return {
        "id": id_, "address": addr, "city": city, "state": state, "zip": zip_,
        "full_address": full, "rent": rent, "beds": beds, "baths": baths, "sqft": sqft,
        "property_type": ptype, "days_on": days, "year_built": yr, "latitude": lat,
        "longitude": lon, "listing_url": "", "has_rc_photo": False,
        "photo_url": ph, "photo_urls": [ph], "is_sale": False,
    }

DEMO_LISTINGS = [
    _demo("demo-1", "4521 W Baseline Rd",  "Phoenix",  "AZ", "85041", 2195, 3, 2.0, 1420, "Single Family", 4,  2003, 33.3495, -112.1401),
    _demo("demo-2", "8830 S 51st Ave",     "Laveen",   "AZ", "85339", 1950, 3, 2.0, 1280, "Single Family", 11, 1998, 33.3601, -112.1522),
    _demo("demo-3", "2340 E Mckellips Rd", "Mesa",     "AZ", "85213", 2450, 4, 2.5, 1850, "Single Family", 2,  2011, 33.4371, -111.7840),
    _demo("demo-4", "1602 N Dysart Rd",    "Avondale", "AZ", "85323", 1875, 3, 2.0, 1310, "Townhouse",     18, 2005, 33.4355, -112.3494),
    _demo("demo-5", "5910 W Ray Rd",       "Chandler", "AZ", "85226", 2650, 4, 3.0, 2100, "Single Family", 7,  2015, 33.3064, -111.9419),
    _demo("demo-6", "3215 S Gilbert Rd",   "Gilbert",  "AZ", "85295", 2300, 3, 2.5, 1650, "Single Family", 14, 2008, 33.3022, -111.7890),
]
