# Most-Commented Deals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate `--most-commented` CLI mode that displays all homepage deals with more than five comments in descending comment-count order.

**Architecture:** Parse every `.dealCard` into one deal dictionary containing presentation fields, comment count, and hot status. Keep existing hot-deal behavior through a compatibility filter, and add a pure selector for most-commented deals. Build CLI arguments separately from execution so mode conflicts are directly testable.

**Tech Stack:** Python 3.13, argparse, BeautifulSoup, unittest

## Global Constraints

- Include every homepage deal in most-commented mode, regardless of price or flame status.
- Include only comment counts strictly greater than five.
- Sort comment counts numerically in descending order.
- Treat absent or malformed counts as zero.
- Preserve existing behavior when `--most-commented` is absent.
- Do not add dependencies.

---

### Task 1: Parse Homepage Deals and Select Most-Commented Results

**Files:**
- Create: `tests/test_deals.py`
- Modify: `deals.py:78-117`

**Interfaces:**
- Produces: `scrape_deals(html: str) -> list[dict]`
- Produces: `scrape_hot_deals(html: str) -> list[dict]`
- Produces: `select_most_commented(deals: list[dict], minimum: int = 5) -> list[dict]`
- Each parsed dictionary contains `title`, `price`, `original_price`, `link`, `comments: int`, and `is_hot: bool`.

- [ ] **Step 1: Write failing parser and selection tests**

Create `tests/test_deals.py` with a static `.dealCard` fixture containing hot and non-hot cards with comment values `12`, `5`, `8`, missing, and malformed. Assert that `scrape_deals` returns all cards, normalizes relative links, parses valid counts, maps invalid counts to zero, and records hot status. Assert that `select_most_commented` returns titles for counts 12 and 8 in that order.

- [ ] **Step 2: Verify the tests fail for missing APIs**

Run: `.venv/bin/python -m unittest tests.test_deals -v`

Expected: FAIL because `scrape_deals` and `select_most_commented` cannot be imported.

- [ ] **Step 3: Implement generalized parsing and selection**

In `deals.py`, iterate over `soup.select(".dealCard")`. Read `.dealCard__title`, `.dealCard__price`, `.dealCard__originalPrice`, `a[href]`, and `.dealCardSocialControls__commentsCount`; parse comments with `int(re.sub(r"[^\d]", "", text))` only when digits exist, otherwise use zero. Set `is_hot` from `card.select_one(".dealCard__fireIcon") is not None`. Preserve title deduplication. Implement `scrape_hot_deals` as a filter over `scrape_deals`, and implement:

```python
def select_most_commented(deals, minimum=5):
    return sorted(
        (deal for deal in deals if deal["comments"] > minimum),
        key=lambda deal: deal["comments"],
        reverse=True,
    )
```

- [ ] **Step 4: Verify parser and selection tests pass**

Run: `.venv/bin/python -m unittest tests.test_deals -v`

Expected: all Task 1 tests PASS.

### Task 2: Add the CLI Mode and Comments Table Column

**Files:**
- Modify: `tests/test_deals.py`
- Modify: `deals.py:120-202`

**Interfaces:**
- Produces: `build_parser() -> argparse.ArgumentParser`
- Updates: `print_table(deals, headers=..., include_comments=False)`
- Consumes: `scrape_deals` and `select_most_commented` from Task 1.

- [ ] **Step 1: Write failing CLI and output tests**

Add tests asserting:

```python
parser = build_parser()
assert parser.parse_args(["--most-commented"]).most_commented is True
with self.assertRaises(SystemExit):
    parser.parse_args(["--most-commented", "--all-hot"])
```

Capture `print_table(..., include_comments=True)` output and assert it contains `Comments` and the numeric count.

- [ ] **Step 2: Verify the new tests fail**

Run: `.venv/bin/python -m unittest tests.test_deals -v`

Expected: FAIL because `build_parser` and `include_comments` do not exist.

- [ ] **Step 3: Implement CLI mode and table rendering**

Extract argument construction into `build_parser`. Put `--all-hot` and `--most-commented` in an argparse mutually exclusive group. Keep `--max-price` outside the group.

Update `print_table` so `include_comments=True` inserts a fixed-width Comments column before Link and adjusts the terminal-width calculation, row values, fallback column widths, and default headers.

In `main`, call `scrape_deals` once. For most-commented mode, call `select_most_commented`, set the heading to `Most-Commented Homepage Deals (> 5 comments)`, and render with `include_comments=True`. Otherwise retain the existing all-hot and cheap/free branches.

- [ ] **Step 4: Verify all automated tests pass**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests PASS without warnings or errors.

- [ ] **Step 5: Verify CLI help and live mode**

Run: `.venv/bin/python deals.py --help`

Expected: help lists `--most-commented` and shows it as mutually exclusive with `--all-hot`.

Run: `.venv/bin/python deals.py --most-commented`

Expected: a Comments column is displayed; every row has more than five comments and values descend numerically.
