#!/usr/bin/env python3
"""
slickdeals_hot_deals.py

Scrapes the Slickdeals.net frontpage for "Hot Deals" (deals marked with the
flame/fire icon) and prints out the free & cheap ones in a formatted table.

Requirements:
    uv sync

Usage:
    uv run deals.py                  # default: show deals <= $15 or Free
    uv run deals.py --max-price 25   # custom price threshold
    uv run deals.py --all-hot        # show ALL hot deals (no price filter)
    uv run deals.py --most-commented # show homepage deals with > 5 comments
    uv run deals.py --query laptop   # filter deals by title
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


def scrape_deals(html: str):
    """Parse every deal card on the homepage."""
    soup = BeautifulSoup(html, "html.parser")
    deals = []
    seen_titles = set()

    for card in soup.select(".dealCard"):
        title_el = card.select_one(".dealCard__title")
        price_el = card.select_one(".dealCard__price")
        orig_price_el = card.select_one(".dealCard__originalPrice")
        comments_el = card.select_one(".dealCardSocialControls__commentsCount")
        link_el = card.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else "N/A"
        price = price_el.get_text(strip=True) if price_el else ""
        orig_price = orig_price_el.get_text(strip=True) if orig_price_el else ""
        comments_text = comments_el.get_text(strip=True) if comments_el else ""
        comments_digits = re.sub(r"[^\d]", "", comments_text)
        comments = int(comments_digits) if comments_digits else 0
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
            "comments": comments,
            "is_hot": card.select_one(".dealCard__fireIcon") is not None,
        })

    return deals


def scrape_hot_deals(html: str):
    """Parse the page and return deals that have the fire/flame icon."""
    return [deal for deal in scrape_deals(html) if deal["is_hot"]]


def select_most_commented(deals, minimum=5):
    """Return deals above the comment threshold, most commented first."""
    return sorted(
        (deal for deal in deals if deal["comments"] > minimum),
        key=lambda deal: deal["comments"],
        reverse=True,
    )


def filter_by_query(deals, query):
    """Return deals whose title contains query, ignoring case."""
    normalized_query = query.casefold()
    if not normalized_query:
        return deals
    return [
        deal for deal in deals
        if normalized_query in deal["title"].casefold()
    ]


def print_table(deals, headers=None, include_comments=False):
    if headers is None:
        headers = (
            ("Title", "Price", "Original Price", "Comments", "Link")
            if include_comments
            else ("Title", "Price", "Original Price", "Link")
        )

    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns

    # Fixed-width columns; split remaining space between Title and Link.
    price_w, orig_w, comments_w = 8, 14, 8
    title_max = 35
    link_min = 30
    column_count = 5 if include_comments else 4
    borders = 3 * (column_count - 1) + column_count
    fixed_width = price_w + orig_w + (comments_w if include_comments else 0)
    remaining = max(term_width - fixed_width - borders, 30)
    link_w = max(link_min, remaining - title_max)
    title_w = remaining - link_w

    def wrap(text, width):
        return "\n".join(textwrap.wrap(str(text), width=width)) or ""

    rows = []
    for deal in deals:
        row = [
            wrap(deal["title"], title_w),
            wrap(deal["price"] or "-", price_w),
            wrap(deal["original_price"] or "-", orig_w),
        ]
        if include_comments:
            row.append(wrap(deal["comments"], comments_w))
        row.append(wrap(deal["link"], link_w))
        rows.append(row)

    if HAVE_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        col_widths = [title_w, price_w, orig_w]
        if include_comments:
            col_widths.append(comments_w)
        col_widths.append(link_w)

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


def build_parser():
    parser = argparse.ArgumentParser(description="Fetch Slickdeals hot deals.")
    parser.add_argument(
        "--max-price", type=float, default=15.0,
        help="Max price (in $) to count as 'cheap'. Default: 15",
    )
    parser.add_argument(
        "--query", default="",
        help="Only show deals whose title contains this text (case-insensitive).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--all-hot", action="store_true",
        help="Show ALL hot deals (skip free/cheap filtering).",
    )
    mode.add_argument(
        "--most-commented", action="store_true",
        help="Show homepage deals with more than 5 comments.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    print(f"Fetching {URL} ...", file=sys.stderr)
    html = fetch_html(URL)

    all_deals = scrape_deals(html)
    if args.most_commented:
        selected = select_most_commented(all_deals)
        title = "Most-Commented Homepage Deals (> 5 comments)"
        print(f"Found {len(all_deals)} homepage deals total.\n", file=sys.stderr)
    else:
        all_hot_deals = [deal for deal in all_deals if deal["is_hot"]]
        print(f"Found {len(all_hot_deals)} hot deals total.\n", file=sys.stderr)

    if args.all_hot:
        selected = all_hot_deals
        title = "ALL Hot Deals (flame icon)"
    elif not args.most_commented:
        selected = [d for d in all_hot_deals if is_cheap_or_free(d["price"], args.max_price)]
        title = f"Free & Cheap Hot Deals (<= ${args.max_price:.2f} or Free)"

    selected = filter_by_query(selected, args.query)

    print(f"=== {title} ({len(selected)} results) ===\n")
    if selected:
        print_table(selected, include_comments=args.most_commented)
    else:
        print("No matching deals found.")


if __name__ == "__main__":
    main()
