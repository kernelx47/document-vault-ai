#!/usr/bin/env python3
"""Generate synthetic commercial insurance demo PDFs + SUMMARY.md files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fpdf import FPDF

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "demo-docs"

BROKERS = [
    "Horizon Risk Partners",
    "Cedar Street Insurance Group",
    "Atlas Brokerage Services",
    "Northgate Commercial Lines",
    "Summit Underwriters LLC",
    "Meridian Agency Partners",
    "Bridgepoint Risk Advisors",
    "Keystone P&C Brokers",
]

CARRIERS = [
    "Meridian Mutual Insurance Company",
    "Pioneer Commercial Group",
    "Atlas National P&C",
    "Frontier Indemnity Company",
    "Harborline Insurance Group",
    "Granite State Mutual",
    "Copper Ridge Underwriters",
    "Blue Summit Insurance Co.",
]

LANDLORDS = [
    "Lakeside Industrial REIT LLC",
    "Parkview Commercial Properties",
    "Gateway Industrial Holdings",
    "Redstone Warehouse REIT",
    "Union Pier Logistics Parks",
    "Broadway Office Towers LLC",
    "Centennial Business Park REIT",
    "Harborview Mixed-Use Holdings",
]

CLIENTS = [
    ("Northstar Fulfillment Inc.", "Northstar Distribution Center", "1200 Commerce Way, Phoenix AZ 85043"),
    ("Blue Ridge Manufacturing LLC", "Blue Ridge Precision Parts", "4550 Foundry Lane, Charlotte NC 28208"),
    ("Coastal Catering Supply Co.", "Coastal Foodservice Depot", "88 Harbor Drive, Tampa FL 33602"),
    ("Prairie Cold Storage LLC", "Prairie Cold Chain Logistics", "7100 Grain Elevator Rd, Omaha NE 68107"),
    ("Metro Print & Packaging Inc.", "Metro Label Solutions", "220 Industrial Blvd, Columbus OH 43228"),
    ("Silver Creek Auto Parts LLC", "Silver Creek Wholesale Parts", "990 Truck Route, Nashville TN 37210"),
    ("Cascade Beverage Distributors", "Cascade Beverage Warehouse", "501 Brewery Row, Portland OR 97209"),
    ("Ironwood Building Materials", "Ironwood Lumber & Supply", "3400 Mill Road, Denver CO 80216"),
    ("Harbor Tech Assembly LLC", "Harbor Electronics Assembly", "77 Innovation Park, San Jose CA 95134"),
    ("Greenline Organic Foods Inc.", "Greenline Natural Foods DC", "1600 Organic Way, Austin TX 78744"),
    ("Valley Medical Supply LLC", "Valley Healthcare Logistics", "410 Carepark Circle, Salt Lake City UT 84104"),
    ("Sunbelt Equipment Rental", "Sunbelt Heavy Equipment", "8800 Rental Yard, Atlanta GA 30336"),
    ("Keystone Craft Brewery LLC", "Keystone Brewing & Bottling", "12 Brewery Lane, Milwaukee WI 53204"),
    ("Pacific Seafood Processors", "Pacific Catch Processing", "500 Dockside Ave, Seattle WA 98108"),
    ("Midwest Tire Wholesale Inc.", "Midwest Tire Distribution", "6700 Tire Parkway, Kansas City MO 64129"),
    ("Alpine Ski Resort Services LLC", "Alpine Lodge Hospitality Supply", "200 Mountain Rd, Burlington VT 05401"),
    ("Desert Sun Solar Installers", "Desert Sun Energy Contractors", "4500 Solar Way, Las Vegas NV 89118"),
    ("Great Lakes Freight LLC", "Great Lakes Regional Trucking", "1900 Port Authority Dr, Cleveland OH 44114"),
    ("Magnolia Event Rentals Inc.", "Magnolia Party & Tent Rental", "330 Celebration Ave, New Orleans LA 70125"),
    ("Red Oak Furniture Works", "Red Oak Custom Manufacturing", "800 Craftsman Blvd, Grand Rapids MI 49503"),
    ("Sterling Dental Labs LLC", "Sterling Dental Prosthetics", "55 Medical Park Dr, Raleigh NC 27607"),
    ("Timberline Logging Co.", "Timberline Forest Products", "Route 9 Mile 12, Boise ID 83714"),
    ("Urban Eats Restaurant Group", "Urban Eats Commissary Kitchen", "1440 Kitchen Row, Chicago IL 60608"),
    ("Vantage Data Centers LLC", "Vantage Colocation Services", "900 Server Farm Pkwy, Ashburn VA 20147"),
    ("Westwind Aviation Services", "Westwind FBO & Hangar Ops", "1 Airport Rd, Wichita KS 67209"),
    ("Yosemite Trail Outfitters", "Yosemite Outdoor Gear Wholesale", "610 Trailhead Way, Fresno CA 93711"),
    ("Beacon Home Health LLC", "Beacon In-Home Care Services", "275 Wellness Circle, Indianapolis IN 46204"),
    ("Copper Canyon Mining Supply", "Copper Canyon Industrial Supply", "4200 Mine Road, Tucson AZ 85706"),
    ("Delta Plastics Recycling", "Delta Recycled Materials", "750 Greenway Dr, Houston TX 77015"),
]

PRODUCERS = [
    ("Jordan Lee", "jlee@horizonrisk.demo"),
    ("Maria Santos", "msantos@cedarstreet.demo"),
    ("David Chen", "dchen@northgate.demo"),
    ("Emily Hart", "ehart@bridgepoint.demo"),
    ("Robert Kim", "rkim@keystone.demo"),
    ("Sarah Nguyen", "snguyen@atlasbroker.demo"),
    ("Michael Torres", "mtorres@meridianagency.demo"),
    ("Lisa Patel", "lpatel@summituw.demo"),
]


@dataclass
class Account:
    legal_name: str
    dba: str
    address: str
    broker: str
    producer_name: str
    producer_email: str
    prefix: str
    effective: date
    renewal: date


def _money(value: int) -> str:
    return f"USD {value:,}"


def _pdf_text(text: str) -> str:
    """Normalize text for core PDF fonts (Helvetica = Latin-1)."""
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2192", "->")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def _write_pdf(path: Path, title: str, lines: list[str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(pdf.epw, 7, _pdf_text(f"DEMO - {title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    for line in lines:
        if line.strip():
            pdf.multi_cell(pdf.epw, 5, _pdf_text(line), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(3)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def _write_summary(path: Path, body: str) -> None:
    path.write_text(body.strip() + "\n", encoding="utf-8")


def _account(index: int) -> Account:
    legal, dba, address = CLIENTS[index % len(CLIENTS)]
    broker = BROKERS[index % len(BROKERS)]
    producer_name, producer_email = PRODUCERS[index % len(PRODUCERS)]
    year = 2026 + (index % 3)
    month = 1 + (index % 12)
    effective = date(year, month, 1)
    renewal = date(year + 1, month, 1)
    prefix = "".join(part[0] for part in legal.split()[:2]).upper()[:3] + str(100 + index)
    return Account(
        legal_name=legal,
        dba=dba,
        address=address,
        broker=broker,
        producer_name=producer_name,
        producer_email=producer_email,
        prefix=prefix,
        effective=effective,
        renewal=renewal,
    )


def _gl_policy(account: Account, variant: int) -> tuple[str, list[str], str]:
    carrier = CARRIERS[variant % len(CARRIERS)]
    gl_occ = 1_000_000 + (variant % 4) * 500_000
    gl_agg = gl_occ * 2
    building = 2_500_000 + (variant % 5) * 250_000
    bpp = 500_000 + (variant % 6) * 50_000
    ded = 5_000 + (variant % 4) * 2_500
    policy_no = f"{account.prefix}-GLPR-{account.effective.year}-{11800 + variant}"
    title = "Commercial GL and Property Policy Summary"
    lines = [
        f"Named insured: {account.legal_name} dba {account.dba}",
        f"Risk location: {account.address}",
        f"Policy number: {policy_no}",
        f"Carrier: {carrier}",
        f"Policy period: {account.effective.strftime('%B %d, %Y')} to {account.renewal.strftime('%B %d, %Y')}",
        f"General liability: {_money(gl_occ)} per occurrence / {_money(gl_agg)} aggregate",
        f"Products and completed operations: {_money(gl_occ)} aggregate",
        f"Commercial property building limit: {_money(building)}",
        f"Business personal property (BPP): {_money(bpp)}",
        f"Property deductible: {_money(ded)} per occurrence",
        "GL deductible: USD 0",
        "Additional insured: Landlord or project owner when required by written contract",
        f"Broker of record: {account.broker}",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name} dba {account.dba}  
**Type:** Commercial GL + Property policy summary (synthetic demo)

## Policy basics
- **Policy number:** {policy_no}
- **Carrier:** {carrier}
- **Location:** {account.address}
- **Period:** {account.effective.isoformat()} → {account.renewal.isoformat()}

## Limits & deductibles
| Coverage | Limit |
|----------|-------|
| GL per occurrence | {_money(gl_occ)} |
| GL aggregate | {_money(gl_agg)} |
| Products/completed ops aggregate | {_money(gl_occ)} |
| Building | {_money(building)} |
| Business personal property (BPP) | {_money(bpp)} |
| Property deductible | {_money(ded)} |
| GL deductible | USD 0 |

## Suggested chatbot questions
1. What are {account.dba}'s GL limits?
2. What is the property deductible on this policy?
3. Who is the carrier and when does coverage renew?
"""
    return title, lines, summary


def _wc_policy(account: Account, variant: int) -> tuple[str, list[str], str]:
    carrier = CARRIERS[(variant + 2) % len(CARRIERS)]
    mod = round(0.88 + (variant % 9) * 0.02, 2)
    el_each = 500_000 + (variant % 3) * 500_000
    payroll = 1_200_000 + variant * 85_000
    policy_no = f"{account.prefix}-WC-{account.effective.year}-{22000 + variant}"
    title = "Workers Compensation Policy Summary"
    lines = [
        f"Employer: {account.legal_name}",
        f"Operations: {account.dba} — {account.address}",
        f"Policy number: {policy_no}",
        f"Carrier: {carrier}",
        f"Policy period: {account.effective.strftime('%B %d, %Y')} to {account.renewal.strftime('%B %d, %Y')}",
        f"Estimated annual payroll: {_money(payroll)}",
        f"Experience modification factor: {mod}",
        f"Employers liability: {_money(el_each)} each accident / {_money(el_each)} policy limit",
        "Statutory workers compensation: As required by state law",
        f"Governing classification: Warehouse — NCCI {5800 + (variant % 40)}",
        f"Broker: {account.broker}",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Type:** Workers compensation policy summary (synthetic demo)

## Policy basics
- **Policy number:** {policy_no}
- **Carrier:** {carrier}
- **Experience mod:** {mod}
- **Payroll:** {_money(payroll)}

## Suggested chatbot questions
1. What is the experience modification factor?
2. What are the employers liability limits?
3. Which NCCI class code applies?
"""
    return title, lines, summary


def _quote_comparison(account: Account, variant: int) -> tuple[str, list[str], str]:
    c1, c2, c3 = CARRIERS[variant % len(CARRIERS)], CARRIERS[(variant + 1) % len(CARRIERS)], CARRIERS[(variant + 3) % len(CARRIERS)]
    p1, p2, p3 = 98_000 + variant * 1200, 94_500 + variant * 1100, 102_800 + variant * 1300
    gl = _money(1_500_000 + (variant % 3) * 500_000)
    title = "Renewal Quote Comparison Memorandum"
    lines = [
        f"Account: {account.legal_name} — {account.address}",
        f"Broker: {account.broker}",
        f"Proposed effective date: {account.effective.strftime('%B %d, %Y')}",
        "",
        f"Option A — {c1}: Total premium {_money(p1)} | GL {gl} | Property {_money(3_000_000 + variant * 100_000)} | Deductible {_money(10_000)}",
        f"Option B — {c2}: Total premium {_money(p2)} | GL {gl} | Property {_money(3_000_000 + variant * 100_000)} | Deductible {_money(15_000)}",
        f"Option C — {c3}: Total premium {_money(p3)} | GL {gl} | Property {_money(3_500_000 + variant * 100_000)} | Deductible {_money(10_000)}",
        "",
        f"Lowest premium option: {c2} at {_money(p2)}",
        f"Broadest property limit: {c3}",
        "Note: Option B excludes equipment breakdown unless endorsed",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Broker:** {account.broker}  
**Type:** Renewal quote comparison (synthetic demo)

## Quotes
| Carrier | Total premium |
|---------|---------------|
| A — {c1.split()[0]} | {_money(p1)} |
| B — {c2.split()[0]} | {_money(p2)} |
| C — {c3.split()[0]} | {_money(p3)} |

## Suggested chatbot questions
1. Which carrier has the lowest total premium?
2. What coverage gap exists on the lowest-price option?
"""
    return title, lines, summary


def _broker_proposal(account: Account, variant: int) -> tuple[str, list[str], str]:
    gl_carrier = CARRIERS[(variant + 1) % len(CARRIERS)]
    wc_carrier = CARRIERS[(variant + 4) % len(CARRIERS)]
    auto_carrier = CARRIERS[(variant + 2) % len(CARRIERS)]
    gl_prem = 88_000 + variant * 900
    wc_prem = 36_000 + variant * 700
    auto_prem = 18_000 + variant * 450
    total = gl_prem + wc_prem + auto_prem
    units = 3 + (variant % 6)
    bind_day = max(1, account.effective.day - 10)
    bind = account.effective.replace(day=bind_day)
    title = "Client Insurance Proposal"
    lines = [
        f"Prepared for: {account.legal_name}",
        f"Presented by: {account.broker}",
        f"Producer: {account.producer_name} — {account.producer_email}",
        f"Recommended effective date: {account.effective.strftime('%B %d, %Y')}",
        f"Bind deadline: {bind.strftime('%B %d, %Y')}",
        "",
        f"GL + Property — {gl_carrier}: {_money(gl_prem)}",
        f"Workers compensation — {wc_carrier}: {_money(wc_prem)}",
        f"Commercial auto ({units} units) — {auto_carrier}: {_money(auto_prem)}",
        f"Total recommended annual premium: {_money(total)}",
        "",
        "Highlights: competitive pricing vs expiring program; improved uninsured motorist limits on auto",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Broker:** {account.broker}  
**Type:** Client insurance proposal (synthetic demo)

## Recommendation
- **Total annual premium:** {_money(total)}
- **Bind deadline:** {bind.isoformat()}

## Suggested chatbot questions
1. What is the total recommended premium?
2. When is the bind deadline?
3. How many commercial auto units are included?
"""
    return title, lines, summary


def _coi(account: Account, variant: int) -> tuple[str, list[str], str]:
    holder = LANDLORDS[variant % len(LANDLORDS)]
    gl = _money(2_000_000 if variant % 2 else 1_000_000)
    wc = "Statutory limits"
    auto = _money(1_000_000)
    title = "Certificate of Liability Insurance"
    lines = [
        f"Certificate holder: {holder}",
        f"Additional insured: {holder} — per written contract",
        f"Named insured: {account.legal_name} dba {account.dba}",
        f"Location: {account.address}",
        f"General liability: {gl} each occurrence",
        f"Workers compensation: {wc}",
        f"Commercial auto: {auto} combined single limit",
        f"Policy effective: {account.effective.strftime('%B %d, %Y')}",
        f"Policy expiration: {account.renewal.strftime('%B %d, %Y')}",
        f"Broker contact: {account.producer_name}, {account.broker}",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Certificate holder:** {holder}  
**Type:** Certificate of insurance (synthetic demo)

## Suggested chatbot questions
1. Who is the certificate holder?
2. What GL limit appears on the certificate?
3. Is the landlord listed as additional insured?
"""
    return title, lines, summary


def _gap_memo(account: Account, variant: int) -> tuple[str, list[str], str]:
    landlord = LANDLORDS[(variant + 1) % len(LANDLORDS)]
    bpp = 600_000 + variant * 25_000
    ti_val = bpp + 180_000 + (variant % 5) * 20_000
    title = "Coverage Gap Analysis Memorandum"
    lines = [
        f"To: {account.legal_name}",
        f"From: {account.broker} — Commercial P&C",
        f"Re: Lease compliance review — landlord {landlord}",
        f"Location: {account.address}",
        "",
        "Lease requirements: GL USD 2M/4M — met | WC statutory + EL USD 1M — met",
        f"BPP limit {_money(bpp)} vs tenant improvement valuation {_money(ti_val)} — gap identified",
        "Flood coverage: not in current program — recommended for broker review",
        "Commercial auto USD 1M CSL — met where vehicles operate on premises",
        "",
        f"Recommendation: increase BPP to {_money(ti_val + 50_000)}; obtain flood indication",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Landlord:** {landlord}  
**Broker:** {account.broker}  
**Type:** Coverage gap analysis memo (synthetic demo)

## Identified gaps
1. BPP limit {_money(bpp)} vs TI valuation {_money(ti_val)}
2. Flood not included

## Suggested chatbot questions
1. What coverage gaps were identified?
2. What is the tenant improvement valuation vs BPP limit?
"""
    return title, lines, summary


def _loss_run(account: Account, variant: int) -> tuple[str, list[str], str]:
    carrier = CARRIERS[(variant + 5) % len(CARRIERS)]
    claims = 4 + (variant % 6)
    incurred = 80_000 + variant * 3_500
    premium = 420_000 + variant * 12_000
    ratio = round(incurred / premium * 100, 1)
    mod_start = round(1.02 + (variant % 5) * 0.01, 2)
    mod_end = round(mod_start - 0.08 - (variant % 3) * 0.02, 2)
    title = "Five-Year Loss Run Summary"
    lines = [
        f"Named insured: {account.legal_name}",
        f"Carrier: {carrier}",
        f"Report as of: January 31, {account.effective.year}",
        f"Policy years reviewed: five years ending {account.effective.year - 1}",
        f"Total claim count: {claims}",
        f"Total incurred losses: {_money(incurred)}",
        f"Total earned premium: {_money(premium)}",
        f"Five-year loss ratio: {ratio}%",
        f"Experience mod trend: {mod_start} improved to {mod_end}",
        "",
        "Largest closed claim: workers compensation — warehouse lifting injury",
        "Recent property claim: roof hail damage — closed",
    ]
    summary = f"""# Summary: {{filename}}

**Client:** {account.legal_name}  
**Carrier:** {carrier}  
**Type:** Five-year loss run summary (synthetic demo)

## Summary stats
- **Total claims:** {claims}
- **5-year incurred losses:** {_money(incurred)}
- **Loss ratio:** {ratio}%
- **Experience mod:** {mod_start} → {mod_end}

## Suggested chatbot questions
1. What is the 5-year loss ratio?
2. How has the experience mod changed?
3. What was the largest claim type mentioned?
"""
    return title, lines, summary


GENERATORS = [
    ("gl-property-policy", _gl_policy),
    ("workers-comp-policy", _wc_policy),
    ("quote-comparison", _quote_comparison),
    ("broker-proposal", _broker_proposal),
    ("certificate-of-insurance", _coi),
    ("coverage-gap-memo", _gap_memo),
    ("loss-run-summary", _loss_run),
]


def generate(count: int, start_number: int = 8) -> list[str]:
    created: list[str] = []
    base_index = start_number - 8
    for i in range(count):
        doc_num = start_number + i
        variant_index = base_index + i
        slug, generator = GENERATORS[variant_index % len(GENERATORS)]
        account = _account(variant_index)
        filename = f"{doc_num:02d}-{account.prefix.lower()}-{slug}.pdf"
        title, lines, summary_template = generator(account, variant_index)
        pdf_path = OUTPUT_DIR / filename
        summary_path = OUTPUT_DIR / filename.replace(".pdf", ".SUMMARY.md")
        _write_pdf(pdf_path, title, lines)
        _write_summary(summary_path, summary_template.replace("{filename}", filename))
        created.append(filename)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic demo insurance PDFs.")
    parser.add_argument("--count", type=int, default=50, help="Number of documents to generate")
    parser.add_argument("--start", type=int, default=8, help="Starting file number (default 8)")
    args = parser.parse_args()
    created = generate(args.count, start_number=args.start)
    print(f"Generated {len(created)} documents in {OUTPUT_DIR}")
    for name in created[:5]:
        print(f"  {name}")
    if len(created) > 5:
        print(f"  ... and {len(created) - 5} more")


if __name__ == "__main__":
    main()
