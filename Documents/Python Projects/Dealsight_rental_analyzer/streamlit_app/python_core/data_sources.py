"""
Data Sources Integrations
==========================
Zillow (ZPID/scrape), RentCast API, Census API, ATTOM, FRED
All methods return normalized dicts; callers handle None gracefully.
"""

import os
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Config – set via environment / Streamlit secrets
# ─────────────────────────────────────────────

RENTCAST_KEY   = os.getenv("RENTCAST_API_KEY", "839086d2336e4b3c82b131b99ebc8a81")
ATTOM_KEY      = os.getenv("ATTOM_API_KEY", "fd7b32fdf942d549f4954643886f4dca")
FRED_KEY       = os.getenv("FRED_API_KEY", "")   # free at fred.stlouisfed.org
CENSUS_KEY     = os.getenv("CENSUS_API_KEY", "a66823cd6eaf303640a6c5bb757597ced5c5d2ab")  # free at api.census.gov
RAPIDAPI_KEY   = os.getenv("RAPIDAPI_KEY", "34ac648f6dmsh43b80d9e87aef04p11e08fjsn4a33aea74f55")    # Zillow via RapidAPI


def _get(url: str, headers: dict = None, params: dict = None,
         timeout: int = 10) -> Optional[dict]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"API call failed: {url} → {e}")
        return None


# ─────────────────────────────────────────────
# RentCast  (rentcast.io)
# ─────────────────────────────────────────────

class RentCastClient:
    BASE = "https://api.rentcast.io/v1"

    def __init__(self, api_key: str = RENTCAST_KEY):
        self.headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    def rent_estimate(self, address: str = None,
                      latitude: float = None, longitude: float = None,
                      bedrooms: int = 3, bathrooms: float = 2,
                      property_type: str = "Single Family",
                      square_footage: int = None) -> Optional[dict]:
        params = {
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "propertyType": property_type,
        }
        if address:
            params["address"] = address
        elif latitude and longitude:
            params["latitude"] = latitude
            params["longitude"] = longitude
        if square_footage:
            params["squareFootage"] = square_footage

        data = _get(f"{self.BASE}/avm/rent/long-term",
                    headers=self.headers, params=params)
        if not data:
            return None
        return {
            "rent_low":    data.get("rentRangeLow"),
            "rent_median": data.get("rent"),
            "rent_high":   data.get("rentRangeHigh"),
            "comps":       data.get("comparables", [])[:5],
        }

class RentCastClient:
    BASE = "https://api.rentcast.io/v1"

    def __init__(self, api_key: str = RENTCAST_KEY):
        self.headers = {"X-Api-Key": api_key, "Accept": "application/json"}

    def rent_estimate(self, address: str = None,
                      latitude: float = None, longitude: float = None,
                      bedrooms: int = 3, bathrooms: float = 2,
                      property_type: str = "Single Family",
                      square_footage: int = None) -> Optional[dict]:
        params = {
            "bedrooms":     bedrooms,
            "bathrooms":    bathrooms,
            "propertyType": property_type,
        }
        if address:
            params["address"] = address
        elif latitude and longitude:
            params["latitude"]  = latitude
            params["longitude"] = longitude
        if square_footage:
            params["squareFootage"] = square_footage

        data = _get(f"{self.BASE}/avm/rent/long-term",
                    headers=self.headers, params=params)
        if not data:
            return None
        return {
            "rent_low":    data.get("rentRangeLow"),
            "rent_median": data.get("rent"),
            "rent_high":   data.get("rentRangeHigh"),
            "comps":       data.get("comparables", [])[:5],
        }

    def rent_comps(self, address: str, radius_miles: float = 1.0,
                   bedrooms: int = 3, limit: int = 10) -> Optional[list]:
        params = {
            "address":    address,
            "bedrooms":   bedrooms,
            "radius":     radius_miles,
            "maxResults": limit,
            "compCount":  limit,
        }
        data = _get(f"{self.BASE}/avm/rent/long-term",
                    headers=self.headers, params=params)
        if not data:
            return None

        comparables = data.get("comparables", [])
        if not comparables:
            return None

        return [
            {
                "address":     c.get("formattedAddress") or c.get("addressLine1", ""),
                "rent":        c.get("price")            or c.get("rentAmount"),
                "beds":        c.get("bedrooms"),
                "baths":       c.get("bathrooms"),
                "sqft":        c.get("squareFootage"),
                "days_on":     c.get("daysOnMarket"),
                "distance":    c.get("distance"),
                "correlation": c.get("correlation"),
            }
            for c in comparables[:limit]
        ]

    def property_value(self, address: str) -> Optional[dict]:
        params = {"address": address}
        data = _get(f"{self.BASE}/avm/value",
                    headers=self.headers, params=params)
        if not data:
            return None
        return {
            "value_low":      data.get("priceLow"),
            "value":          data.get("price"),
            "value_high":     data.get("priceHigh"),
            "price_per_sqft": data.get("pricePerSquareFoot"),
        }


# ─────────────────────────────────────────────
# Zillow via RapidAPI (unofficial)
# ─────────────────────────────────────────────

class ZillowClient:
    BASE = "https://zillow-com1.p.rapidapi.com"

    def __init__(self, api_key: str = RAPIDAPI_KEY):
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
        }

    def property_details(self, zpid: str = None,
                         address: str = None) -> Optional[dict]:
        if zpid:
            data = _get(f"{self.BASE}/property",
                        headers=self.headers, params={"zpid": zpid})
        elif address:
            # First search for ZPID
            search = _get(f"{self.BASE}/propertyExtendedSearch",
                          headers=self.headers,
                          params={"location": address, "home_type": "Houses"})
            if not search or not search.get("props"):
                return None
            zpid = search["props"][0].get("zpid")
            if not zpid:
                return None
            data = _get(f"{self.BASE}/property",
                        headers=self.headers, params={"zpid": zpid})
        else:
            return None

        if not data:
            return None
        return {
            "zpid":           data.get("zpid"),
            "address":        data.get("address", {}).get("streetAddress"),
            "city":           data.get("address", {}).get("city"),
            "state":          data.get("address", {}).get("state"),
            "zip":            data.get("address", {}).get("zipcode"),
            "price":          data.get("price"),
            "zestimate":      data.get("zestimate"),
            "rent_zestimate": data.get("rentZestimate"),
            "beds":           data.get("bedrooms"),
            "baths":          data.get("bathrooms"),
            "sqft":           data.get("livingArea"),
            "year_built":     data.get("yearBuilt"),
            "property_type":  data.get("homeType"),
            "tax_annual":     data.get("annualHomeownersInsurance"),
            "hoa":            data.get("monthlyHoaFee"),
            "description":    data.get("description"),
            "photos":         [p.get("url") for p in data.get("photos", [])[:5]],
        }

    def comps(self, zpid: str, count: int = 5) -> Optional[list]:
        data = _get(f"{self.BASE}/similarHomes",
                    headers=self.headers, params={"zpid": zpid, "count": count})
        if not data or not data.get("results"):
            return None
        return [
            {
                "address": c.get("address"),
                "price":   c.get("price"),
                "beds":    c.get("bedrooms"),
                "baths":   c.get("bathrooms"),
                "sqft":    c.get("livingArea"),
            }
            for c in data["results"]
        ]


# ─────────────────────────────────────────────
# ATTOM Data  (attomdata.com)
# ─────────────────────────────────────────────

class ATTOMClient:
    BASE = "https://api.attomdata.com/propertyapi/v1.0.0"

    def __init__(self, api_key: str = ATTOM_KEY):
        self.headers = {
            "apikey": api_key,
            "Accept": "application/json",
        }

    def property_detail(self, address: str, city_state: str) -> Optional[dict]:
        parts = city_state.split(",")
        city = parts[0].strip() if parts else ""
        state = parts[1].strip() if len(parts) > 1 else ""
        params = {
            "address1": address,
            "address2": city_state,
        }
        data = _get(f"{self.BASE}/property/detail",
                    headers=self.headers, params=params)
        if not data or not data.get("property"):
            return None
        p = data["property"][0]
        summary = p.get("summary", {})
        sale = p.get("sale", {})
        assessment = p.get("assessment", {})
        return {
            "attom_id":      p.get("identifier", {}).get("attomId"),
            "year_built":    summary.get("yearBuilt"),
            "sqft":          summary.get("livingSize"),
            "lot_sqft":      summary.get("lotSize"),
            "beds":          summary.get("bedroomsCount"),
            "baths":         summary.get("bathroomCount"),
            "last_sale_price": sale.get("saleAmountData", {}).get("saleAmt"),
            "last_sale_date":  sale.get("saleTransDate"),
            "assessed_value":  assessment.get("assessed", {}).get("assdTtlValue"),
            "market_value":    assessment.get("market", {}).get("mktTtlValue"),
            "tax_amount":      assessment.get("tax", {}).get("taxAmt"),
        }

    def sales_history(self, address: str, city_state: str,
                      years: int = 5) -> Optional[list]:
        params = {"address1": address, "address2": city_state}
        data = _get(f"{self.BASE}/saleshistory/detail",
                    headers=self.headers, params=params)
        if not data or not data.get("property"):
            return None
        sales = data["property"][0].get("saleHistory", [])
        return [
            {
                "date":  s.get("saleTransDate"),
                "price": s.get("saleAmountData", {}).get("saleAmt"),
                "type":  s.get("saleTransType"),
            }
            for s in sales[:years * 2]
        ]


# ─────────────────────────────────────────────
# FRED (Federal Reserve Economic Data)
# ─────────────────────────────────────────────

class FREDClient:
    BASE = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str = FRED_KEY):
        self.api_key = api_key

    def _series(self, series_id: str, limit: int = 1,
                sort_order: str = "desc") -> Optional[list]:
        params = {
            "series_id":  series_id,
            "api_key":    self.api_key,
            "file_type":  "json",
            "limit":      limit,
            "sort_order": sort_order,
        }
        data = _get(f"{self.BASE}/series/observations", params=params)
        if not data:
            return None
        return data.get("observations", [])

    def mortgage_30yr_fixed(self) -> Optional[float]:
        obs = self._series("MORTGAGE30US")
        return float(obs[0]["value"]) / 100 if obs and obs[0]["value"] != "." else None

    def mortgage_15yr_fixed(self) -> Optional[float]:
        obs = self._series("MORTGAGE15US")
        return float(obs[0]["value"]) / 100 if obs and obs[0]["value"] != "." else None

    def federal_funds_rate(self) -> Optional[float]:
        obs = self._series("FEDFUNDS")
        return float(obs[0]["value"]) / 100 if obs and obs[0]["value"] != "." else None

    def cpi_inflation(self) -> Optional[float]:
        obs = self._series("CPIAUCSL")
        return float(obs[0]["value"]) if obs and obs[0]["value"] != "." else None

    def unemployment_rate(self) -> Optional[float]:
        obs = self._series("UNRATE")
        return float(obs[0]["value"]) if obs and obs[0]["value"] != "." else None

    def hpi_us(self) -> Optional[float]:
        """House Price Index – national"""
        obs = self._series("USSTHPI")
        return float(obs[0]["value"]) if obs and obs[0]["value"] != "." else None

    def get_market_summary(self) -> dict:
        return {
            "mortgage_30yr":    self.mortgage_30yr_fixed(),
            "mortgage_15yr":    self.mortgage_15yr_fixed(),
            "fed_funds_rate":   self.federal_funds_rate(),
            "cpi":              self.cpi_inflation(),
            "unemployment":     self.unemployment_rate(),
            "house_price_index": self.hpi_us(),
        }


# ─────────────────────────────────────────────
# Census API  (data.census.gov)
# ─────────────────────────────────────────────

class CensusClient:
    BASE = "https://api.census.gov/data"

    def __init__(self, api_key: str = CENSUS_KEY):
        self.api_key = api_key

    def acs_zip(self, zip_code: str) -> Optional[dict]:
        """
        American Community Survey 5-year for a ZIP (ZCTA).
        Variables: median household income, median gross rent, vacancy rate, population.
        """
        params = {
            "get": "B19013_001E,B25064_001E,B25002_003E,B01003_001E",
            "for": f"zip code tabulation area:{zip_code}",
            "key": self.api_key,
        }
        data = _get(f"{self.BASE}/2022/acs/acs5", params=params)
        if not data or len(data) < 2:
            return None
        headers, values = data[0], data[1]
        mapping = {
            "B19013_001E": "median_household_income",
            "B25064_001E": "median_gross_rent",
            "B25002_003E": "vacant_housing_units",
            "B01003_001E": "population",
        }
        return {mapping.get(k, k): v for k, v in zip(headers, values)
                if k in mapping}

    def county_population_trend(self, state_fips: str,
                                 county_fips: str) -> Optional[dict]:
        """Population growth estimate for a county."""
        params = {
            "get": "NAME,POP_2022,POP_2021,POP_2020",
            "for": f"county:{county_fips}",
            "in":  f"state:{state_fips}",
            "key": self.api_key,
        }
        data = _get(f"{self.BASE}/2022/pep/population", params=params)
        if not data or len(data) < 2:
            return None
        h, v = data[0], data[1]
        result = dict(zip(h, v))
        try:
            growth = ((int(result.get("POP_2022", 0)) -
                       int(result.get("POP_2020", 0))) /
                      max(int(result.get("POP_2020", 1)), 1)) * 100
            result["pop_growth_2yr_pct"] = round(growth, 2)
        except Exception:
            pass
        return result


# ─────────────────────────────────────────────
# Unified Lookup  (convenience wrapper)
# ─────────────────────────────────────────────

class PropertyDataAggregator:
    """
    Single call to enrich a property address with data from all sources.
    Gracefully degrades if any API key is missing.
    """

    def __init__(self):
        self.rentcast = RentCastClient() if RENTCAST_KEY else None
        self.zillow   = ZillowClient()  if RAPIDAPI_KEY  else None
        self.attom    = ATTOMClient()   if ATTOM_KEY     else None
        self.fred     = FREDClient()    if FRED_KEY      else None
        self.census   = CensusClient()  if CENSUS_KEY    else None

    def enrich(self, address: str, city_state: str,
               zip_code: str = "", bedrooms: int = 3,
               bathrooms: float = 2) -> dict:
        result: dict = {"address": address, "city_state": city_state}

        # RentCast rent estimate
        if self.rentcast:
            full_addr = f"{address}, {city_state}"
            rc = self.rentcast.rent_estimate(address=full_addr,
                                             bedrooms=bedrooms,
                                             bathrooms=bathrooms)
            if rc:
                result["rentcast"] = rc

        # Zillow property details
        if self.zillow:
            full_addr = f"{address}, {city_state}"
            zd = self.zillow.property_details(address=full_addr)
            if zd:
                result["zillow"] = zd

        # ATTOM detail + tax history
        if self.attom:
            ad = self.attom.property_detail(address, city_state)
            if ad:
                result["attom"] = ad

        # FRED macro data
        if self.fred:
            result["macro"] = self.fred.get_market_summary()

        # Census ZIP data
        if self.census and zip_code:
            cd = self.census.acs_zip(zip_code)
            if cd:
                result["census"] = cd

        return result
