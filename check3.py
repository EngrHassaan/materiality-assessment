# -*- coding: utf-8 -*-
"""
Interactive ESGFP scoring with:
- AHP/FAHP key-issue weighting per pillar (multi-method + visuals)
- Indicator-based scoring (IS/GM/PS pipeline) using your formulas
- Scenarios (MCDA methods) + Validation (DEA extended + Monte-Carlo)
- + NEW: SMAA (Stochastic Multicriteria Acceptability Analysis)
- + NEW: Weight Stability Intervals (Critical Weight Analysis)

NOTE: No files are saved. All outputs display on screen only.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Sequence, Any
import io
import math
import random
import re
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Plot style (professional)
# =============================================================================
def apply_pro_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
            "figure.titlesize": 16,
            "axes.grid": True,
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
            "axes.axisbelow": True,
        }
    )


# =============================================================================
# Input helpers
# =============================================================================
GE_SCALE_HINT = "GE scale (0–10): High=9.00, Moderate=7.50, Low-to-Moderate=5.00, Low=2.50"

EXPOSURE_MAP: Dict[str, float] = {
    "high": 9.0,
    "high exposure": 9.0,
    "moderate": 7.5,
    "moderate exposure": 7.5,
    "moderate to lower": 5.0,
    "low to moderate": 5.0,
    "low to moderate exposure": 5.0,
    "lower": 2.5,
    "low": 2.5,
    "low exposure": 2.5,
    "9": 9.0,
    "7.5": 7.5,
    "5": 5.0,
    "2.5": 2.5,
}


def _is_help(s: str) -> bool:
    return s.strip().lower() in {"help", "?", "h"}


def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        ans = safe_input(f"{prompt} [{d}]: ").strip().lower()
        if not ans:
            return default
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please enter y or n.")


def prompt_int(prompt: str, min_val: int, max_val: int) -> int:
    while True:
        raw = safe_input(prompt).strip()
        if _is_help(raw):
            print(f"Hint: enter an integer in [{min_val}, {max_val}].")
            continue
        try:
            v = int(raw)
            if min_val <= v <= max_val:
                return v
            print(f"❌ Enter integer in [{min_val}, {max_val}]")
        except ValueError:
            print("❌ Invalid integer. Type 'help' for guidance.")


def prompt_float(
    prompt: str,
    lo: float,
    hi: float,
    inclusive_low: bool = True,
    inclusive_high: bool = True,
) -> float:
    while True:
        raw = safe_input(prompt).strip()
        if _is_help(raw):
            print(
                f"Hint: enter a number in {'[' if inclusive_low else '('}{lo}, {hi}{']' if inclusive_high else ')'}"
            )
            continue
        try:
            v = float(raw)
            ok_lo = v >= lo if inclusive_low else v > lo
            ok_hi = v <= hi if inclusive_high else v < hi
            if ok_lo and ok_hi:
                return v
            bounds = f"{'[' if inclusive_low else '('}{lo}, {hi}{']' if inclusive_high else ')'}"
            print(f"❌ Enter number in {bounds}")
        except ValueError:
            print("❌ Invalid number. Type 'help' for guidance.")


def prompt_float_or_default(prompt: str, default: float, lo: float, hi: float) -> float:
    while True:
        raw = safe_input(f"{prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        if _is_help(raw):
            print(f"Hint: press Enter to use default. Otherwise enter a number in [{lo}, {hi}].")
            continue
        try:
            v = float(raw)
            if lo <= v <= hi:
                return v
            print(f"❌ Enter number in [{lo}, {hi}]")
        except ValueError:
            print("❌ Invalid number. Type 'help' or press Enter for default.")


def prompt_str_nonempty(prompt: str, default: str) -> str:
    raw = safe_input(f"{prompt} [default {default}]: ").strip()
    return raw or default


def prompt_exposure(prompt: str) -> float:
    """Accept label shortcuts or any numeric in [0,10]."""
    while True:
        print(f"    {GE_SCALE_HINT}")
        raw = safe_input(prompt).strip().lower()
        if _is_help(raw):
            print(f"Hint: type high/moderate/low to moderate/low or any number in [0,10].")
            print(f"{GE_SCALE_HINT}")
            continue
        if raw in EXPOSURE_MAP:
            return float(EXPOSURE_MAP[raw])
        try:
            if raw.startswith("."):
                raw = "0" + raw
            v = float(raw)
            if 0.0 <= v <= 10.0:
                return v
        except ValueError:
            pass
        print("❌ Use: high/moderate/low to moderate/low (or numeric ∈ [0,10]).")


def prompt_comment() -> str:
    return safe_input("Any comment for this input? (press Enter to skip): ").strip()


def ask_gm_sign_each_time(context: str) -> int:
    print(f"\nGM modifier sign for PS = IS ± GM ({context})")
    gm_choice = safe_input("Use GM as [+] add (default) or [-] subtract? [+/-]: ").strip()
    return -1 if gm_choice.strip() == "-" else 1


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def ask_choice(prompt: str, choices: Sequence[str], allow_blank: bool = False) -> str:
    choices_lower = {c.lower(): c for c in choices}
    while True:
        ans = safe_input(prompt).strip()
        if allow_blank and ans == "":
            return ""
        if ans.lower() in choices_lower:
            return choices_lower[ans.lower()]
        print(f"Choose one of: {', '.join(choices)}")


def ask_int(prompt: str, min_value: int, max_value: int, default: Optional[int] = None) -> int:
    while True:
        ans = safe_input(prompt).strip()
        if ans == "" and default is not None:
            return default
        try:
            v = int(ans)
        except ValueError:
            print("Enter an integer.")
            continue
        if min_value <= v <= max_value:
            return v
        print(f"Enter a value between {min_value} and {max_value}.")


# =============================================================================
# Indicator model
# =============================================================================
@dataclass(frozen=True)
class IndicatorDef:
    pillar: str
    key_issue: str
    indicator: str
    unit: str
    formula_desc: str
    criteria: str
    default_mode: str  # "A" | "B" | "C"
    higher_is_better: bool


Model = Dict[str, Dict[str, List[IndicatorDef]]]  # pillar -> key_issue -> indicators


RAW_INDICATORS_TSV = """Pillar\tKeyIssue\tIndicator\tUnit\tHigherIsBetter
Environment\tCarbon Efficiency\tNet Carbon Avoided Cost\tUSD/metric ton CO2-e\t0
Environment\tCarbon Efficiency\tTotal Carbon Emissions (Scope 1 & 2)\tmetric tons CO2-e\t0
Environment\tCarbon Efficiency\tCarbon Intensity per Unit\tkg CO2/ton product\t0
Environment\tEnergy Efficiency\tSpecific Energy Consumption\tMJ/ton product\t0
Environment\tEnergy Efficiency\tRenewable Energy Utilization\t% of total energy\t1
Environment\tWater Management\tWater Intensity\tm3/ton product\t0
Environment\tWater Management\tWater Stress Impact\tindex score\t0
Environment\tWaste Management\tWaste-to-Product Conversion\t% conversion\t1
Environment\tWaste Management\tHazardous Waste Generation\tkg/ton product\t0
Environment\tWaste Management\tRecyclable Input Material\t% recycled\t1
Environment\tOperational Efficiency\tProcess Downtime\t% downtime\t0
Environment\tOperational Efficiency\tMaterial Conversion Efficiency\t% conversion\t1
Environment\tOperational Efficiency\tUnit Production Cost\tUSD/ton\t0
Environment\tEnergy Optimization\tEnergy Efficiency Improvement\t% improvement\t1
Environment\tPollution Control\tProcess-Related Air Pollutants\tkg/ton product\t0
Environment\tClean Technology\tAdoption of Cleaner Technologies\t% processes\t1
Environment\tSustainable Products\tRevenue from Green Products\t% revenue\t1
Environment\tR&D Investment\tInvestment in Sustainable Technology\t% revenue\t1
Environment\tLifecycle Impact\tProduct Carbon Footprint\tkg CO2-e/unit\t0
Environment\tEnvironmental Sustainability (SGI)\tPM2.5 / Air Pollution Exposure\tug/m3\t0
Social\tOccupational Health & Safety\tInherent Safety Index (ISI)\tindex score\t1
Social\tOccupational Health & Safety\tOHS Score\tscore (0-100)\t1
Social\tOccupational Health & Safety\tFatal Occupational Injuries\tper 100,000 workers\t0
Social\tOccupational Health & Safety\tNon-fatal Occupational Injuries\tper 100,000 workers\t0
Social\tOccupational Health & Safety\tLabor Inspection Rate\tinspections/1000 employees\t1
Social\tEmployment\tUnemployment Rate\t%\t0
Social\tEmployment\tDirect & Indirect Jobs\tnumber\t1
Social\tEmployment\tEmployment Score\tscore (0-100)\t1
Social\tSocial Protection\tPopulation Covered by Social Protection\t% population\t1
Social\tLabor Rights\tCompliance with Labor Rights\tscore (0-100)\t1
Social\tCommunity Impact\tPopulation Exposure Index\tindex\t0
Social\tCommunity Impact\tSocial Sustainability (SGI)\tindex\t1
Governance\tGender Equality\tFemale to Male Labor Force Participation Ratio\tratio\t1
Governance\tGender Equality\tWomen in Management Positions\t%\t1
Governance\tRegulatory Quality\tRegulatory Quality Estimate\tindex\t1
Governance\tRights\tEconomic & Social Rights Score\tindex\t1
Governance\tInnovation\tR&D Expenditure\t% GDP\t1
Governance\tTrade & Logistics\tLead Time to Export\tdays\t0
Governance\tTrade & Logistics\tLead Time to Import\tdays\t0
Governance\tTrade & Logistics\tLogistics Performance Index\t1-5\t1
Governance\tGovernance Burden\tTime Dealing with Regulators\t% management time\t0
Governance\tGender Inclusion\tFirms with Female Top Manager\t% firms\t1
Governance\tGender Inclusion\tFirms with Female Ownership\t% firms\t1
Governance\tFinance Access\tFirms Using Banks for Working Capital\t% firms\t1
Governance\tLabor Market\tFemale Labor Force Participation\t%\t1
Governance\tCybersecurity\tCyber Crisis Management (NCSI)\tindex\t1
Governance\tCybersecurity\tCyber Incident Response Capacity\tindex\t1
Governance\tCybersecurity\tProtection of Personal Data\tindex\t1
Governance\tCybersecurity\tCyber Threat Awareness\tindex\t1
Governance\tDigitalization\tDigital Development Level\tindex\t1
Governance\tAccountability\tConsensus Building (SGI)\tindex\t1
Governance\tAccountability\tHorizontal Accountability\tindex\t1
Governance\tAccountability\tDiagonal Accountability\tindex\t1
Governance\tBusiness Environment\tStarting a Business\tindex\t1
Governance\tBusiness Environment\tDealing with Construction Permits\tindex\t1
Governance\tBusiness Environment\tGetting Electricity\tindex\t1
Governance\tBusiness Environment\tRegistering Property\tindex\t1
Governance\tBusiness Environment\tGetting Credit\tindex\t1
Governance\tBusiness Environment\tProtecting Minority Investors\tindex\t1
Governance\tBusiness Environment\tGINI Index\tindex\t0
Governance\tBusiness Environment\tPaying Taxes\tindex\t1
Governance\tBusiness Environment\tTrading Across Borders\tindex\t1
Governance\tBusiness Environment\tEnforcing Contracts\tindex\t1
Governance\tBusiness Environment\tResolving Insolvency\tindex\t1
Governance\tPolicy Quality\tSustainable Policymaking (SGI)\tindex\t1
Governance\tPolicy Quality\tEconomic Sustainability (SGI)\tindex\t1
Finance\tESG Financing\tESG-Linked Financing\tUSD (million)\t1
Finance\tCost Structure\tTotal Cost\tUSD (million)\t0
Finance\tReturns\tROI\t%\t1
Finance\tRisk\tNPV\tUSD (million)\t1
Finance\tRisk\tIRR\t%\t1
Process\tMaterials\tEquipment Fabrication Material (encoded)\tscore\t1
Process\tMaterials\tCorrosion Rate\tmm/year\t0
Process\tEnergy\tSpecific Energy Consumption\tMJ/kg\t0
Process\tHazard\tChemical Hazard Risk\trisk score\t0
"""


def _default_mode_from_row(indicator: str, unit: str, higher_is_better: bool) -> str:
    txt = f"{indicator} {unit}".lower()
    if "rank" in txt or "index" in txt:
        return "C"
    return "A" if higher_is_better else "B"


def _default_formula_desc(mode: str) -> str:
    if mode == "A":
        return "Higher-is-better scoring (CS uses 30+60×normalized for multi; CS=90 for single)."
    if mode == "B":
        return "Lower-is-better scoring (CS uses 30+60×normalized for multi; CS=90 for single)."
    return "Index/ranking scoring to deciles (0..90)."


def parse_indicator_model(raw_tsv: str) -> Model:
    df = pd.read_csv(io.StringIO(raw_tsv), sep="\t")

    df["Pillar"] = df["Pillar"].astype(str).str.strip()
    df["KeyIssue"] = df["KeyIssue"].astype(str).str.strip()
    df["Indicator"] = df["Indicator"].astype(str).str.strip()
    df["Unit"] = df["Unit"].astype(str).str.strip()
    df["HigherIsBetter"] = df["HigherIsBetter"].astype(int)

    if "FormulaDesc" not in df.columns:
        df["FormulaDesc"] = ""
    if "Criteria" not in df.columns:
        df["Criteria"] = ""
    if "DefaultMode" not in df.columns:
        df["DefaultMode"] = ""

    model: Model = {}
    for _, r in df.iterrows():
        hib = bool(int(r["HigherIsBetter"]))
        default_mode = str(r.get("DefaultMode", "")).strip().upper()
        if default_mode not in {"A", "B", "C"}:
            default_mode = _default_mode_from_row(str(r["Indicator"]), str(r["Unit"]), hib)

        formula_desc = str(r.get("FormulaDesc", "")).strip() or _default_formula_desc(default_mode)
        criteria = str(r.get("Criteria", "")).strip() or "Criterion"

        idef = IndicatorDef(
            pillar=str(r["Pillar"]),
            key_issue=str(r["KeyIssue"]),
            indicator=str(r["Indicator"]),
            unit=str(r["Unit"]),
            formula_desc=formula_desc,
            criteria=criteria,
            default_mode=default_mode,
            higher_is_better=hib,
        )
        model.setdefault(idef.pillar, {}).setdefault(idef.key_issue, []).append(idef)

    for pillar in model:
        for key_issue in model[pillar]:
            model[pillar][key_issue] = sorted(model[pillar][key_issue], key=lambda x: x.indicator.lower())

    return dict(sorted(model.items(), key=lambda kv: kv[0].lower()))


def print_model_structure(model: Model) -> None:
    _print_header("Built-in structure (Pillars → Key Issues → Indicators + metadata)")
    for pillar in sorted(model.keys()):
        print(f"\n📌 {pillar}")
        issues = model[pillar]
        for ki in sorted(issues.keys()):
            inds = issues[ki]
            print(f"  • {ki} ({len(inds)} indicators)")
            for idef in inds:
                direction = "higher is better" if idef.higher_is_better else "lower is better"
                print(f"     - Indicator: {idef.indicator}")
                print(f"       Unit: {idef.unit}")
                print(f"       Criteria: {idef.criteria}")
                print(f"       Default mode: {idef.default_mode} ({direction})")
                print(f"       Formula/Description: {idef.formula_desc}")


def _pillars_to_issues_from_model(model: Model) -> Dict[str, List[str]]:
    return {p: sorted(list(issues.keys())) for p, issues in model.items()}


def apply_pillar_issue_scope_to_model(model: Model, pillars_to_issues: Dict[str, List[str]]) -> Model:
    new_model: Model = {}
    for pillar in sorted(pillars_to_issues.keys()):
        issues_list = pillars_to_issues.get(pillar, [])
        new_model[pillar] = {}
        if pillar in model:
            for ki in sorted(issues_list):
                new_model[pillar][ki] = model[pillar].get(ki, [])
        else:
            for ki in sorted(issues_list):
                new_model[pillar][ki] = []
    return new_model


def _parse_selection_indices(selection: str, n: int) -> List[int]:
    s = selection.strip()
    if not s:
        return list(range(n))

    parts = re.split(r"[,\s]+", s)
    idxs: set = set()
    for part in parts:
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            if not a.strip().isdigit() or not b.strip().isdigit():
                raise ValueError(f"Bad range token: '{part}'")
            start = int(a) - 1
            end = int(b) - 1
            if start > end:
                start, end = end, start
            for k in range(start, end + 1):
                idxs.add(k)
        else:
            if not part.isdigit():
                raise ValueError(f"Bad token: '{part}'")
            idxs.add(int(part) - 1)

    if not idxs:
        raise ValueError("No selection provided.")
    if min(idxs) < 0 or max(idxs) >= n:
        raise ValueError("Selection out of range.")
    return sorted(idxs)


def ask_multi_select(items: List[str], title: str) -> List[str]:
    _print_header(title)
    for i, item in enumerate(items, 1):
        print(f"{i:>2}. {item}")
    print("\nSelect items by number; supports ranges like 1-3, 6-8.")
    print("Press Enter for ALL.")
    while True:
        ans = safe_input("Selection: ").strip()
        try:
            idxs = _parse_selection_indices(ans, len(items))
            return [items[i] for i in idxs]
        except Exception as e:
            print(f"Invalid selection: {e}")


def edit_pillars_and_issues(pillars: Dict[str, List[str]]) -> Dict[str, List[str]]:
    while True:
        _print_header("Current Pillars and Key Issues (AHP scope)")
        for p in sorted(pillars.keys()):
            print(f"- {p} ({len(pillars[p])} issues)")
        print("\nActions:")
        print("  1) Add pillar")
        print("  2) Remove pillar")
        print("  3) Add key issue to a pillar")
        print("  4) Remove key issue from a pillar")
        print("  5) Continue")
        action = ask_int("Choose action (1-5): ", 1, 5)

        if action == 1:
            new_p = safe_input("New pillar name: ").strip()
            if not new_p:
                print("Pillar name cannot be empty.")
                continue
            if new_p in pillars:
                print("Pillar already exists.")
                continue
            issues: List[str] = []
            print("Enter key issues for this pillar (blank line to stop):")
            while True:
                ki = safe_input("  Key issue: ").strip()
                if not ki:
                    break
                issues.append(ki)
            pillars[new_p] = sorted(set(issues)) if issues else []
        elif action == 2:
            p_list = sorted(pillars.keys())
            if not p_list:
                print("No pillars to remove.")
                continue
            sel = ask_multi_select(p_list, "Select pillar(s) to remove")
            for p in sel:
                pillars.pop(p, None)
        elif action == 3:
            p_list = sorted(pillars.keys())
            if not p_list:
                print("No pillars available.")
                continue
            p = ask_choice("Which pillar? ", p_list)
            ki = safe_input("New key issue name: ").strip()
            if not ki:
                print("Key issue cannot be empty.")
                continue
            pillars[p] = sorted(set(pillars.get(p, []) + [ki]))
        elif action == 4:
            p_list = sorted(pillars.keys())
            if not p_list:
                print("No pillars available.")
                continue
            p = ask_choice("Which pillar? ", p_list)
            issues = pillars.get(p, [])
            if not issues:
                print("That pillar has no issues.")
                continue
            sel = ask_multi_select(issues, f"Select key issue(s) to remove from {p}")
            pillars[p] = [x for x in issues if x not in set(sel)]
        else:
            return pillars


def _prompt_default_mode(default_mode: str) -> str:
    while True:
        raw = safe_input(f"Default scoring mode [A/B/C] (default {default_mode}): ").strip().upper()
        if raw == "":
            return default_mode
        if raw in {"A", "B", "C"}:
            return raw
        print("❌ Enter A, B, or C (or press Enter for default).")


def _prompt_hib(default: bool) -> bool:
    ans = safe_input(f"Higher is better? [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if ans == "":
        return default
    return ans in {"y", "yes"}


def edit_indicators_in_model(model: Model) -> Model:
    while True:
        _print_header("Indicator editor (per Key Issue) – metadata needed for scoring step")
        pillars = sorted(model.keys())
        if not pillars:
            print("No pillars exist.")
            return model

        print("Actions:")
        print("  1) Select pillar & key issue to edit indicators")
        print("  2) Print current structure")
        print("  3) Continue")
        action = ask_int("Choose action (1-3): ", 1, 3)

        if action == 2:
            print_model_structure(model)
            continue
        if action == 3:
            return model

        pillar = ask_choice("Which pillar? ", pillars)
        key_issues = sorted(model.get(pillar, {}).keys())
        if not key_issues:
            print("This pillar has no key issues.")
            continue
        ki = ask_choice("Which key issue? ", key_issues)

        while True:
            inds = model[pillar][ki]
            _print_header(f"Indicators – {pillar} | {ki} ({len(inds)} indicators)")
            if inds:
                for i, idef in enumerate(inds, 1):
                    direction = "higher" if idef.higher_is_better else "lower"
                    print(f"{i:>2}. {idef.indicator} [{idef.unit}] | mode={idef.default_mode} ({direction})")
                    print(f"    Criteria: {idef.criteria}")
                    print(f"    Formula/Description: {idef.formula_desc}")
            else:
                print("(No indicators yet for this key issue.)")

            print("\nActions:")
            print("  1) Add indicator")
            print("  2) Remove indicator")
            print("  3) Edit indicator metadata")
            print("  4) Back")
            act2 = ask_int("Choose action (1-4): ", 1, 4)

            if act2 == 4:
                break

            if act2 == 1:
                ind_name = safe_input("Indicator name: ").strip()
                if not ind_name:
                    print("Indicator name cannot be empty.")
                    continue
                unit = safe_input("Unit: ").strip() or "unit"
                criteria = safe_input("Criteria (text): ").strip() or "Criterion"
                default_mode = _prompt_default_mode("A")
                higher_is_better = True
                if default_mode in {"A", "B"}:
                    higher_is_better = (default_mode == "A")
                    higher_is_better = _prompt_hib(higher_is_better)
                else:
                    higher_is_better = _prompt_hib(True)

                formula_desc = safe_input("Formula/Description (text): ").strip() or _default_formula_desc(default_mode)

                new_idef = IndicatorDef(
                    pillar=pillar,
                    key_issue=ki,
                    indicator=ind_name,
                    unit=unit,
                    formula_desc=formula_desc,
                    criteria=criteria,
                    default_mode=default_mode,
                    higher_is_better=higher_is_better,
                )
                model[pillar][ki] = sorted(model[pillar][ki] + [new_idef], key=lambda x: x.indicator.lower())
                continue

            if act2 == 2:
                if not inds:
                    print("No indicators to remove.")
                    continue
                sel = ask_int(f"Select indicator number to remove (1-{len(inds)}): ", 1, len(inds))
                keep = [x for j, x in enumerate(inds, 1) if j != sel]
                model[pillar][ki] = keep
                continue

            if act2 == 3:
                if not inds:
                    print("No indicators to edit.")
                    continue
                sel = ask_int(f"Select indicator number to edit (1-{len(inds)}): ", 1, len(inds))
                idef = inds[sel - 1]

                _print_header(f"Editing: {idef.indicator}")
                ind_name = prompt_str_nonempty("Indicator name", idef.indicator)
                unit = prompt_str_nonempty("Unit", idef.unit)
                criteria = prompt_str_nonempty("Criteria", idef.criteria)
                default_mode = _prompt_default_mode(idef.default_mode)
                hib_default = idef.higher_is_better if default_mode in {"A", "B"} else idef.higher_is_better
                higher_is_better = _prompt_hib(hib_default)
                formula_desc = prompt_str_nonempty("Formula/Description", idef.formula_desc)

                updated = IndicatorDef(
                    pillar=pillar,
                    key_issue=ki,
                    indicator=ind_name,
                    unit=unit,
                    formula_desc=formula_desc,
                    criteria=criteria,
                    default_mode=default_mode,
                    higher_is_better=higher_is_better,
                )

                new_list = []
                for j, x in enumerate(inds):
                    new_list.append(updated if j == (sel - 1) else x)
                model[pillar][ki] = sorted(new_list, key=lambda x: x.indicator.lower())
                continue

        if ask_yes_no("Do you want to edit anything or re-run this step?", default=False):
            continue


# =============================================================================
# AHP/FAHP (key issue weights)
# =============================================================================
RI_TABLE = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}

TFN_SCALE = {
    1: (1.0, 1.0, 1.0),
    2: (1.0, 2.0, 3.0),
    3: (2.0, 3.0, 4.0),
    4: (3.0, 4.0, 5.0),
    5: (4.0, 5.0, 6.0),
    6: (5.0, 6.0, 7.0),
    7: (6.0, 7.0, 8.0),
    8: (7.0, 8.0, 9.0),
    9: (9.0, 9.0, 9.0),
}

SAATY_MIN = 1.0 / 9.0
SAATY_MAX = 9.0


@dataclass(frozen=True)
class ConsistencyResult:
    lambda_max: float
    ci: float
    cr: float
    ri: float


def _print_rating_scale() -> None:
    print("\nRating criteria (Saaty scale reference):")
    print("  1  Equal Importance")
    print("  3  Moderate Importance")
    print("  5  Strong Importance")
    print("  7  Very Strong Importance")
    print("  9  Highly Likely Important")
    print("  Intermediate values: 2, 4, 6, 8")


def parse_ratio(text: str) -> float:
    t = text.strip()
    if re.fullmatch(r"\d+/\d+", t):
        a, b = t.split("/")
        bi = int(b)
        if bi == 0:
            raise ValueError("Division by zero.")
        return int(a) / bi
    return float(t)


def _validate_saaty_value(v: float) -> None:
    if v <= 0:
        raise ValueError("Value must be > 0.")
    if v < SAATY_MIN or v > SAATY_MAX:
        raise ValueError(f"Value must be within Saaty bounds: {SAATY_MIN:.6f} .. {SAATY_MAX:.0f}")


def nearest_saaty_value(x: float) -> int:
    x = max(SAATY_MIN, min(SAATY_MAX, x))
    candidates = list(range(1, 10))
    return int(min(candidates, key=lambda k: abs(k - x)))


def crisp_pairwise_matrix_manual(criteria: List[str]) -> np.ndarray:
    n = len(criteria)
    A = np.ones((n, n), dtype=float)

    _print_header("Pairwise Comparison (Manual Input)")
    print("Allowed: 1..9 or fractions like 1/3.")
    print("Meaning: value = how much MORE important ROW is than COLUMN.")
    print(f"Enforced bounds: {SAATY_MIN:.6f} .. {SAATY_MAX:.0f}\n")

    for i in range(n):
        for j in range(i + 1, n):
            while True:
                raw = safe_input(f"How important is '{criteria[i]}' vs '{criteria[j]}'? ").strip()
                try:
                    v = parse_ratio(raw)
                    _validate_saaty_value(v)

                    if v >= 1.0:
                        v = float(nearest_saaty_value(v))
                    else:
                        inv = 1.0 / v
                        _validate_saaty_value(inv)
                        v = 1.0 / float(nearest_saaty_value(inv))

                    A[i, j] = v
                    A[j, i] = 1.0 / v
                    break
                except Exception as e:
                    print(f"Invalid input: {e}")
    return A


def crisp_pairwise_matrix_from_ratings(criteria: List[str], ratings: List[int]) -> np.ndarray:
    n = len(criteria)
    A = np.ones((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j:
                A[i, j] = 1.0
            else:
                ratio = ratings[i] / max(ratings[j], 1e-9)
                if ratio >= 1:
                    A[i, j] = float(nearest_saaty_value(ratio))
                else:
                    A[i, j] = 1.0 / float(nearest_saaty_value(1.0 / ratio))
    for i in range(n):
        for j in range(i + 1, n):
            A[j, i] = 1.0 / A[i, j]
    return A


def normalize_columns(A: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    col_sums = A.sum(axis=0)
    norm = A / col_sums
    w = norm.mean(axis=1)
    return norm, w / w.sum()


def ahp_geometric_mean_weights(A: np.ndarray) -> np.ndarray:
    n = A.shape[0]
    gm = np.prod(A, axis=1) ** (1.0 / n)
    return gm / gm.sum()


def eigenvector_weights(A: np.ndarray) -> Tuple[np.ndarray, float]:
    vals, vecs = np.linalg.eig(A)
    idx = int(np.argmax(vals.real))
    lambda_max = float(vals[idx].real)
    w = np.abs(vecs[:, idx].real)
    return w / w.sum(), lambda_max


def consistency_metrics(n: int, lambda_max: float) -> ConsistencyResult:
    ci = 0.0 if n <= 2 else (lambda_max - n) / (n - 1)
    ri = RI_TABLE.get(n, RI_TABLE[max(RI_TABLE.keys())])
    cr = 0.0 if ri == 0 else ci / ri
    return ConsistencyResult(lambda_max=lambda_max, ci=ci, cr=cr, ri=ri)


def tfn_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def tfn_mul(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def tfn_reciprocal(tfn: Tuple[float, float, float]) -> Tuple[float, float, float]:
    l, m, u = tfn
    return (1.0 / u, 1.0 / m, 1.0 / l)


def crisp_to_tfn(v: float) -> Tuple[float, float, float]:
    if v >= 1.0:
        return TFN_SCALE[nearest_saaty_value(v)]
    inv = 1.0 / v
    return tfn_reciprocal(TFN_SCALE[nearest_saaty_value(inv)])


def build_fuzzy_matrix(A: np.ndarray) -> List[List[Tuple[float, float, float]]]:
    n = A.shape[0]
    F: List[List[Tuple[float, float, float]]] = []
    for i in range(n):
        row: List[Tuple[float, float, float]] = []
        for j in range(n):
            row.append((1.0, 1.0, 1.0) if i == j else crisp_to_tfn(float(A[i, j])))
        F.append(row)
    return F


def fahp_buckley_defuzz(F: List[List[Tuple[float, float, float]]]) -> np.ndarray:
    n = len(F)
    g: List[Tuple[float, float, float]] = []
    for i in range(n):
        l_prod, m_prod, u_prod = 1.0, 1.0, 1.0
        for j in range(n):
            l, m, u = F[i][j]
            l_prod *= l
            m_prod *= m
            u_prod *= u
        g.append((l_prod ** (1.0 / n), m_prod ** (1.0 / n), u_prod ** (1.0 / n)))

    sum_l = sum(x[0] for x in g)
    sum_m = sum(x[1] for x in g)
    sum_u = sum(x[2] for x in g)
    inv_sum = (1.0 / sum_u, 1.0 / sum_m, 1.0 / sum_l)

    fuzzy_w: List[Tuple[float, float, float]] = []
    for (l, m, u) in g:
        fuzzy_w.append((l * inv_sum[0], m * inv_sum[1], u * inv_sum[2]))

    defuzz = np.array([(l + m + u) / 3.0 for (l, m, u) in fuzzy_w], dtype=float)
    return defuzz / defuzz.sum()


def _possibility_geq(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    l1, m1, u1 = a
    l2, m2, u2 = b
    if m1 >= m2:
        return 1.0
    if l2 >= u1:
        return 0.0
    denom = (m1 - u1) - (m2 - l2)
    if abs(denom) < 1e-12:
        return 0.0
    val = (l2 - u1) / denom
    return float(max(0.0, min(1.0, val)))


def fahp_chang_extent(F: List[List[Tuple[float, float, float]]]) -> np.ndarray:
    n = len(F)

    row_sums: List[Tuple[float, float, float]] = []
    for i in range(n):
        s = (0.0, 0.0, 0.0)
        for j in range(n):
            s = tfn_add(s, F[i][j])
        row_sums.append(s)

    total = (0.0, 0.0, 0.0)
    for rs in row_sums:
        total = tfn_add(total, rs)

    inv_total = tfn_reciprocal(total)
    S: List[Tuple[float, float, float]] = [tfn_mul(rs, inv_total) for rs in row_sums]  # noqa: E701

    d = np.zeros(n, dtype=float)
    for i in range(n):
        vals = []
        for k in range(n):
            if k == i:
                continue
            vals.append(_possibility_geq(S[i], S[k]))
        d[i] = min(vals) if vals else 1.0

    return (d / d.sum()) if d.sum() > 0 else (np.ones(n) / n)


def _heatmap_figsize(n: int) -> Tuple[float, float]:
    w = max(6.0, min(14.0, 0.55 * n))
    h = max(5.0, min(12.0, 0.45 * n))
    return w, h


def plot_heatmap(matrix: np.ndarray, labels: List[str], title: str, annotate: bool = True) -> None:
    n = len(labels)
    fig_w, fig_h = _heatmap_figsize(n)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(matrix, aspect="auto", interpolation="nearest")
    ax.set_title(title)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=75, ha="right")
    ax.set_yticklabels(labels)

    cbar = fig.colorbar(im, ax=ax, shrink=0.9)
    cbar.ax.set_ylabel("Value", rotation=90)

    if annotate and n <= 14:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{matrix[i, j]:.2g}", ha="center", va="center")

    fig.tight_layout()
    plt.show()


def plot_weights_comparison(df_weights: pd.DataFrame, title: str, top_n: int) -> None:
    df = df_weights.copy().sort_values("FAHP Buckley", ascending=False).head(top_n)
    labels = df["Key Issue"].astype(str).tolist()
    methods = [c for c in df.columns if c != "Key Issue"]

    fig_w = max(8.0, min(18.0, 0.6 * len(labels) + 6.0))
    fig, ax = plt.subplots(figsize=(fig_w, 6.0))

    x = np.arange(len(labels), dtype=float)
    width = 0.82 / max(1, len(methods))

    for i, m in enumerate(methods):
        ax.bar(x + i * width, df[m].astype(float).to_numpy(), width=width, label=m)

    ax.set_title(title)
    ax.set_xlabel("Key Issue")
    ax.set_ylabel("Weight")
    ax.set_xticks(x + width * (len(methods) - 1) / 2.0)
    ax.set_xticklabels(labels, rotation=75, ha="right")
    ax.grid(True, axis="y", linewidth=0.6, alpha=0.5)

    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0.0)
    fig.tight_layout()
    plt.show()


def plot_rank_lines(df_weights: pd.DataFrame, title: str, top_n: int) -> None:
    df = df_weights.copy().sort_values("FAHP Buckley", ascending=False).head(top_n)
    labels = df["Key Issue"].astype(str).tolist()
    methods = [c for c in df.columns if c != "Key Issue"]

    fig_w = max(8.0, min(18.0, 0.6 * len(labels) + 6.0))
    fig, ax = plt.subplots(figsize=(fig_w, 6.0))

    for m in methods:
        ranks = pd.Series(df[m].astype(float).to_numpy()).rank(ascending=False, method="average").to_numpy()
        ax.plot(range(len(labels)), ranks, marker="o", linewidth=1.5, label=m)

    ax.set_title(title)
    ax.set_xlabel("Key Issue (sorted by FAHP Buckley)")
    ax.set_ylabel("Rank (1 = highest)")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=75, ha="right")
    ax.set_yticks(range(1, len(labels) + 1))
    ax.grid(True, axis="y", linewidth=0.6, alpha=0.5)
    ax.invert_yaxis()

    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0.0)
    fig.tight_layout()
    plt.show()


def _spearman_corr_matrix(method_to_w: Dict[str, np.ndarray]) -> pd.DataFrame:
    methods = list(method_to_w.keys())
    m = len(methods)
    C = np.eye(m, dtype=float)
    for i in range(m):
        for j in range(i + 1, m):
            x = method_to_w[methods[i]]
            y = method_to_w[methods[j]]
            rx = pd.Series(x).rank(method="average").to_numpy()
            ry = pd.Series(y).rank(method="average").to_numpy()
            cx = rx - rx.mean()
            cy = ry - ry.mean()
            denom = float(np.sqrt((cx**2).sum()) * np.sqrt((cy**2).sum()))
            corr = float((cx * cy).sum() / denom) if denom > 0 else 0.0
            C[i, j] = corr
            C[j, i] = corr
    return pd.DataFrame(C, index=methods, columns=methods)


def plot_weight_variability(df_weights: pd.DataFrame, methods: List[str], title: str, top_n: int) -> None:
    W = df_weights[methods].astype(float)
    rng = (W.max(axis=1) - W.min(axis=1)).set_axis(df_weights["Key Issue"].astype(str))
    rng = rng.sort_values(ascending=False).head(top_n)
    labels = rng.index.tolist()
    values = rng.to_numpy()

    fig_w = max(8.0, min(18.0, 0.6 * len(labels) + 6.0))
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_xlabel("Key Issue")
    ax.set_ylabel("Weight range (max-min across methods)")
    ax.grid(True, axis="y", linewidth=0.6, alpha=0.5)
    ax.set_xticklabels(labels, rotation=75, ha="right")
    fig.tight_layout()
    plt.show()


def _top_k_agreement(df_weights: pd.DataFrame, methods: List[str], k: int = 5) -> Tuple[float, List[str]]:
    k_eff = min(k, len(df_weights))
    top_sets = []
    for m in methods:
        top = df_weights.sort_values(m, ascending=False).head(k_eff)["Key Issue"].astype(str).tolist()
        top_sets.append(set(top))
    intersection = set.intersection(*top_sets) if top_sets else set()
    rate = (len(intersection) / float(k_eff)) if k_eff > 0 else 0.0
    return rate, sorted(intersection)


def run_ahp_fahp_section(model: Model) -> Tuple[Model, Dict[str, pd.DataFrame], str]:
    pillars_to_issues = _pillars_to_issues_from_model(model)

    _print_header("FAHP/AHP Multi-method Validation (Key Issues Only)")
    for p in sorted(pillars_to_issues.keys()):
        print(f"  - {p}: {len(pillars_to_issues[p])} key issues")

    pillar_names = sorted(pillars_to_issues.keys())
    if not pillar_names:
        print("No pillars available. Exiting.")
        sys.exit(0)

    cr_threshold = 0.10
    weights_by_pillar: Dict[str, pd.DataFrame] = {}

    for pillar in pillar_names:
        issues_all = pillars_to_issues[pillar]
        if not issues_all:
            print(f"\nSkipping pillar '{pillar}' (no issues).")
            continue

        rerun_pillar = True
        while rerun_pillar:
            issues = ask_multi_select(issues_all, f"[{pillar}] Select key issues/themes to include")
            if len(issues) == 0:
                print("No key issues selected. Skipping pillar.")
                break

            if len(issues) == 1:
                only = issues[0]
                df_weights = pd.DataFrame(
                    {
                        "Key Issue": [only],
                        "AHP RowAvg": [1.0],
                        "AHP Eigen": [1.0],
                        "AHP GeoMean": [1.0],
                        "FAHP Buckley": [1.0],
                        "FAHP Chang": [1.0],
                    }
                )
                weights_by_pillar[pillar] = df_weights
                print(f"\n[{pillar}] Single key issue selected → weight=1.0")
                rerun_pillar = ask_yes_no(f"Do you want to re-run pillar '{pillar}'?", default=False)
                continue

            _print_header(f"[{pillar}] Optional baseline ratings (1-9)")
            _print_rating_scale()
            ratings = [ask_int(f"Rating for '{ki}' (1-9, default 1): ", 1, 9, default=1) for ki in issues]
            mode = ask_choice("\nPairwise input mode: 'manual' or 'auto': ", ["manual", "auto"])

            while True:
                _print_header(f"[{pillar}] Pairwise + Weights (Multi-method)")

                if mode == "manual":
                    A = crisp_pairwise_matrix_manual(issues)
                else:
                    A = crisp_pairwise_matrix_from_ratings(issues, ratings)
                    print("\nAuto-filled pairwise matrix from ratings (snapped to Saaty scale).")

                norm_A, w_rowavg = normalize_columns(A)
                w_gm = ahp_geometric_mean_weights(A)

                cons: Optional[ConsistencyResult] = None
                try:
                    w_eig, lambda_max = eigenvector_weights(A)
                    cons = consistency_metrics(len(issues), lambda_max)
                except Exception:
                    w_eig = w_rowavg

                F = build_fuzzy_matrix(A)
                w_fuzzy_buckley = fahp_buckley_defuzz(F)
                w_fuzzy_chang = fahp_chang_extent(F)

                df_weights = pd.DataFrame(
                    {
                        "Key Issue": issues,
                        "AHP RowAvg": w_rowavg,
                        "AHP Eigen": w_eig,
                        "AHP GeoMean": w_gm,
                        "FAHP Buckley": w_fuzzy_buckley,
                        "FAHP Chang": w_fuzzy_chang,
                    }
                ).sort_values("FAHP Buckley", ascending=False)

                print("\nWeights (sorted by FAHP Buckley):")
                print(df_weights.to_string(index=False, float_format=lambda x: f"{x:.6f}"))

                methods = ["AHP RowAvg", "AHP Eigen", "AHP GeoMean", "FAHP Buckley", "FAHP Chang"]
                agree_rate, agree_items = _top_k_agreement(df_weights, methods, k=5)
                print("\nValidation: Top-5 rank agreement across methods")
                print(f"  Agreement rate: {agree_rate:.2%}")
                print(f"  Common Top-5 items ({len(agree_items)}): {', '.join(agree_items) if agree_items else 'None'}")

                need_decision = False
                if cons is None:
                    print("\nConsistency: unavailable (eigen computation failed).")
                    need_decision = True
                elif len(issues) < 3:
                    print("\nConsistency: CR not applicable for n < 3 (proceeding).")
                else:
                    print("\nConsistency (eigen):")
                    print(f"  lambda_max = {cons.lambda_max:.6f}")
                    print(f"  CI         = {cons.ci:.6f}")
                    print(f"  RI         = {cons.ri:.2f}")
                    print(f"  CR         = {cons.cr:.6f} (threshold {cr_threshold:.2f})")
                    if cons.cr > cr_threshold:
                        need_decision = True

                if need_decision:
                    print("\nAlternative options:")
                    print("  1) Redo pairwise comparisons (recommended)")
                    print("  2) Switch to auto (from ratings)")
                    print("  3) Continue anyway")
                    choice = ask_choice("Choose 1/2/3: ", ["1", "2", "3"])
                    if choice == "1":
                        mode = "manual"
                        continue
                    if choice == "2":
                        mode = "auto"
                        continue

                top_n = min(len(issues), ask_int("Top N to plot (default 15): ", 2, 200, default=15))

                plot_heatmap(A, issues, f"{pillar} | Pairwise Matrix", annotate=True)
                plot_weights_comparison(df_weights, f"{pillar} | Weights by Method (Top {top_n})", top_n)
                plot_rank_lines(df_weights, f"{pillar} | Rank Comparison (Top {top_n})", top_n)

                method_to_w = {m: df_weights[m].to_numpy() for m in methods}
                corr_df = _spearman_corr_matrix(method_to_w)
                plot_heatmap(
                    corr_df.to_numpy(),
                    corr_df.columns.tolist(),
                    f"{pillar} | Method Correlation (Spearman)",
                    annotate=True,
                )

                plot_weight_variability(
                    df_weights,
                    methods,
                    f"{pillar} | Weight Variability (Top {top_n})",
                    top_n,
                )

                weights_by_pillar[pillar] = df_weights
                rerun_pillar = ask_yes_no(f"Do you want to re-run pillar '{pillar}'?", default=False)
                break

    print("\nChoose which weight method to APPLY for scoring:")
    print("  1) AHP RowAvg")
    print("  2) AHP Eigen")
    print("  3) AHP GeoMean")
    print("  4) FAHP Buckley (default)")
    print("  5) FAHP Chang")
    choice = ask_choice("Select 1/2/3/4/5: ", ["1", "2", "3", "4", "5"], allow_blank=True) or "4"
    method_map = {"1": "AHP RowAvg", "2": "AHP Eigen", "3": "AHP GeoMean", "4": "FAHP Buckley", "5": "FAHP Chang"}
    chosen_method = method_map[choice]
    print(f"Using '{chosen_method}' weights for ESGFP scoring.")

    new_model: Model = {}
    for pillar, dfw in weights_by_pillar.items():
        issues = dfw["Key Issue"].astype(str).tolist()
        if pillar not in model:
            continue
        new_model[pillar] = {}
        for ki in issues:
            if ki in model[pillar]:
                new_model[pillar][ki] = model[pillar][ki]
            else:
                new_model[pillar][ki] = []
                print(f"⚠️  AHP includes '{pillar}:{ki}' but no indicators exist in the model yet.")

    return new_model, weights_by_pillar, chosen_method


def extract_issue_weights(
    weights_by_pillar: Dict[str, pd.DataFrame], method: str
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for pillar, dfw in weights_by_pillar.items():
        if method not in dfw.columns:
            continue
        d = {}
        for _, r in dfw.iterrows():
            d[str(r["Key Issue"])] = float(r[method])
        s = sum(d.values())
        if s > 0:
            d = {k: v / s for k, v in d.items()}
        out[pillar] = d
    return out


# =============================================================================
# Indicator scoring (your formulas)
# =============================================================================
INDICATOR_SCORE_SCALE = 90.0
GM_MIN = 0.5
GM_MAX = 0.6
PILLAR_SCORE_THEORETICAL_MAX = INDICATOR_SCORE_SCALE + GM_MAX  # ≈ 90.6
MIN_DISPLAY_SCORE = 1.0
OUTPUT_SCALE = 10.0


def compute_indicator_score_scaled(
    current: float,
    vmin: float,
    vmax: float,
    higher_is_better: bool,
    n_alts: int,
) -> float:
    """
    UPDATED formula:
    - If n_alts == 1: CS = 90
    - Else:
        Higher: CS = 30 + 60 * [(cur - min)/(max-min)]
        Lower : CS = 30 + 60 * [(max - cur)/(max-min)]
    """
    if n_alts <= 1:
        return 90.0
    denom = vmax - vmin
    if abs(denom) < 1e-12:
        return 90.0
    if higher_is_better:
        norm = (current - vmin) / denom
    else:
        norm = (vmax - current) / denom
    norm = float(np.clip(norm, 0.0, 1.0))
    return float(30.0 + 60.0 * norm)


def compute_rank_cs(
    current_rank: float,
    best_rank: float,
    worst_rank: float,
    lower_rank_is_better: bool,
) -> float:
    if math.isclose(best_rank, worst_rank):
        return 0.0

    lo = min(best_rank, worst_rank)
    hi = max(best_rank, worst_rank)

    if current_rank < lo or current_rank > hi:
        raise ValueError(f"Rank must be within [{lo}, {hi}]")

    pos = (current_rank - lo) / (hi - lo)
    perf = (1.0 - pos) if lower_rank_is_better else pos

    perf = float(np.clip(perf, 0.0, 1.0))
    decile = int(math.floor(perf * 10.0))
    if decile >= 10:
        decile = 9
    return float(decile * 10.0)


def compute_gm(ge: float) -> float:
    ge_norm = float(np.clip(float(ge) / 10.0, 0.0, 1.0))
    return 0.1 * ge_norm + 0.5


def compute_ps(is_score: float, gm: float, gm_sign: int) -> float:
    ps = is_score + (gm_sign * gm)
    return float(max(0.0, ps))


def compute_final_indicator_score(ps: float, key_issue_weight: float, n_criteria: int) -> float:
    n = max(1, int(n_criteria))
    return ps * (float(key_issue_weight) / float(n))


# =============================================================================
# ESGFP scoring (technologies/process designs)
# =============================================================================
def _indicator_key(p: str, ki: str, ind: str) -> str:
    return f"{p}:{ki}:{ind}"


def _prompt_scoring_mode(default_mode: str) -> str:
    print("\nScoring options:")
    print("  A — Higher is better")
    print("      If 1 alternative: CS = 90")
    print("      Else: CS = 30 + 60 × [(I_current - I_min) / (I_max - I_min)]")
    print("  B — Lower is better")
    print("      If 1 alternative: CS = 90")
    print("      Else: CS = 30 + 60 × [(I_max - I_current) / (I_max - I_min)]")
    print("  C — Index / ranking-based indicator (custom scale)")
    while True:
        raw = safe_input(f"Choose [A/B/C] (default {default_mode}): ").strip().upper()
        if raw == "":
            return default_mode
        if raw in {"A", "B", "C"}:
            return raw
        print("❌ Enter A, B, or C (or press Enter for default).")


def collect_scores_for_alternatives(
    labels: List[str],
    model: Model,
    issue_weights: Dict[str, Dict[str, float]],
    gm_value: float,
    alt_term_singular: str,
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, List[str]]]]:
    scores_by_alt: Dict[str, Dict[str, float]] = {lab: {} for lab in labels}
    comments_by_alt: Dict[str, Dict[str, List[str]]] = {lab: {} for lab in labels}

    print(f"\n📥 Indicator inputs for {alt_term_singular}(s)")
    print("IS (CS) ceiling is 90.")
    print("GE is entered once per indicator (applies to all alternatives for that indicator).")
    print("GM = 0.1*(GE/10) + 0.5; sign is chosen per criterion per key issue per " + alt_term_singular + ".")
    print("PS = IS ± GM")

    for pillar, issues in model.items():
        for key_issue, indicators in issues.items():
            w = float(issue_weights.get(pillar, {}).get(key_issue, 0.0))
            n_criteria = max(1, len(indicators))
            if not indicators:
                continue

            print(f"\n— {pillar} | {key_issue} (AHP weight={w:.4f}, criteria={n_criteria})")

            for idef in indicators:
                direction_default = "higher is better" if idef.higher_is_better else "lower is better"
                ind_title = f"{idef.indicator} [{idef.unit}] ({direction_default})"
                ind_meta = f"Criteria: {idef.criteria} | DefaultMode: {idef.default_mode}\n    Formula/Description: {idef.formula_desc}"

                rerun_indicator = True
                while rerun_indicator:
                    print(f"\n  • {ind_title}")
                    print(f"    {ind_meta}")

                    default_mode = idef.default_mode if idef.default_mode in {"A", "B", "C"} else (
                        "A" if idef.higher_is_better else "B"
                    )
                    mode = _prompt_scoring_mode(default_mode)

                    ge = prompt_exposure("    GE (0–10 or label): ")
                    ge_cmt = prompt_comment()
                    gm_local = compute_gm(ge)

                    print(f"    ▶ Raw calc (shared for this indicator): GE={ge:.4f} → GM={gm_local:.4f}")

                    if ge_cmt:
                        for lab in labels:
                            comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                f"GE: {ge_cmt}"
                            )

                    if mode in {"A", "B"}:
                        hib = (mode == "A")
                        mode_text = "Higher-is-better" if hib else "Lower-is-better"
                        print(f"    ▶ Scoring mode selected: {mode_text}")

                        if len(labels) == 1:
                            lab = labels[0]
                            cur = prompt_float("    Current: ", -1e18, 1e18)
                            cmt = prompt_comment()
                            if cmt:
                                comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                    f"Current: {cmt}"
                                )

                            is_score = compute_indicator_score_scaled(cur, cur, cur, hib, n_alts=1)

                            ctx = f"{pillar} | {key_issue} | {idef.indicator} | {alt_term_singular.title()}: {lab}"
                            gm_sign = ask_gm_sign_each_time(ctx)
                            sign_char = "+" if gm_sign > 0 else "-"

                            ps = compute_ps(is_score, gm_local, gm_sign)
                            final_score = compute_final_indicator_score(ps, w, n_criteria)
                            scores_by_alt[lab][_indicator_key(pillar, key_issue, idef.indicator)] = round(final_score, 6)

                            print(
                                f"    ✅ Raw scores ({lab}) → IS={is_score:.4f}, GM={gm_local:.4f}, "
                                f"PS=IS {sign_char} GM={ps:.4f}, Final={final_score:.6f}"
                            )

                        else:
                            current_vals: Dict[str, float] = {}
                            for lab in labels:
                                val = prompt_float(f"    {lab} Current: ", -1e18, 1e18)
                                cmt = prompt_comment()
                                if cmt:
                                    comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                        f"Value: {cmt}"
                                    )
                                current_vals[lab] = val

                            vmin = min(current_vals.values())
                            vmax = max(current_vals.values())
                            print(f"    ▶ Raw calc (this indicator across all): I_min={vmin:.6g}, I_max={vmax:.6g}")

                            for lab in labels:
                                is_score = compute_indicator_score_scaled(
                                    current=current_vals[lab],
                                    vmin=vmin,
                                    vmax=vmax,
                                    higher_is_better=hib,
                                    n_alts=len(labels),
                                )

                                ctx = f"{pillar} | {key_issue} | {idef.indicator} | {alt_term_singular.title()}: {lab}"
                                gm_sign = ask_gm_sign_each_time(ctx)
                                sign_char = "+" if gm_sign > 0 else "-"

                                ps = compute_ps(is_score, gm_local, gm_sign)
                                final_score = compute_final_indicator_score(ps, w, n_criteria)
                                scores_by_alt[lab][_indicator_key(pillar, key_issue, idef.indicator)] = round(final_score, 6)

                                print(
                                    f"    ✅ Raw scores ({lab}) → Current={current_vals[lab]:.6g}, "
                                    f"IS={is_score:.4f}, GM={gm_local:.4f}, PS=IS {sign_char} GM={ps:.4f}, "
                                    f"Final={final_score:.6f}"
                                )

                    else:
                        print("    ▶ Scoring mode selected: Index / ranking-based (deciles)")
                        best_rank = prompt_float("    Best rank (e.g., 1):  ", -1e18, 1e18)
                        cmt = prompt_comment()
                        if cmt:
                            for lab in labels:
                                comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                    f"Best rank: {cmt}"
                                )

                        worst_rank = prompt_float("    Worst rank (e.g., 200): ", -1e18, 1e18)
                        cmt = prompt_comment()
                        if cmt:
                            for lab in labels:
                                comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                    f"Worst rank: {cmt}"
                                )

                        lower_better = ask_yes_no("    Is LOWER rank better? ", default=True)
                        print(
                            f"    ▶ Raw calc (ranking scale): best={best_rank:.6g}, worst={worst_rank:.6g}, "
                            f"{'lower-rank-better' if lower_better else 'higher-rank-better'}"
                        )

                        for lab in labels:
                            r = prompt_float(f"    {lab} Current rank: ", -1e18, 1e18)
                            cmt2 = prompt_comment()
                            if cmt2:
                                comments_by_alt[lab].setdefault(_indicator_key(pillar, key_issue, idef.indicator), []).append(
                                    f"Rank: {cmt2}"
                                )
                            try:
                                is_score = compute_rank_cs(
                                    current_rank=r,
                                    best_rank=best_rank,
                                    worst_rank=worst_rank,
                                    lower_rank_is_better=lower_better,
                                )
                            except Exception as e:
                                print(f"❌ Rank input invalid: {e}")
                                is_score = 0.0

                            ctx = f"{pillar} | {key_issue} | {idef.indicator} | {alt_term_singular.title()}: {lab}"
                            gm_sign = ask_gm_sign_each_time(ctx)
                            sign_char = "+" if gm_sign > 0 else "-"

                            ps = compute_ps(is_score, gm_local, gm_sign)
                            final_score = compute_final_indicator_score(ps, w, n_criteria)
                            scores_by_alt[lab][_indicator_key(pillar, key_issue, idef.indicator)] = round(final_score, 6)

                            print(
                                f"    ✅ Raw scores ({lab}) → Rank={r:.6g}, IS(decile)={is_score:.4f}, "
                                f"GM={gm_local:.4f}, PS=IS {sign_char} GM={ps:.4f}, Final={final_score:.6f}"
                            )

                    rerun_indicator = ask_yes_no("Do you want to edit anything or re-run this step?", default=False)

    return scores_by_alt, comments_by_alt


def compute_key_issue_scores(
    scores_by_tech: Dict[str, Dict[str, float]],
    model: Model,
) -> Dict[str, pd.DataFrame]:
    techs = list(scores_by_tech.keys())
    out: Dict[str, pd.DataFrame] = {}

    for pillar, issues in model.items():
        rows: List[Dict[str, Any]] = []
        for key_issue, indicators in issues.items():
            if not indicators:
                continue
            row: Dict[str, Any] = {"KeyIssue": key_issue}
            for tech in techs:
                total = 0.0
                for idef in indicators:
                    k = _indicator_key(pillar, key_issue, idef.indicator)
                    total += float(scores_by_tech[tech].get(k, 0.0))
                row[tech] = total
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows).set_index("KeyIssue")[techs]
        else:
            df = pd.DataFrame(columns=techs).set_index(pd.Index([], name="KeyIssue"))
        out[pillar] = df

    return out


def compute_pillar_scores(
    scores_by_tech: Dict[str, Dict[str, float]],
    model: Model,
) -> pd.DataFrame:
    techs = list(scores_by_tech.keys())
    rows: List[Dict[str, Any]] = []

    for pillar, issues in model.items():
        row: Dict[str, Any] = {"Pillar": pillar}
        for tech in techs:
            total = 0.0
            for key_issue, indicators in issues.items():
                for idef in indicators:
                    total += float(scores_by_tech[tech].get(_indicator_key(pillar, key_issue, idef.indicator), 0.0))
            row[tech] = total
        rows.append(row)

    return pd.DataFrame(rows).set_index("Pillar")[techs]


def build_indicator_score_frames(
    scores_by_alt: Dict[str, Dict[str, float]],
    model: Model,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Returns:
      pillar -> key_issue -> DataFrame(index=Indicator, columns=Alternatives) with FINAL indicator scores.
    """
    alts = list(scores_by_alt.keys())
    out: Dict[str, Dict[str, pd.DataFrame]] = {}
    for pillar, issues in model.items():
        out[pillar] = {}
        for key_issue, indicators in issues.items():
            if not indicators:
                continue
            rows = []
            for idef in indicators:
                r = {"Indicator": idef.indicator}
                for alt in alts:
                    r[alt] = float(scores_by_alt[alt].get(_indicator_key(pillar, key_issue, idef.indicator), 0.0))
                rows.append(r)
            df = pd.DataFrame(rows).set_index("Indicator")[alts]
            out[pillar][key_issue] = df
    return out


def _norm0_10(values: Sequence[float], base: float) -> List[float]:
    if base <= 0:
        base = 1.0
    return [(float(v) / base) * OUTPUT_SCALE for v in values]


def plot_key_issue_heatmap_raw(key_issue_scores: Dict[str, pd.DataFrame]) -> None:
    for pillar, df in key_issue_scores.items():
        if df.empty:
            continue
        data = df.copy()
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(data.values, aspect="auto")
        ax.set_title(f"{pillar} – Key Issue Scores (Raw)")
        ax.set_xticks(range(data.shape[1]))
        ax.set_xticklabels(data.columns, rotation=45, ha="right")
        ax.set_yticks(range(data.shape[0]))
        ax.set_yticklabels(data.index)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, f"{data.values[i, j]:.3f}", ha="center", va="center", fontsize=8)
        fig.colorbar(im, ax=ax, shrink=0.85, label="Score")
        fig.tight_layout()
        plt.show()


def plot_indicator_heatmaps(ind_frames: Dict[str, Dict[str, pd.DataFrame]]) -> None:
    """
    Visualize FINAL indicator scores per key issue (raw).
    """
    for pillar, d in ind_frames.items():
        for key_issue, df in d.items():
            if df.empty:
                continue
            data = df.copy()
            fig_h = max(4.0, min(10.0, 0.35 * data.shape[0] + 3.0))
            fig, ax = plt.subplots(figsize=(10, fig_h))
            im = ax.imshow(data.values, aspect="auto")
            ax.set_title(f"{pillar} | {key_issue} – Indicator Final Scores (Raw)")
            ax.set_xticks(range(data.shape[1]))
            ax.set_xticklabels(data.columns, rotation=45, ha="right")
            ax.set_yticks(range(data.shape[0]))
            ax.set_yticklabels(data.index)
            if data.shape[0] <= 20 and data.shape[1] <= 10:
                for i in range(data.shape[0]):
                    for j in range(data.shape[1]):
                        ax.text(j, i, f"{data.values[i, j]:.3f}", ha="center", va="center", fontsize=7)
            fig.colorbar(im, ax=ax, shrink=0.85, label="Final indicator score")
            fig.tight_layout()
            plt.show()


def _radar_axes(num_vars: int):
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    return ax, angles


def plot_pillar_heatmaps(pillar_scores: pd.DataFrame) -> None:
    if pillar_scores.empty:
        print("(No pillar scores to plot.)")
        return

    data = pillar_scores.copy()

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data.values, aspect="auto")
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(data.columns, rotation=45, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(data.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("Pillar Scores – Raw")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Score")
    fig.tight_layout()
    plt.show()

    mean = data.mean(axis=1)
    std = data.std(axis=1).replace(0, 1.0)
    z = data.sub(mean, axis=0).div(std, axis=0)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(z.values, aspect="auto", cmap="coolwarm")
    ax.set_xticks(range(z.shape[1]))
    ax.set_xticklabels(z.columns, rotation=45, ha="right")
    ax.set_yticks(range(z.shape[0]))
    ax.set_yticklabels(z.index)
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            ax.text(j, i, f"{z.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("Pillar Scores – Z-score by Pillar")
    fig.colorbar(im, ax=ax, shrink=0.8, label="z")
    fig.tight_layout()
    plt.show()


def plot_radar_profiles(pillar_scores: pd.DataFrame) -> None:
    """
    Normalized radar (0–10) + tick ranges + showing values clearly.
    """
    if pillar_scores.empty:
        return
    pillars = pillar_scores.index.tolist()
    techs = pillar_scores.columns.tolist()
    norm = (pillar_scores / PILLAR_SCORE_THEORETICAL_MAX) * OUTPUT_SCALE

    ax, angles = _radar_axes(len(pillars))
    for tech in techs:
        vals = norm[tech].tolist()
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=2, alpha=0.9, label=tech)
        ax.fill(angles, vals, alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(pillars)

    ticks = [0, 2, 4, 6, 8, 10]
    ax.set_yticks(ticks)
    ax.set_yticklabels([str(t) for t in ticks])

    ax.set_ylim(0, 10)
    ax.set_title("Pillar Profiles (Radar, normalized 0–10)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=False)
    plt.show()


def plot_radar_profiles_raw(pillar_scores: pd.DataFrame) -> None:
    """
    Raw radar chart (separate from normalized), with ranges & tick labels.
    """
    if pillar_scores.empty:
        return
    pillars = pillar_scores.index.tolist()
    techs = pillar_scores.columns.tolist()

    max_val = float(np.nanmax(pillar_scores.to_numpy())) if pillar_scores.size else 1.0
    max_val = max(max_val, 1e-9)
    top = max_val * 1.05

    ax, angles = _radar_axes(len(pillars))
    for tech in techs:
        vals = pillar_scores[tech].astype(float).tolist()
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=2, alpha=0.9, label=tech)
        ax.fill(angles, vals, alpha=0.06)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(pillars)

    ticks = np.linspace(0.0, top, 6).tolist()
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t:.1f}" for t in ticks])

    ax.set_ylim(0, top)
    ax.set_title("Pillar Profiles (Radar, raw scores)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=False)
    plt.show()


def plot_parallel_coordinates(pillar_scores: pd.DataFrame) -> None:
    if pillar_scores.empty:
        return
    data = pillar_scores.copy()
    lo = data.min(axis=1)
    hi = data.max(axis=1)
    denom = (hi - lo).replace(0, 1.0)
    norm = data.sub(lo, axis=0).div(denom, axis=0)

    x = np.arange(len(data.index))
    fig, ax = plt.subplots(figsize=(12, 6))
    for tech in norm.columns:
        ax.plot(x, norm[tech].values, marker="o", linewidth=2, alpha=0.9, label=tech)
    ax.set_xticks(x)
    ax.set_xticklabels(data.index)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Normalized (0–1)")
    ax.set_title("Parallel Coordinates – Pillar Profiles")
    ax.legend(loc="upper right", ncol=2, frameon=False)
    plt.show()


def plot_tradeoff_scatter(pillar_scores: pd.DataFrame) -> None:
    if pillar_scores.empty:
        return
    pairs = [
        ("Finance", "Environment"),
        ("Governance", "Process"),
        ("Finance", "Social"),
    ]
    for xlab, ylab in pairs:
        if xlab not in pillar_scores.index or ylab not in pillar_scores.index:
            continue
        x = pillar_scores.loc[xlab, :]
        y = pillar_scores.loc[ylab, :]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(x, y, s=120, alpha=0.85, edgecolor="black", linewidth=0.7)
        for tech in pillar_scores.columns:
            ax.annotate(tech, (x[tech], y[tech]), xytext=(6, 6), textcoords="offset points")
        ax.set_xlabel(f"{xlab} (pillar score)")
        ax.set_ylabel(f"{ylab} (pillar score)")
        ax.set_title(f"{ylab} vs {xlab} – Trade-off View")
        plt.show()


def plot_overall_summary(pillar_scores: pd.DataFrame, alt_term_singular: str) -> None:
    if pillar_scores.empty:
        return
    overall = pillar_scores.sum(axis=0).astype(float)
    fig, ax = plt.subplots(figsize=(10, 5))
    overall.sort_values(ascending=False).plot(kind="bar", ax=ax)
    ax.set_title(f"Overall Summary Score (sum of pillar scores) – {alt_term_singular.title()} comparison")
    ax.set_ylabel("Overall score (raw)")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_pillar_sum_from_key_issues(key_issue_scores: Dict[str, pd.DataFrame]) -> None:
    """
    Display sum of all key issues in a pillar (raw) as a bar chart per pillar.
    """
    for pillar, df in key_issue_scores.items():
        if df.empty:
            continue
        sums = df.sum(axis=0).astype(float)
        fig, ax = plt.subplots(figsize=(9, 4.8))
        sums.sort_values(ascending=False).plot(kind="bar", ax=ax)
        ax.set_title(f"{pillar} – Sum of Key Issues (Raw pillar total)")
        ax.set_ylabel("Sum of key issue scores")
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5)
        plt.tight_layout()
        plt.show()


def _print_comments_summary(
    comments_by_alt: Dict[str, Dict[str, List[str]]],
    alt_term_singular: str,
) -> None:
    any_comments = any(any(v for v in d.values()) for d in comments_by_alt.values())
    if not any_comments:
        return

    _print_header("📝 Input Comments Summary")
    for alt, d in comments_by_alt.items():
        print(f"\n{alt_term_singular.title()}: {alt}")
        for k, comments in d.items():
            if not comments:
                continue
            print(f"  - {k}")
            for c in comments:
                print(f"      • {c}")


def display_scoring_summary_before_scenarios(
    scores_by_alt: Dict[str, Dict[str, float]],
    model: Model,
    alt_term_singular: str,
    comments_by_alt: Dict[str, Dict[str, List[str]]],
) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    - Display final score of each indicator (per key issue)
    - Display key issue scores
    - Display sum of key issues per pillar
    - Provide visuals + summary report
    - Do this BEFORE scenarios
    """
    _print_header("📌 ESGFP Scoring Summary (Before Scenarios)")

    ind_frames = build_indicator_score_frames(scores_by_alt, model)
    key_issue_scores = compute_key_issue_scores(scores_by_alt, model)
    pillar_scores = compute_pillar_scores(scores_by_alt, model)

    print("\n📋 Pillar Scores (Raw):")
    print(pillar_scores.round(6))

    for pillar, df in key_issue_scores.items():
        if df.empty:
            continue
        print(f"\n📋 Key Issue Scores – {pillar} (Raw):")
        print(df.round(6))

    plot_indicator_heatmaps(ind_frames)
    plot_key_issue_heatmap_raw(key_issue_scores)
    plot_pillar_sum_from_key_issues(key_issue_scores)

    plot_pillar_heatmaps(pillar_scores)
    plot_radar_profiles(pillar_scores)
    plot_radar_profiles_raw(pillar_scores)
    plot_parallel_coordinates(pillar_scores)
    plot_tradeoff_scatter(pillar_scores)
    plot_overall_summary(pillar_scores, alt_term_singular)

    _print_comments_summary(comments_by_alt, alt_term_singular)

    return ind_frames, key_issue_scores, pillar_scores


def esgfp_section(
    model: Model,
    issue_weights: Dict[str, Dict[str, float]],
    gm_value: float,
    alt_term_singular: str,
    alt_term_plural: str,
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, List[str]]]]:
    print(f"\n📦 ESGFP SECTION — enter {alt_term_plural} and indicator data.")

    n = prompt_int(f"How many {alt_term_plural} are you comparing? ", 1, 50)
    labels: List[str] = []
    used: set = set()
    for i in range(n):
        default_name = f"{alt_term_singular.title()} {i + 1}"
        name = prompt_str_nonempty(f"   {alt_term_singular.title()} name", default_name)
        base = name.strip() or default_name
        label = base
        k = 2
        while label in used:
            label = f"{base} ({k})"
            k += 1
        used.add(label)
        labels.append(label)

    while True:
        scores_by_alt, comments_by_alt = collect_scores_for_alternatives(
            labels, model, issue_weights, gm_value, alt_term_singular
        )
        if ask_yes_no("Do you want to edit anything or re-run this step?", default=False):
            continue
        break

    while True:
        cmd = safe_input(
            f"\n[ESGFP] Choose: [V]isualize  [L]ist  [R]e-enter values  [P]roceed → "
        ).strip().lower()

        if cmd in {"l", "list"}:
            print(f"{alt_term_plural.title()}:", ", ".join(labels))
            continue

        if cmd in {"r", "re", "re-enter", "reenter"}:
            scores_by_alt, comments_by_alt = collect_scores_for_alternatives(
                labels, model, issue_weights, gm_value, alt_term_singular
            )
            continue

        if cmd in {"v", "visualize"}:
            _ = display_scoring_summary_before_scenarios(scores_by_alt, model, alt_term_singular, comments_by_alt)
            continue

        if cmd in {"p", "proceed", ""}:
            return scores_by_alt, comments_by_alt

        print("❌ Unknown option. Type 'help' at prompts where available.")


# =============================================================================
# MCDA cheatsheet
# =============================================================================
def method_cheatsheet() -> None:
    print(
        r"""
🧭 MCDA Quick Course

Core here:
• WSM / WLC (Weighted Sum / Weighted Linear Combination)
  - Weight source: Manual / expert
  - Aggregation: Additive
  - Suitable for: ESG, policy, design ranking
  - Enter pillar weights summing to 100%.

Also available:
• WPM – Multiplicative (ratio tradeoffs), tech comparison
• Rank-based – Additive over ranks, early-stage screening
• TOPSIS / VIKOR / EDAS – Distance/compromise-based
• MAUT – Utility-weighted (risk–benefit, diminishing returns)
• PCA – Statistical, objective (correlated criteria)

Validation:
• DEA (approximate convex-hull, output-oriented, VRS)
  - P(frontier), φ̂ (radial expansion), EffOut=1/φ̂, bottlenecks, peer mix, targets.
• Monte-Carlo sensitivity
  - Random weights (Dirichlet α, default 1.0) + mild noise → P(Best), rank stability.
• SMAA (added)
  - Rank acceptability + central weight vectors (conditional on being best).
• Weight stability intervals (added)
  - Critical weight interval for each pillar weight s.t. baseline winner stays winner (Weighted Sum).
"""
    )


# =============================================================================
# MCDA utilities + methods (unchanged)
# =============================================================================
def _weights_vector(pillars: Sequence[str], weights_pct: Dict[str, float]) -> np.ndarray:
    w = np.array([float(weights_pct.get(p, 0.0)) for p in pillars], dtype=float)
    s = w.sum()
    return w / (s if s != 0 else 1.0)


def _decision_matrix(pillar_scores: pd.DataFrame) -> Tuple[np.ndarray, List[str], List[str]]:
    alts = list(pillar_scores.columns)
    crits = list(pillar_scores.index)
    A = pillar_scores.to_numpy().T
    return A, alts, crits


def method_weighted(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    s = A @ w
    return pd.Series(s, index=alts).sort_values(ascending=False)


def method_wpm(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    col_max = A.max(axis=0)
    col_max[col_max == 0.0] = 1.0
    N = A / col_max
    N[N <= 0.0] = 1e-12
    log_scores = (np.log(N) * w).sum(axis=1)
    scores = np.exp(log_scores)
    return pd.Series(scores, index=alts).sort_values(ascending=False)


def method_rank(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    alts = list(pillar_scores.columns)
    crits = list(pillar_scores.index)
    w = _weights_vector(crits, weights_pct)
    m = len(alts)
    points = np.zeros(m)
    for j, _ in enumerate(crits):
        ranks = pillar_scores.iloc[j, :].rank(ascending=False, method="average")
        pts = (m - ranks + 1.0).to_numpy()
        points += w[j] * pts
    return pd.Series(points, index=alts).sort_values(ascending=False)


def method_topsis(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    norm = np.linalg.norm(A, axis=0)
    norm[norm == 0.0] = 1.0
    R = A / norm
    V = R * w
    ideal_best = V.max(axis=0)
    ideal_worst = V.min(axis=0)
    d_best = np.linalg.norm(V - ideal_best, axis=1)
    d_worst = np.linalg.norm(V - ideal_worst, axis=1)
    score = d_worst / (d_best + d_worst + 1e-12)
    return pd.Series(score, index=alts).sort_values(ascending=False)


def method_vikor(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float], v: float = 0.5) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    f_star = A.max(axis=0)
    f_minus = A.min(axis=0)
    denom = f_star - f_minus
    denom[denom == 0.0] = 1.0
    gap = (f_star - A) / denom
    S = (gap * w).sum(axis=1)
    R = (gap * w).max(axis=1)
    S_star, S_minus = S.min(), S.max()
    R_star, R_minus = R.min(), R.max()
    QS = (S - S_star) / (S_minus - S_star + 1e-12)
    QR = (R - R_star) / (R_minus - R_star + 1e-12)
    Q = v * QS + (1 - v) * QR
    score = 1.0 - Q
    return pd.Series(score, index=alts).sort_values(ascending=False)


def method_edas(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    avg = A.mean(axis=0)
    avg[avg == 0.0] = 1.0
    PDA = np.maximum(0.0, (A - avg) / avg)
    NDA = np.maximum(0.0, (avg - A) / avg)
    SP = PDA @ w
    SN = NDA @ w
    NSP = SP / (SP.max() + 1e-12)
    NSN = SN / (SN.max() + 1e-12)
    AS = (NSP + (1.0 - NSN)) / 2.0
    return pd.Series(AS, index=alts).sort_values(ascending=False)


def method_maut(pillar_scores: pd.DataFrame, weights_pct: Dict[str, float]) -> pd.Series:
    A, alts, crits = _decision_matrix(pillar_scores)
    w = _weights_vector(crits, weights_pct)
    lo = A.min(axis=0)
    hi = A.max(axis=0)
    denom = hi - lo
    denom[denom == 0.0] = 1.0
    U = (A - lo) / denom
    score = U @ w
    return pd.Series(score, index=alts).sort_values(ascending=False)


def method_pca(pillar_scores: pd.DataFrame) -> pd.Series:
    A, alts, _ = _decision_matrix(pillar_scores)
    if A.shape[0] < 2 or A.shape[1] < 1:
        return pd.Series(np.ones(A.shape[0]), index=alts)
    X = A - A.mean(axis=0)
    std = A.std(axis=0, ddof=1)
    std[std == 0.0] = 1.0
    X = X / std
    U, S, _ = np.linalg.svd(X, full_matrices=False)
    pc1_scores = U[:, 0] * S[0]
    mean_profile = X.mean(axis=1)
    if np.corrcoef(pc1_scores, mean_profile)[0, 1] < 0:
        pc1_scores = -pc1_scores
    lo, hi = pc1_scores.min(), pc1_scores.max()
    if hi - lo <= 1e-12:
        scaled = np.full_like(pc1_scores, 0.5)
    else:
        scaled = (pc1_scores - lo) / (hi - lo)
    return pd.Series(scaled, index=alts).sort_values(ascending=False)


def _scale_series_by_method(s: pd.Series, method: str) -> pd.Series:
    if s.empty:
        return s
    m = method.upper()
    if m == "WEIGHTED":
        base = PILLAR_SCORE_THEORETICAL_MAX
        return ((s / base) * OUTPUT_SCALE).clip(lower=MIN_DISPLAY_SCORE)
    if m in {"TOPSIS", "VIKOR", "EDAS", "MAUT", "PCA"}:
        return (s * OUTPUT_SCALE).clip(lower=MIN_DISPLAY_SCORE)
    if m == "RANK":
        lo, hi = float(s.min()), float(s.max())
        if math.isclose(hi, lo):
            return pd.Series([OUTPUT_SCALE / 2.0] * len(s), index=s.index)
        return (((s - lo) / (hi - lo)) * OUTPUT_SCALE).clip(lower=MIN_DISPLAY_SCORE)
    if m == "WPM":
        return (s * OUTPUT_SCALE).clip(lower=MIN_DISPLAY_SCORE)
    lo, hi = float(s.min()), float(s.max())
    if math.isclose(hi, lo):
        return pd.Series([OUTPUT_SCALE / 2.0] * len(s), index=s.index)
    return (((s - lo) / (hi - lo)) * OUTPUT_SCALE).clip(lower=MIN_DISPLAY_SCORE)


def prompt_pillar_weights(pillars: List[str]) -> Dict[str, float]:
    while True:
        weights: Dict[str, float] = {}
        print("\n🔢 Enter pillar weights (sum must equal 100%).")
        for p in pillars:
            w = prompt_float(f" - {p} (%): ", 0.0, 100.0)
            weights[p] = w
        total = sum(weights.values())
        if abs(total - 100.0) < 1e-6:
            return weights
        print(f"❌ Total = {total}. Must be exactly 100. Try again.")


def prompt_methods() -> List[str]:
    print("\n🧰 Select decision methods (comma-separated). Options:")
    print("   weighted, wpm, rank, topsis, vikor, edas, maut, pca")
    print("   - Press Enter for 'weighted' only. Type 'help' to view the quick course.")
    while True:
        raw = safe_input("   Methods: ").strip().lower()
        if raw == "":
            return ["WEIGHTED"]
        if _is_help(raw):
            method_cheatsheet()
            continue
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        allowed = {
            "weighted": "WEIGHTED",
            "wpm": "WPM",
            "rank": "RANK",
            "topsis": "TOPSIS",
            "vikor": "VIKOR",
            "edas": "EDAS",
            "maut": "MAUT",
            "pca": "PCA",
        }
        chosen: List[str] = []
        for p in parts:
            if p in allowed:
                tag = allowed[p]
                if tag not in chosen:
                    chosen.append(tag)
        if chosen:
            if "WEIGHTED" not in chosen:
                chosen.insert(0, "WEIGHTED")
            return chosen
        print("❌ Please enter valid methods (or press Enter). Type 'help' for the course.")


def plot_weight_donut(weights_pct: Dict[str, float], title: str = "Pillar Weights (%)") -> None:
    labels = list(weights_pct.keys())
    sizes = [weights_pct[k] for k in labels]

    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    wedges, _, _ = ax.pie(
        sizes,
        wedgeprops=dict(width=0.42),
        startangle=90,
        counterclock=False,
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        pctdistance=0.78,
    )
    ax.set_title(title)

    ax.text(0, 0, "100%", ha="center", va="center", fontsize=12)
    ax.legend(
        wedges,
        [f"{l} – {s:.1f}%" for l, s in zip(labels, sizes)],
        title="Pillars",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        frameon=False,
    )
    plt.show()


def _scenario_condition_text(weights_pct: Dict[str, float], methods: List[str], do_norm: bool) -> str:
    wtxt = ", ".join([f"{k}={v:.1f}%" for k, v in weights_pct.items()])
    mtxt = ", ".join(methods)
    ntx = "scaled 0–10" if do_norm else "raw"
    return f"Weights: {wtxt} | Methods: {mtxt} | Output: {ntx}"


def _scenario_barplot(df_to_plot: pd.DataFrame, title: str, ylabel: str) -> None:
    cols_for_plot = list(df_to_plot.columns)[:6]
    ax = df_to_plot[cols_for_plot].plot(kind="bar", figsize=(12, 6), title=title)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    plt.tight_layout()
    plt.show()


def plot_scenario_decision_heatmap(summary_by_scenario: pd.DataFrame, title: str) -> None:
    if summary_by_scenario.empty:
        return
    data = summary_by_scenario.copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data.values, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(data.columns, rotation=45, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(data.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8, label="SummaryScore")
    fig.tight_layout()
    plt.show()


def plot_scenario_best_scores(best_scores: pd.Series, title: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    best_scores.plot(kind="bar", ax=ax, title=title)
    ax.set_ylabel("Best SummaryScore")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def _scenario_rank_matrix(summary_by_scenario: pd.DataFrame) -> pd.DataFrame:
    if summary_by_scenario.empty:
        return summary_by_scenario
    ranks = summary_by_scenario.rank(ascending=False, method="average", axis=0)
    return ranks


def _scenario_rank_correlation(rank_matrix: pd.DataFrame) -> pd.DataFrame:
    if rank_matrix.empty:
        return pd.DataFrame()
    scenarios = list(rank_matrix.columns)
    m = len(scenarios)
    C = np.eye(m, dtype=float)
    for i in range(m):
        for j in range(i + 1, m):
            x = rank_matrix[scenarios[i]].to_numpy(dtype=float)
            y = rank_matrix[scenarios[j]].to_numpy(dtype=float)
            cx = x - x.mean()
            cy = y - y.mean()
            denom = float(np.sqrt((cx**2).sum()) * np.sqrt((cy**2).sum()))
            corr = float((cx * cy).sum() / denom) if denom > 0 else 0.0
            C[i, j] = corr
            C[j, i] = corr
    return pd.DataFrame(C, index=scenarios, columns=scenarios)


def plot_scenario_rank_stability_report(summary_by_scenario: pd.DataFrame) -> None:
    if summary_by_scenario.empty:
        return

    _print_header("📈 Scenario Comparison Report — Rank Stability Across Scenarios")

    rank_mat = _scenario_rank_matrix(summary_by_scenario)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(rank_mat.values, aspect="auto")
    ax.set_title("Rank Heatmap (1 = best) — across scenarios")
    ax.set_xticks(range(rank_mat.shape[1]))
    ax.set_xticklabels(rank_mat.columns, rotation=45, ha="right")
    ax.set_yticks(range(rank_mat.shape[0]))
    ax.set_yticklabels(rank_mat.index)
    for i in range(rank_mat.shape[0]):
        for j in range(rank_mat.shape[1]):
            ax.text(j, i, f"{rank_mat.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Rank")
    fig.tight_layout()
    plt.show()

    rank_std = rank_mat.std(axis=1).astype(float).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    rank_std.plot(kind="bar", ax=ax)
    ax.set_title("Rank Stability by Alternative (Std Dev across scenarios) — lower is more stable")
    ax.set_ylabel("Rank Std Dev")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()

    corr_df = _scenario_rank_correlation(rank_mat)
    if not corr_df.empty:
        fig, ax = plt.subplots(figsize=(8.8, 6.6))
        im = ax.imshow(corr_df.values, aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_title("Scenario Rank Similarity (Spearman correlation on ranks)")
        ax.set_xticks(range(corr_df.shape[1]))
        ax.set_xticklabels(corr_df.columns, rotation=45, ha="right")
        ax.set_yticks(range(corr_df.shape[0]))
        ax.set_yticklabels(corr_df.index)
        for i in range(corr_df.shape[0]):
            for j in range(corr_df.shape[1]):
                ax.text(j, i, f"{corr_df.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
        fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman corr")
        fig.tight_layout()
        plt.show()


def run_scenarios_with_methods(pillar_scores: pd.DataFrame) -> Tuple[List[pd.DataFrame], List[Dict[str, float]], List[List[str]], List[str]]:
    while True:
        print("\n🎯 SCENARIOS — build and view results; you can re-run as needed.")
        pillars = pillar_scores.index.tolist()

        n_scen = prompt_int("How many scenarios do you want to run? ", 1, 50)

        scenario_scaled_list: List[pd.DataFrame] = []
        scenario_weights_list: List[Dict[str, float]] = []
        scenario_methods_list: List[List[str]] = []
        scenario_condition_list: List[str] = []

        for sidx in range(n_scen):
            _print_header(f"SCENARIO {sidx + 1} / {n_scen}")

            print("Step 1: Define scenario conditions (pillar weights).")
            weights_pct = prompt_pillar_weights(pillars)

            print("\nStep 2: Select decision methods for this scenario.")
            methods = prompt_methods()

            per_method: Dict[str, pd.Series] = {}
            per_method["WEIGHTED"] = method_weighted(pillar_scores, weights_pct)
            if "WPM" in methods:
                per_method["WPM"] = method_wpm(pillar_scores, weights_pct)
            if "RANK" in methods:
                per_method["RANK"] = method_rank(pillar_scores, weights_pct)
            if "TOPSIS" in methods:
                per_method["TOPSIS"] = method_topsis(pillar_scores, weights_pct)
            if "VIKOR" in methods:
                per_method["VIKOR"] = method_vikor(pillar_scores, weights_pct, v=0.5)
            if "EDAS" in methods:
                per_method["EDAS"] = method_edas(pillar_scores, weights_pct)
            if "MAUT" in methods:
                per_method["MAUT"] = method_maut(pillar_scores, weights_pct)
            if "PCA" in methods:
                per_method["PCA"] = method_pca(pillar_scores)

            scenario_df = pd.DataFrame(per_method)
            scenario_df.index.name = "Alternative"

            norm_ans = safe_input("   Normalize outputs to 0–10 for display? [Y/n]: ").strip().lower()
            do_norm = norm_ans not in {"n", "no"}

            if do_norm:
                scaled_cols = {col: _scale_series_by_method(scenario_df[col], col) for col in scenario_df.columns}
                scenario_df_scaled = pd.DataFrame(scaled_cols, index=scenario_df.index)
            else:
                scenario_df_scaled = scenario_df.copy()

            cond_text = _scenario_condition_text(weights_pct, methods, do_norm)
            scenario_condition_list.append(cond_text)

            print(f"\n✅ Scenario {sidx + 1} conditions:")
            print(f"   {cond_text}")

            print("\n🏁 Scenario Results" + (" (0–10 scaled)" if do_norm else " (raw)") + ":")
            print(scenario_df_scaled.round(4))

            raw_title = f"Scenario {sidx + 1} – Results (RAW)\n{_scenario_condition_text(weights_pct, methods, do_norm=False)}"
            _scenario_barplot(scenario_df, raw_title, ylabel="Score (raw)")

            if do_norm:
                scaled_title = f"Scenario {sidx + 1} – Results (0–10 scaled)\n{cond_text}"
                _scenario_barplot(scenario_df_scaled, scaled_title, ylabel="Score (0–10)")

            plot_weight_donut(weights_pct, title=f"Scenario {sidx + 1} – Pillar Weights (%)")

            scenario_scaled_list.append(scenario_df_scaled)
            scenario_weights_list.append(weights_pct)
            scenario_methods_list.append(methods)

            # Always build a comparable 0–10 "ScenarioSummaryScore" for cross-scenario comparison,
            # even if user chose raw output for display in that scenario.
            scaled_for_compare = {
                col: _scale_series_by_method(scenario_df[col], col) for col in scenario_df.columns
            }
            scenario_compare_df = pd.DataFrame(scaled_for_compare, index=scenario_df.index)
            scenario_summary = scenario_compare_df.mean(axis=1).astype(float)

            print("\n📌 Scenario summary (0–10 comparable) — mean across selected methods:")
            print(scenario_summary.sort_values(ascending=False).round(4))

        # Build cross-scenario "ScenarioSummaryScore" matrix (alts × scenarios)
        scenario_names = [f"Scenario {i + 1}" for i in range(n_scen)]
        summary_cols: Dict[str, pd.Series] = {}
        for i, df_scaled in enumerate(scenario_scaled_list):
            # If df_scaled is already scaled 0–10, we can still compute a summary score
            # as mean across its columns, but it may mix raw/scaled depending on user choice.
            # So we reconstruct from raw "pillar_scores" + the stored weights/methods for a consistent 0–10 compare.
            weights_pct = scenario_weights_list[i]
            methods = scenario_methods_list[i]

            per_method: Dict[str, pd.Series] = {}
            per_method["WEIGHTED"] = method_weighted(pillar_scores, weights_pct)
            if "WPM" in methods:
                per_method["WPM"] = method_wpm(pillar_scores, weights_pct)
            if "RANK" in methods:
                per_method["RANK"] = method_rank(pillar_scores, weights_pct)
            if "TOPSIS" in methods:
                per_method["TOPSIS"] = method_topsis(pillar_scores, weights_pct)
            if "VIKOR" in methods:
                per_method["VIKOR"] = method_vikor(pillar_scores, weights_pct, v=0.5)
            if "EDAS" in methods:
                per_method["EDAS"] = method_edas(pillar_scores, weights_pct)
            if "MAUT" in methods:
                per_method["MAUT"] = method_maut(pillar_scores, weights_pct)
            if "PCA" in methods:
                per_method["PCA"] = method_pca(pillar_scores)

            raw_df = pd.DataFrame(per_method)
            scaled_cols = {col: _scale_series_by_method(raw_df[col], col) for col in raw_df.columns}
            scaled_df = pd.DataFrame(scaled_cols, index=raw_df.index)
            summary_cols[scenario_names[i]] = scaled_df.mean(axis=1).astype(float)

        summary_by_scenario = pd.DataFrame(summary_cols)
        _print_header("📌 Scenario Summary Report (Comparable 0–10 ScenarioSummaryScore)")
        for i, cond in enumerate(scenario_condition_list):
            print(f"{scenario_names[i]}: {cond}")
        print("\nScenarioSummaryScore (alts × scenarios):")
        print(summary_by_scenario.round(4))

        plot_scenario_decision_heatmap(summary_by_scenario, "Scenario SummaryScore Heatmap (0–10 comparable)")
        best_scores = summary_by_scenario.max(axis=0).astype(float)
        plot_scenario_best_scores(best_scores, "Best ScenarioSummaryScore per Scenario")
        plot_scenario_rank_stability_report(summary_by_scenario)

        if ask_yes_no("Do you want to edit anything or re-run this step?", default=False):
            continue

        return scenario_scaled_list, scenario_weights_list, scenario_methods_list, scenario_condition_list


# =============================================================================
# Validation (DEA + Monte-Carlo + SMAA + Weight Stability Intervals)
# =============================================================================
def validation_help() -> None:
    print(
        r"""
🔎 Validation — quick help

DEA (approximate, output-oriented, VRS-like sampling):
• A design is “efficient-ish” if convex mixes of others rarely dominate it across pillars.
• We simulate many peer mixes and estimate:
  - FrontierProb: fraction of random peer mixes that match/exceed the design.
  - PhiHat: maximal radial expansion factor still matched by peers (>=1).
  - EffOut = 1/PhiHat (higher is better).

Monte-Carlo sensitivity:
• Randomize weights (Dirichlet α) and add mild score noise (σ).
• Re-run chosen MCDA methods and summarize:
  - P(Best), mean/σ of ranks, rankograms.

SMAA (Stochastic Multicriteria Acceptability Analysis):
• Sample weights from a distribution (Dirichlet α).
• Compute Weighted-Sum ranking repeatedly.
• Outputs:
  - Rank acceptability indices: P(alt gets rank r)
  - Central weight vector: average weights conditional on the alt being best.

Weight Stability Intervals (Critical Weight Analysis, proportional-redistribution):
• For baseline WEIGHTED scenario:
  - For each pillar weight w_j, compute [min,max] interval such that the baseline winner stays winner,
    holding other weights in their baseline proportions.
"""
    )


def _dirichlet(alpha: np.ndarray) -> np.ndarray:
    samples = np.random.gamma(shape=alpha, scale=1.0)
    s = samples.sum()
    if s <= 0:
        return np.ones_like(alpha) / len(alpha)
    return samples / s


def approx_dea_diagnostics(
    pillar_scores: pd.DataFrame,
    samples: int = 5000,
    seed: Optional[int] = None,
    min_peer_lambda: float = 0.05,
    eps: float = 1e-9,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      dea_summary (index=Alt)
      peer_matrix (alts × alts, avg best-mix lambdas)
      targets (pillars × alts, projected target = phi_hat * current)
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    alts = list(pillar_scores.columns)
    pillars = list(pillar_scores.index)
    Y = pillar_scores.to_numpy().T  # m × n
    m, n = Y.shape

    frontier_hits = np.zeros(m, dtype=int)
    phi_hat = np.ones(m, dtype=float)
    best_lambda_store: List[Optional[np.ndarray]] = [None] * m

    for i in range(m):
        others = [k for k in range(m) if k != i]
        if not others:
            continue
        Y_others = Y[others, :]

        best_r = 1.0
        best_lamb = None

        for _ in range(samples):
            lamb = _dirichlet(np.ones(len(others)))
            mix = lamb @ Y_others

            denom = np.maximum(Y[i, :], eps)
            ratios = mix / denom
            r = float(np.min(ratios))

            if r >= 1.0:
                frontier_hits[i] += 1
                if r > best_r:
                    best_r = r
                    best_lamb = lamb

        phi_hat[i] = max(best_r, 1.0)
        best_lambda_store[i] = best_lamb

    eff_out = 1.0 / np.maximum(phi_hat, 1e-12)
    frontier_prob = frontier_hits / float(samples)

    dea_summary = pd.DataFrame(
        {
            "Alt": alts,
            "FrontierProb": frontier_prob,
            "PhiHat": phi_hat,
            "EffOut": eff_out,
        }
    ).set_index("Alt")

    peer = np.zeros((m, m), dtype=float)
    for i in range(m):
        others = [k for k in range(m) if k != i]
        lamb = best_lambda_store[i]
        if lamb is None:
            continue
        for w, k in zip(lamb, others):
            if w >= min_peer_lambda:
                peer[i, k] = w
    peer_matrix = pd.DataFrame(peer, index=alts, columns=alts)

    targets = pillar_scores.copy()
    for i_alt, alt in enumerate(alts):
        targets[alt] = pillar_scores[alt] * phi_hat[i_alt]

    return dea_summary, peer_matrix, targets


def run_monte_carlo_sensitivity(
    pillar_scores: pd.DataFrame,
    methods: Sequence[str],
    sims: int = 2000,
    weight_alpha: float = 1.0,
    score_noise_sigma: float = 0.03,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    methods = [m.upper() for m in methods]
    if "WEIGHTED" not in methods:
        methods = ["WEIGHTED"] + methods

    alts = pillar_scores.columns.tolist()
    pillars = pillar_scores.index.tolist()
    m = len(alts)
    n = len(pillars)

    best_counts: Dict[str, Dict[str, int]] = {meth: {a: 0 for a in alts} for meth in methods}
    rank_sum: Dict[str, np.ndarray] = {meth: np.zeros(m, dtype=float) for meth in methods}
    rank_sqsum: Dict[str, np.ndarray] = {meth: np.zeros(m, dtype=float) for meth in methods}
    rank_counts: Dict[str, np.ndarray] = {meth: np.zeros((m, m), dtype=int) for meth in methods}

    A0 = pillar_scores.to_numpy().T  # m × n
    alpha_vec = np.full(n, float(weight_alpha))

    for _ in range(sims):
        w = _dirichlet(alpha_vec)
        noise = np.random.normal(0.0, score_noise_sigma, size=A0.shape)
        A = np.clip(A0 + noise, a_min=0.0, a_max=None)
        dfA = pd.DataFrame(A.T, index=pillars, columns=alts)

        w_pct = {p: w[i] * 100.0 for i, p in enumerate(pillars)}
        per_method: Dict[str, pd.Series] = {}
        per_method["WEIGHTED"] = method_weighted(dfA, w_pct)
        if "WPM" in methods:
            per_method["WPM"] = method_wpm(dfA, w_pct)
        if "RANK" in methods:
            per_method["RANK"] = method_rank(dfA, w_pct)
        if "TOPSIS" in methods:
            per_method["TOPSIS"] = method_topsis(dfA, w_pct)
        if "VIKOR" in methods:
            per_method["VIKOR"] = method_vikor(dfA, w_pct, v=0.5)
        if "EDAS" in methods:
            per_method["EDAS"] = method_edas(dfA, w_pct)
        if "MAUT" in methods:
            per_method["MAUT"] = method_maut(dfA, w_pct)
        if "PCA" in methods:
            per_method["PCA"] = method_pca(dfA)

        for meth, s in per_method.items():
            s_sorted = s.sort_values(ascending=False)
            winner = s_sorted.index[0]
            best_counts[meth][winner] += 1
            ranks = s.rank(ascending=False, method="average")
            rank_vals = ranks.loc[alts].to_numpy(dtype=float)

            # rankogram
            for i_alt, rk in enumerate(rank_vals.astype(int)):
                rk = int(max(1, min(m, rk)))
                rank_counts[meth][i_alt, rk - 1] += 1

            rank_sum[meth] += rank_vals
            rank_sqsum[meth] += rank_vals**2

    pbest_rows = []
    for meth, d in best_counts.items():
        for a in alts:
            pbest_rows.append({"Method": meth, "Alt": a, "P(Best)": d[a] / float(sims)})
    Pbest = pd.DataFrame(pbest_rows).pivot(index="Alt", columns="Method", values="P(Best)").fillna(0.0)

    mean_rows = []
    std_rows = []
    RankDist: Dict[str, pd.DataFrame] = {}
    for meth in methods:
        mu = rank_sum[meth] / float(sims)
        var = (rank_sqsum[meth] / float(sims)) - (mu**2)
        var = np.maximum(var, 0.0)
        sd = np.sqrt(var)
        for i, a in enumerate(alts):
            mean_rows.append({"Method": meth, "Alt": a, "MeanRank": mu[i]})
            std_rows.append({"Method": meth, "Alt": a, "StdRank": sd[i]})
        rd = (rank_counts[meth] / float(sims))
        RankDist[meth] = pd.DataFrame(rd, index=alts, columns=[f"rank_{k}" for k in range(1, m + 1)])

    MeanRank = pd.DataFrame(mean_rows).pivot(index="Alt", columns="Method", values="MeanRank")
    StdRank = pd.DataFrame(std_rows).pivot(index="Alt", columns="Method", values="StdRank")
    return Pbest, MeanRank, StdRank, RankDist


def plot_pbest(series: pd.Series, title: str) -> None:
    if series.empty:
        print("(No data to plot.)")
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    series = series.astype(float).sort_values(ascending=False)
    series.plot(kind="bar", ax=ax, title=title)
    ax.set_ylabel("Probability")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_rankogram(rankdist: pd.DataFrame, method: str) -> None:
    if rankdist.empty:
        return
    df = rankdist.copy()
    df = df.loc[:, sorted(df.columns, key=lambda c: int(c.split("_")[1]))]
    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = np.zeros(df.shape[0])
    x = np.arange(df.shape[0])
    for col in df.columns:
        ax.bar(x, df[col].values, bottom=bottom, width=0.8, label=col.replace("_", " ").title())
        bottom += df[col].values
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=0)
    ax.set_ylabel("Probability")
    ax.set_title(f"Rankogram – {method}")
    ax.legend(ncol=min(df.shape[1], 5), frameon=False)
    plt.show()


def plot_mc_heatmaps(Pbest: pd.DataFrame, MeanRank: pd.DataFrame) -> None:
    for name, mat, cmap, label in [
        ("P(Best)", Pbest, "Greens", "Probability"),
        ("Mean Rank", MeanRank, "RdYlGn_r", "Rank (lower=better)"),
    ]:
        if mat.empty:
            continue
        data = mat.copy()
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(data.values, aspect="auto", cmap=cmap)
        ax.set_xticks(range(data.shape[1]))
        ax.set_xticklabels(data.columns, rotation=45, ha="right")
        ax.set_yticks(range(data.shape[0]))
        ax.set_yticklabels(data.index)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, f"{data.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
        ax.set_title(f"Monte-Carlo – {name}")
        fig.colorbar(im, ax=ax, shrink=0.8, label=label)
        fig.tight_layout()
        plt.show()


# -------------------------
# SMAA
# -------------------------
def run_smaa(
    pillar_scores: pd.DataFrame,
    sims: int = 5000,
    weight_alpha: float = 1.0,
    seed: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """
    SMAA for WEIGHTED (WSM) using sampled weights.

    Returns:
      rank_acceptability: DataFrame index=Alt, columns=rank_1..rank_m (probabilities)
      p_best: Series index=Alt, probability of being best
      central_weights: DataFrame index=Alt, columns=pillars (avg weights conditional on being best)
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    alts = pillar_scores.columns.tolist()
    pillars = pillar_scores.index.tolist()
    m = len(alts)
    n = len(pillars)

    rank_counts = np.zeros((m, m), dtype=int)
    best_counts = np.zeros(m, dtype=int)
    alpha_vec = np.full(n, float(weight_alpha))

    best_weight_sum = np.zeros((m, n), dtype=float)
    best_weight_count = np.zeros(m, dtype=int)

    A = pillar_scores.to_numpy().T  # m × n

    for _ in range(sims):
        w = _dirichlet(alpha_vec)
        scores = A @ w
        order = np.argsort(-scores)  # descending
        ranks = np.empty(m, dtype=int)
        ranks[order] = np.arange(1, m + 1)

        for i_alt in range(m):
            rank_counts[i_alt, ranks[i_alt] - 1] += 1

        winner_idx = int(order[0])
        best_counts[winner_idx] += 1
        best_weight_sum[winner_idx, :] += w
        best_weight_count[winner_idx] += 1

    rank_acceptability = pd.DataFrame(
        rank_counts / float(sims),
        index=alts,
        columns=[f"rank_{k}" for k in range(1, m + 1)],
    )
    p_best = pd.Series(best_counts / float(sims), index=alts).sort_values(ascending=False)

    central = np.zeros((m, n), dtype=float)
    for i in range(m):
        if best_weight_count[i] > 0:
            central[i, :] = best_weight_sum[i, :] / float(best_weight_count[i])
        else:
            central[i, :] = np.ones(n, dtype=float) / float(n)
    central_weights = pd.DataFrame(central, index=alts, columns=pillars)

    return rank_acceptability, p_best, central_weights


def plot_smaa_rank_acceptability(rank_acceptability: pd.DataFrame, title: str) -> None:
    if rank_acceptability.empty:
        return
    data = rank_acceptability.copy()
    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(data.values, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(data.columns, rotation=45, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(data.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Probability")
    fig.tight_layout()
    plt.show()


def plot_smaa_central_weights(central_weights: pd.DataFrame, title: str) -> None:
    if central_weights.empty:
        return
    data = central_weights.copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data.values, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(data.columns, rotation=45, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(data.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Weight")
    fig.tight_layout()
    plt.show()


# -------------------------
# Weight Stability Intervals (Critical Weight Analysis)
# -------------------------
def critical_weight_intervals_proportional(
    pillar_scores: pd.DataFrame,
    baseline_weights_pct: Dict[str, float],
) -> Tuple[str, pd.DataFrame]:
    """
    For baseline WEIGHTED winner, compute interval for each weight w_j in [0,1]
    such that winner remains winner, holding other weights in baseline proportions.

    Returns:
      winner_alt
      intervals_df: columns=[baseline_pct, min_pct, max_pct]
    """
    alts = pillar_scores.columns.tolist()
    pillars = pillar_scores.index.tolist()
    w0 = _weights_vector(pillars, baseline_weights_pct)  # sums to 1

    A = pillar_scores.to_numpy().T  # m × n
    scores0 = A @ w0
    winner_idx = int(np.argmax(scores0))
    winner = alts[winner_idx]

    intervals = []
    for j, pillar in enumerate(pillars):
        wj0 = float(w0[j])
        denom_other = (1.0 - wj0)
        # If denom_other ~ 0, weight is essentially 1 already, interval is [1,1]
        if abs(denom_other) < 1e-12:
            intervals.append((pillar, wj0, 1.0, 1.0))
            continue

        # intersection over competitors: t in [0,1]
        t_min = 0.0
        t_max = 1.0

        for b_idx, b in enumerate(alts):
            if b == winner:
                continue
            delta = A[winner_idx, :] - A[b_idx, :]
            A_j = float(delta[j])

            # B = sum_{k!=j} w0_k * delta_k / (1-w0_j)
            B = float(np.dot(np.delete(w0, j), np.delete(delta, j)) / denom_other)

            # inequality: t*A_j + (1-t)*B >= 0  ->  t*(A_j - B) + B >= 0
            c = A_j - B
            d = B

            if abs(c) < 1e-12:
                # constraint becomes B >= 0, else infeasible
                if d < -1e-12:
                    t_min, t_max = 1.0, 0.0
                    break
                continue

            bound = (-d) / c
            if c > 0:
                # t >= bound
                t_min = max(t_min, bound)
            else:
                # t <= bound
                t_max = min(t_max, bound)

        t_min = float(np.clip(t_min, 0.0, 1.0))
        t_max = float(np.clip(t_max, 0.0, 1.0))
        if t_min > t_max:
            # no feasible interval
            t_min, t_max = float("nan"), float("nan")

        intervals.append((pillar, wj0, t_min, t_max))

    df = pd.DataFrame(intervals, columns=["Pillar", "baseline", "min", "max"]).set_index("Pillar")
    df["baseline_pct"] = df["baseline"] * 100.0
    df["min_pct"] = df["min"] * 100.0
    df["max_pct"] = df["max"] * 100.0
    return winner, df[["baseline_pct", "min_pct", "max_pct"]]


def plot_weight_stability_intervals(intervals_df: pd.DataFrame, winner: str, title: str) -> None:
    if intervals_df.empty:
        return
    df = intervals_df.copy()
    df = df.sort_values("baseline_pct", ascending=False)

    y = np.arange(df.shape[0])
    x_min = df["min_pct"].to_numpy(dtype=float)
    x_max = df["max_pct"].to_numpy(dtype=float)
    x0 = df["baseline_pct"].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hlines(y, x_min, x_max, linewidth=4)
    ax.plot(x0, y, marker="o", linewidth=0)

    ax.set_yticks(y)
    ax.set_yticklabels(df.index.tolist())
    ax.set_xlabel("Weight (%)")
    ax.set_title(f"{title}\nBaseline winner: {winner}")
    ax.grid(True, axis="x", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_dea_peer_heatmap(peer_matrix: pd.DataFrame, title: str) -> None:
    if peer_matrix.empty:
        return
    data = peer_matrix.copy()
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(data.values, aspect="auto", cmap="Blues")
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(data.columns, rotation=45, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(data.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data.values[i, j]
            if val > 0:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Weight")
    fig.tight_layout()
    plt.show()


def plot_dea_targets_heatmap(pillar_scores: pd.DataFrame, targets: pd.DataFrame, title: str) -> None:
    if pillar_scores.empty or targets.empty:
        return
    alts = pillar_scores.columns.tolist()
    pillars = pillar_scores.index.tolist()

    # Show target expansion factor (targets/current), clipped.
    ratios = pd.DataFrame(index=pillars, columns=alts, dtype=float)
    for a in alts:
        cur = pillar_scores[a].astype(float).to_numpy()
        tgt = targets[a].astype(float).to_numpy()
        denom = np.maximum(cur, 1e-12)
        ratios[a] = (tgt / denom)

    data = ratios.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data, aspect="auto", cmap="OrRd")
    ax.set_title(title)
    ax.set_xticks(range(len(alts)))
    ax.set_xticklabels(alts, rotation=45, ha="right")
    ax.set_yticks(range(len(pillars)))
    ax.set_yticklabels(pillars)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Target / Current (≈phi)")
    fig.tight_layout()
    plt.show()


def run_validation_suite_interactive(
    pillar_scores: pd.DataFrame,
    last_weights_pct: Dict[str, float],
    last_methods: Sequence[str],
    scenario_label: str = "",
) -> None:
    tag = f" — {scenario_label}" if scenario_label else ""
    print(f"\n🔎 Validation Suite{tag} — DEA (approx) & Monte-Carlo + SMAA + Weight Stability")
    raw = safe_input("   Show validation help? [y/N]: ").strip().lower()
    if raw in {"y", "yes", "help", "h", "?"}:
        validation_help()

    while True:
        dea_samples = int(prompt_float_or_default("   DEA convex-hull samples", 5000, 500, 200000))
        peer_cut = prompt_float_or_default("   Peer weight display cutoff", 0.05, 0.0, 1.0)

        sims = int(prompt_float_or_default("   Monte-Carlo simulations", 2000, 100, 200000))
        alpha = prompt_float_or_default("   Dirichlet alpha (1.0=uniform)", 1.0, 0.1, 10.0)
        sigma = prompt_float_or_default("   Score noise sigma (0.0–0.2)", 0.03, 0.0, 0.5)

        smaa_sims = int(prompt_float_or_default("   SMAA simulations (weights)", 5000, 500, 200000))
        smaa_alpha = prompt_float_or_default("   SMAA Dirichlet alpha", 1.0, 0.1, 10.0)

        print("\n▶ DEA (approx) — computing diagnostics...")
        dea_summary, peer_matrix, targets = approx_dea_diagnostics(
            pillar_scores, samples=dea_samples, min_peer_lambda=peer_cut
        )
        print("\nDEA Summary (EffOut=1/φ̂; higher is better; FrontierProb≈efficiency frequency):")
        print(dea_summary.sort_values(["EffOut", "FrontierProb"], ascending=[False, False]).round(3))

        # Fix: ensure DEA FrontierProb plot always renders with proper y-limits
        plot_pbest(dea_summary["FrontierProb"], f"Approx. DEA Frontier Probability{tag}")
        plot_dea_peer_heatmap(peer_matrix, f"DEA Peer Reference Weights (avg best mix){tag}")
        plot_dea_targets_heatmap(pillar_scores, targets, f"DEA Target Expansion (targets/current){tag}")

        print("\n▶ Monte-Carlo sensitivity — running simulations...")
        Pbest, MeanRank, StdRank, RankDist = run_monte_carlo_sensitivity(
            pillar_scores,
            last_methods,
            sims=sims,
            weight_alpha=alpha,
            score_noise_sigma=sigma,
        )
        print("\nMonte-Carlo — P(Best):")
        print(Pbest.fillna(0.0).round(4))
        if "WEIGHTED" in Pbest.columns:
            plot_pbest(Pbest["WEIGHTED"], f"Monte-Carlo P(Best) — WEIGHTED{tag}")
            plot_rankogram(RankDist["WEIGHTED"], f"WEIGHTED{tag}")
        plot_mc_heatmaps(Pbest, MeanRank)

        print("\nMonte-Carlo — Mean Rank (lower is better):")
        print(MeanRank.round(3))
        print("\nMonte-Carlo — Rank Std Dev (lower = more stable):")
        print(StdRank.round(3))

        print("\n▶ SMAA — rank acceptability + central weights (WEIGHTED only)...")
        rank_acc, p_best, central_w = run_smaa(
            pillar_scores,
            sims=smaa_sims,
            weight_alpha=smaa_alpha,
        )
        print("\nSMAA — P(Best) (WEIGHTED):")
        print(p_best.round(4))
        print("\nSMAA — Central weight vectors (conditional on being best):")
        print((central_w * 100.0).round(2))

        plot_smaa_rank_acceptability(rank_acc, f"SMAA Rank Acceptability (WEIGHTED){tag}")
        plot_pbest(p_best, f"SMAA P(Best) — WEIGHTED{tag}")
        plot_smaa_central_weights(central_w, f"SMAA Central Weights (WEIGHTED){tag}")

        print("\n▶ Weight Stability Intervals — baseline winner robustness (WEIGHTED)...")
        winner, intervals_df = critical_weight_intervals_proportional(pillar_scores, last_weights_pct)
        print(f"\nBaseline winner (WEIGHTED): {winner}")
        print("\nCritical Weight Intervals (proportional redistribution):")
        print(intervals_df.round(2))
        plot_weight_stability_intervals(intervals_df, winner, f"Weight Stability Intervals (Critical Weight){tag}")

        again = safe_input("\nRe-run validation with different settings? [y/N] → ").strip().lower()
        if again not in {"y", "yes"}:
            break


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    apply_pro_style()
    method_cheatsheet()

    # Build model from your indicator list
    model = parse_indicator_model(RAW_INDICATORS_TSV)

    # Ask whether user is evaluating process designs or technologies
    _print_header("Label choice")
    kind = ask_choice("Are you evaluating a (1) Process design or (2) Technology? [1/2]: ", ["1", "2"])
    alt_term_singular = "process design" if kind == "1" else "technology"
    alt_term_plural = "process designs" if kind == "1" else "technologies"

    # Show built-in structure first
    print_model_structure(model)

    # Ask whether to edit pillars/key issues before AHP; if yes also edit indicators metadata
    if ask_yes_no("Do you want to add/remove pillar or key issues before running AHP?", default=False):
        pillars_to_issues = _pillars_to_issues_from_model(model)
        pillars_to_issues = edit_pillars_and_issues(pillars_to_issues)
        model = apply_pillar_issue_scope_to_model(model, pillars_to_issues)

        print("\nNow update indicators + metadata needed for scoring (Unit / Formula / Criteria / Mode).")
        model = edit_indicators_in_model(model)

    # AHP/FAHP at start (per pillar key-issue weights)
    model, weights_by_pillar_df, chosen_method = run_ahp_fahp_section(model)
    issue_weights = extract_issue_weights(weights_by_pillar_df, chosen_method)

    # ESGFP loop
    while True:
        # GM numeric base is not separately requested here; GE per-indicator drives GM.
        gm_value = 0.0

        scores_by_alt, comments_by_alt = esgfp_section(
            model=model,
            issue_weights=issue_weights,
            gm_value=gm_value,
            alt_term_singular=alt_term_singular,
            alt_term_plural=alt_term_plural,
        )

        # Summary visuals BEFORE scenarios
        _, _, pillar_scores_df = display_scoring_summary_before_scenarios(
            scores_by_alt=scores_by_alt,
            model=model,
            alt_term_singular=alt_term_singular,
            comments_by_alt=comments_by_alt,
        )

        # Scenarios
        scenario_df_list, scenario_weights_list, scenario_methods_list, scenario_condition_list = run_scenarios_with_methods(
            pillar_scores_df
        )

        # After scenarios: validate each scenario if desired
        ans = safe_input("\n🧪 Run validation (DEA + Monte-Carlo + SMAA + Weight Stability) for EACH scenario now? [Y/n]: ").strip().lower()
        if ans not in {"n", "no"}:
            for i, _ in enumerate(scenario_df_list):
                scenario_label = f"Scenario {i + 1}"
                print("\n" + "-" * 80)
                print(f"VALIDATION — {scenario_label}")
                print("-" * 80)
                print(f"Conditions: {scenario_condition_list[i]}")
                run_validation_suite_interactive(
                    pillar_scores=pillar_scores_df,
                    last_weights_pct=scenario_weights_list[i],
                    last_methods=scenario_methods_list[i],
                    scenario_label=scenario_label,
                )

        again = safe_input(
            f"\n✅ Do you want to exit or continue with NEW ESGFP calculations? [E]xit / [C]ontinue → "
        ).strip().lower()
        if again in {"e", "exit"}:
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()

