"""
Rental Property Deal Analyzer - Core Calculations Engine
=========================================================
All financial metrics: cash flow, cap rate, DSCR, CoC, BRRRR, STR/Airbnb
"""

from dataclasses import dataclass
from typing import Optional
import math


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class PropertyInputs:
    # Purchase
    purchase_price: float
    down_payment_pct: float          # e.g. 0.20 for 20%
    closing_costs: float             # absolute $
    rehab_costs: float = 0.0
    after_repair_value: float = 0.0  # BRRRR

    # Financing
    loan_interest_rate: float = 0.07  # 7%
    loan_term_years: int = 30
    is_interest_only: bool = False

    # Income
    monthly_rent: float = 0.0
    other_monthly_income: float = 0.0  # laundry, parking, etc.

    # STR / Airbnb
    str_nightly_rate: float = 0.0
    str_occupancy_rate: float = 0.65   # 65% default
    str_platform_fee_pct: float = 0.03  # 3% host fee
    str_cleaning_fee: float = 85.0
    str_avg_stay_nights: float = 3.0

    # Expenses (monthly, unless noted)
    property_tax_annual: float = 0.0
    insurance_annual: float = 0.0
    hoa_monthly: float = 0.0
    property_mgmt_pct: float = 0.10   # 10% of gross rent
    vacancy_rate: float = 0.05        # 5%
    maintenance_pct: float = 0.05     # 5% of gross rent (CapEx + Repairs)
    capex_monthly: float = 0.0        # explicit override
    utilities_monthly: float = 0.0

    # BRRRR refinance
    refi_ltv: float = 0.75
    refi_interest_rate: float = 0.07
    refi_term_years: int = 30
    refi_closing_costs: float = 3000.0


@dataclass(frozen=True)
class BRRRRResult:
    arv: float
    refi_loan_amount: float
    refi_monthly_payment: float
    cash_out_at_refi: float
    refi_closing_costs: float
    cash_left_in_deal: float
    post_refi_monthly_cf: float
    post_refi_coc_return: float
    equity_captured: float
    total_profit_if_sold: float
    infinite_returns: bool


@dataclass
class DealMetrics:
    # Inputs echo
    purchase_price: float
    total_cash_invested: float
    down_payment: float
    loan_amount: float
    monthly_payment: float

    # Income
    gross_monthly_income: float
    effective_gross_income: float   # after vacancy

    # Expenses
    total_monthly_expenses: float
    expense_breakdown: dict

    # Core Metrics
    monthly_cash_flow: float
    annual_cash_flow: float
    cap_rate: float                 # %
    cash_on_cash_return: float      # %
    dscr: float
    gross_rent_multiplier: float
    net_operating_income: float     # annual

    # Ratios
    expense_ratio: float
    break_even_occupancy: float

    # STR
    str_monthly_revenue: float = 0.0
    str_annual_revenue: float = 0.0
    str_monthly_cash_flow: float = 0.0
    str_coc_return: float = 0.0

    # BRRRR
    brrrr: Optional[BRRRRResult] = None


# ─────────────────────────────────────────────
# Grading thresholds
# ─────────────────────────────────────────────
_CF_A,   _CF_B                  = 300,  100
_CR_A,   _CR_B,   _CR_C         = 8.0,  6.0,  4.0
_COC_A,  _COC_B,  _COC_C        = 12.0, 8.0,  5.0
_DSCR_A, _DSCR_B, _DSCR_C       = 1.25, 1.10, 1.0
_GRM_A,  _GRM_B,  _GRM_C        = 8.0,  12.0, 16.0
_STR_SUPPLIES   = 200
_STR_UTIL_EXTRA = 100


# ─────────────────────────────────────────────
# Shared mortgage payment formula
# ─────────────────────────────────────────────
def _calc_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    r, n = annual_rate / 12, years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


# ─────────────────────────────────────────────
# Calculation Engine
# ─────────────────────────────────────────────

class DealAnalyzer:

    def __init__(self, inputs: PropertyInputs):
        self.i = inputs

    # ── Financing ──────────────────────────────

    def _down_payment(self) -> float:
        return self.i.purchase_price * self.i.down_payment_pct

    def _loan_amount(self) -> float:
        return self.i.purchase_price - self._down_payment()

    def _monthly_payment(self, principal: float, annual_rate: float,
                          years: int, interest_only: bool = False) -> float:
        if interest_only:
            return principal * (annual_rate / 12) if principal > 0 else 0.0
        return _calc_payment(principal, annual_rate, years)

    # ── Income ──────────────────────────────────

    def _gross_monthly_income(self) -> float:
        return self.i.monthly_rent + self.i.other_monthly_income

    def _effective_gross_income_monthly(self) -> float:
        return self._gross_monthly_income() * (1 - self.i.vacancy_rate)

    # ── Expenses ────────────────────────────────

    def _expense_breakdown_monthly(self) -> dict:
        gross = self._gross_monthly_income()
        loan = self._loan_amount()
        payment = self._monthly_payment(loan, self.i.loan_interest_rate,
                                         self.i.loan_term_years,
                                         self.i.is_interest_only)

        mgmt = gross * self.i.property_mgmt_pct
        vacancy = gross * self.i.vacancy_rate
        maintenance = gross * self.i.maintenance_pct if self.i.capex_monthly == 0 else self.i.capex_monthly
        prop_tax = self.i.property_tax_annual / 12
        insurance = self.i.insurance_annual / 12

        return {
            "mortgage": round(payment, 2),
            "property_tax": round(prop_tax, 2),
            "insurance": round(insurance, 2),
            "hoa": round(self.i.hoa_monthly, 2),
            "property_mgmt": round(mgmt, 2),
            "vacancy": round(vacancy, 2),
            "maintenance_capex": round(maintenance, 2),
            "utilities": round(self.i.utilities_monthly, 2),
        }

    def _total_monthly_expenses(self, breakdown: dict) -> float:
        return sum(breakdown.values())

    # ── NOI & Core Metrics ───────────────────────

    def _noi_annual(self) -> float:
        gross_annual = self._effective_gross_income_monthly() * 12
        opex = self._expense_breakdown_monthly()
        # NOI excludes debt service
        annual_opex = (sum(opex.values()) - opex["mortgage"]) * 12
        return gross_annual - annual_opex

    def _cap_rate(self) -> float:
        if self.i.purchase_price == 0:
            return 0.0
        noi = self._noi_annual()
        return (noi / self.i.purchase_price) * 100

    def _total_cash_invested(self) -> float:
        return (self._down_payment() + self.i.closing_costs
                + self.i.rehab_costs)

    def _cash_on_cash(self, annual_cf: float) -> float:
        total_cash = self._total_cash_invested()
        if total_cash == 0:
            return 0.0
        return (annual_cf / total_cash) * 100

    def _dscr(self) -> float:
        noi = self._noi_annual()
        annual_debt = self._monthly_payment(
            self._loan_amount(), self.i.loan_interest_rate,
            self.i.loan_term_years, self.i.is_interest_only) * 12
        if annual_debt == 0:
            return float("inf")
        return noi / annual_debt

    def _grm(self) -> float:
        annual_rent = self._gross_monthly_income() * 12
        if annual_rent == 0:
            return 0.0
        return self.i.purchase_price / annual_rent

    def _break_even_occupancy(self, breakdown: dict) -> float:
        """What occupancy is needed to cover all expenses?"""
        total_opex_no_vacancy = sum(v for k, v in breakdown.items()
                                    if k != "vacancy")
        gross = self._gross_monthly_income()
        if gross == 0:
            return 1.0
        return min(total_opex_no_vacancy / gross, 1.0)

    # ── STR / Airbnb ─────────────────────────────

    def _str_monthly_revenue(self) -> float:
        nights_per_month = 30 * self.i.str_occupancy_rate
        turns_per_month = nights_per_month / self.i.str_avg_stay_nights
        nightly_income = nights_per_month * self.i.str_nightly_rate
        cleaning_income = turns_per_month * self.i.str_cleaning_fee
        gross = (nightly_income + cleaning_income)
        platform_fee = gross * self.i.str_platform_fee_pct
        return gross - platform_fee

    def _str_cash_flow_monthly(self, base_breakdown: dict) -> float:
        str_rev = self._str_monthly_revenue()
        # STR replaces long-term rent in expenses
        breakdown = dict(base_breakdown)
        breakdown["property_mgmt"] = 0.0  # usually self-managed for STR
        breakdown["vacancy"] = 0.0         # occupancy already factored
        total_exp = sum(breakdown.values())
        return str_rev - total_exp - _STR_SUPPLIES - _STR_UTIL_EXTRA

    # ── BRRRR Analysis ───────────────────────────

    def _brrrr_analysis(self) -> Optional[BRRRRResult]:
        arv = self.i.after_repair_value
        if arv <= 0:
            return None

        refi_loan = arv * self.i.refi_ltv
        refi_payment = self._monthly_payment(refi_loan, self.i.refi_interest_rate,
                                              self.i.refi_term_years)
        cash_out = refi_loan - self._loan_amount()
        total_invested = self._total_cash_invested()
        cash_left_in = max(total_invested - cash_out - self.i.refi_closing_costs, 0)

        breakdown = self._expense_breakdown_monthly()
        breakdown["mortgage"] = refi_payment
        egi_monthly = self._effective_gross_income_monthly()
        post_refi_cf = egi_monthly - sum(breakdown.values())
        post_refi_coc = ((post_refi_cf * 12) / cash_left_in * 100
                         if cash_left_in > 100 else float("inf"))

        equity_captured = arv - self.i.purchase_price - self.i.rehab_costs

        return BRRRRResult(
            arv=arv,
            refi_loan_amount=round(refi_loan, 2),
            refi_monthly_payment=round(refi_payment, 2),
            cash_out_at_refi=round(cash_out, 2),
            refi_closing_costs=self.i.refi_closing_costs,
            cash_left_in_deal=round(cash_left_in, 2),
            post_refi_monthly_cf=round(post_refi_cf, 2),
            post_refi_coc_return=round(post_refi_coc, 2),
            equity_captured=round(equity_captured, 2),
            total_profit_if_sold=round(equity_captured - self.i.closing_costs, 2),
            infinite_returns=cash_left_in < 100,
        )

    # ── Main Analyze ─────────────────────────────

    def analyze(self) -> DealMetrics:
        down = self._down_payment()
        loan = self._loan_amount()
        payment = self._monthly_payment(loan, self.i.loan_interest_rate,
                                         self.i.loan_term_years,
                                         self.i.is_interest_only)
        breakdown = self._expense_breakdown_monthly()
        total_exp = self._total_monthly_expenses(breakdown)
        egi = self._effective_gross_income_monthly()
        gross = self._gross_monthly_income()

        monthly_cf = egi - total_exp
        annual_cf = monthly_cf * 12
        noi = self._noi_annual()

        # STR
        str_rev = self._str_monthly_revenue()
        str_cf = self._str_cash_flow_monthly(breakdown)
        str_coc = (str_cf * 12 / self._total_cash_invested() * 100
                   if self._total_cash_invested() > 0 else 0)

        return DealMetrics(
            purchase_price=self.i.purchase_price,
            total_cash_invested=round(self._total_cash_invested(), 2),
            down_payment=round(down, 2),
            loan_amount=round(loan, 2),
            monthly_payment=round(payment, 2),
            gross_monthly_income=round(gross, 2),
            effective_gross_income=round(egi, 2),
            total_monthly_expenses=round(total_exp, 2),
            expense_breakdown={k: round(v, 2) for k, v in breakdown.items()},
            monthly_cash_flow=round(monthly_cf, 2),
            annual_cash_flow=round(annual_cf, 2),
            cap_rate=round(self._cap_rate(), 2),
            cash_on_cash_return=round(self._cash_on_cash(annual_cf), 2),
            dscr=round(self._dscr(), 3),
            gross_rent_multiplier=round(self._grm(), 2),
            net_operating_income=round(noi, 2),
            expense_ratio=round(total_exp / gross * 100 if gross > 0 else 0, 1),
            break_even_occupancy=round(self._break_even_occupancy(breakdown) * 100, 1),
            str_monthly_revenue=round(str_rev, 2),
            str_annual_revenue=round(str_rev * 12, 2),
            str_monthly_cash_flow=round(str_cf, 2),
            str_coc_return=round(str_coc, 2),
            brrrr=self._brrrr_analysis(),
        )


# ─────────────────────────────────────────────
# Amortization Schedule
# ─────────────────────────────────────────────

def amortization_schedule(principal: float, annual_rate: float,
                           years: int) -> list[dict]:
    payment = _calc_payment(principal, annual_rate, years)
    r = annual_rate / 12
    n = years * 12
    balance = principal
    rows = []
    total_interest = 0.0
    for month in range(1, n + 1):
        interest = balance * r
        principal_paid = payment - interest
        balance -= principal_paid
        total_interest += interest
        rows.append({
            "month": month,
            "year": math.ceil(month / 12),
            "payment": round(payment, 2),
            "principal": round(principal_paid, 2),
            "interest": round(interest, 2),
            "balance": round(max(balance, 0), 2),
            "total_interest_paid": round(total_interest, 2),
        })
    return rows


# ─────────────────────────────────────────────
# Rule-of-Thumb Graders
# ─────────────────────────────────────────────

def grade_deal(metrics: DealMetrics) -> dict:
    grades = {}

    cf = metrics.monthly_cash_flow
    if cf >= _CF_A:
        grades["cash_flow"] = ("A", "Strong positive cash flow")
    elif cf >= _CF_B:
        grades["cash_flow"] = ("B", "Marginally positive cash flow")
    elif cf >= 0:
        grades["cash_flow"] = ("C", "Break-even – watch expenses")
    else:
        grades["cash_flow"] = ("F", "Negative cash flow – avoid")

    cr = metrics.cap_rate
    if cr >= _CR_A:
        grades["cap_rate"] = ("A", "Excellent cap rate (≥8%)")
    elif cr >= _CR_B:
        grades["cap_rate"] = ("B", "Good cap rate (6-8%)")
    elif cr >= _CR_C:
        grades["cap_rate"] = ("C", "Below average (4-6%)")
    else:
        grades["cap_rate"] = ("F", "Poor cap rate (<4%)")

    coc = metrics.cash_on_cash_return
    if coc >= _COC_A:
        grades["coc"] = ("A", "Excellent CoC (≥12%)")
    elif coc >= _COC_B:
        grades["coc"] = ("B", "Good CoC (8-12%)")
    elif coc >= _COC_C:
        grades["coc"] = ("C", "Acceptable CoC (5-8%)")
    else:
        grades["coc"] = ("F", "Poor CoC (<5%)")

    dscr = metrics.dscr
    if dscr >= _DSCR_A:
        grades["dscr"] = ("A", "Lender-friendly DSCR (≥1.25)")
    elif dscr >= _DSCR_B:
        grades["dscr"] = ("B", "Adequate DSCR (1.10-1.25)")
    elif dscr >= _DSCR_C:
        grades["dscr"] = ("C", "Risky – barely covers debt")
    else:
        grades["dscr"] = ("F", "DSCR below 1.0 – loan risk")

    grm = metrics.gross_rent_multiplier
    if grm <= _GRM_A:
        grades["grm"] = ("A", "Excellent GRM (≤8)")
    elif grm <= _GRM_B:
        grades["grm"] = ("B", "Good GRM (8-12)")
    elif grm <= _GRM_C:
        grades["grm"] = ("C", "Average GRM (12-16)")
    else:
        grades["grm"] = ("F", "High GRM (>16) – overpriced")

    return grades
