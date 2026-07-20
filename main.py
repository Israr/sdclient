#!/usr/bin/env python3
"""
slickdeals_hot_deals.py

Scrapes the Slickdeals.net frontpage for "Hot Deals" (deals marked with the
flame/fire icon) and prints out the free & cheap ones in a formatted table.

Requirements:
    uv sync

Usage:
    uv run main.py                # default: show deals <= $15 or Free
    uv run main.py --max-price 25 # custom price threshold
    uv run main.py --all-hot      # show ALL hot deals (no price filter)
"""

import argparse
import re
import shutil
import sys
import textwrap

import requests
from bs4 import BeautifulSoup

try:
    from tabulate import tabulate
    HAVE_TABULATE = True
except ImportError:
    HAVE_TABULATE = False

URL = "https://slickdeals.net/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    """Download the raw HTML of the page."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_price(price_str: str):
    """
    Try to pull a numeric value out of a price string like:
    '$40', 'from $18', '2 for $9.15', 'Free', '75% Off', etc.
    Returns float or None if not parseable / not a plain price.
    """
    if not price_str:
        return None
    price_str = price_str.strip()
    if price_str.lower() == "free":
        return 0.0
    match = re.search(r"\$([\d,]+\.?\d*)", price_str)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def is_cheap_or_free(price_str: str, max_price: float) -> bool:
    """Decide whether a deal counts as 'free or cheap'."""
    if not price_str:
        return False
    if "free" in price_str.lower():
        return True
    value = parse_price(price_str)
    if value is None:
        return False
    return value <= max_price


def scrape_hot_deals(html: str):
    """
    Parse the page and return a list of dicts for every deal card
    that has the fire/flame icon (dealCard__fireIcon).
    """
    soup = BeautifulSoup(html, "html.parser")
    deals = []
    seen_titles = set()

    fire_icons = soup.select(".dealCard__fireIcon")
    for icon in fire_icons:
        # Fire icon lives inside dealCard__priceContainer -> dealCard__content
        card = icon.find_parent(class_="dealCard__content")
        if not card:
            continue

        title_el = card.select_one(".dealCard__title")
        price_el = card.select_one(".dealCard__price")
        orig_price_el = card.select_one(".dealCard__originalPrice")
        link_el = card.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else "N/A"
        price = price_el.get_text(strip=True) if price_el else ""
        orig_price = orig_price_el.get_text(strip=True) if orig_price_el else ""
        link = link_el["href"] if link_el else ""
        if link and link.startswith("/"):
            link = "https://slickdeals.net" + link

        if title in seen_titles:
            continue
        seen_titles.add(title)

        deals.append({
            "title": title,
            "price": price,
            "original_price": orig_price,
            "link": link,
        })

    return deals


def print_table(deals, headers=("Title", "Price", "Original Price", "Link")):
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns

    # Fixed-width columns, everything else goes to Title/Link.
    price_w, orig_w = 8, 14
    borders = 3 * 3 + 4  # " | " between 4 cols, plus outer padding
    remaining = max(term_width - price_w - orig_w - borders, 30)
    link_w = min(40, remaining // 3)
    title_w = max(remaining - link_w, 20)

    def wrap(text, width):
        return "\n".join(textwrap.wrap(str(text), width=width)) or ""

    rows = [
        [
            wrap(d["title"], title_w),
            wrap(d["price"] or "-", price_w),
            wrap(d["original_price"] or "-", orig_w),
            wrap(d["link"], link_w),
        ]
        for d in deals
    ]

    if HAVE_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        col_widths = [title_w, price_w, orig_w, link_w]

        def fmt_row(row):
            cell_lines = [str(cell).split("\n") for cell in row]
            height = max(len(lines) for lines in cell_lines)
            out_lines = []
            for i in range(height):
                cells = [
                    (lines[i] if i < len(lines) else "").ljust(col_widths[j])
                    for j, lines in enumerate(cell_lines)
                ]
                out_lines.append(" | ".join(cells))
            return "\n".join(out_lines)

        print(fmt_row(list(headers)))
        print("-+-".join("-" * w for w in col_widths))
        for row in rows:
            print(fmt_row(row))
            print("-+-".join("-" * w for w in col_widths))


def main():
    parser = argparse.ArgumentParser(description="Fetch Slickdeals hot deals.")
    parser.add_argument(
        "--max-price", type=float, default=15.0,
        help="Max price (in $) to count as 'cheap'. Default: 15",
    )
    parser.add_argument(
        "--all-hot", action="store_true",
        help="Show ALL hot deals (skip free/cheap filtering).",
    )
    args = parser.parse_args()

    print(f"Fetching {URL} ...", file=sys.stderr)
    html = fetch_html(URL)

    all_hot_deals = scrape_hot_deals(html)
    print(f"Found {len(all_hot_deals)} hot deals total.\n", file=sys.stderr)

    if args.all_hot:
        selected = all_hot_deals
        title = "ALL Hot Deals (flame icon)"
    else:
        selected = [d for d in all_hot_deals if is_cheap_or_free(d["price"], args.max_price)]
        title = f"Free & Cheap Hot Deals (<= ${args.max_price:.2f} or Free)"

    print(f"=== {title} ({len(selected)} results) ===\n")
    if selected:
        print_table(selected)
    else:
        print("No matching deals found.")


if __name__ == "__main__":
    main()
