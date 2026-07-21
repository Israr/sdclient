# Most-Commented Deals CLI Mode

## Goal

Add a CLI mode that displays all Slickdeals homepage deals with more than five comments, ordered from most to fewest comments.

## Command-Line Behavior

- Add a `--most-commented` flag.
- Treat this flag as a separate display mode from the existing hot-deal modes.
- Reject using `--most-commented` together with `--all-hot`.
- Do not apply the `--max-price` filter in most-commented mode. The option may retain its existing default without causing a conflict.
- Preserve all existing behavior when `--most-commented` is absent.

## Scraping and Selection

Generalize homepage parsing around each `.dealCard`. Extract the title, current price, original price, link, and integer comment count from each card. Hot-deal selection will continue to use the card's flame-icon marker.

In most-commented mode:

1. Consider every parsed homepage deal, regardless of flame status or price.
2. Keep only deals whose comment count is strictly greater than five.
3. Sort the selected deals by comment count in descending order.

Cards with an absent or malformed comment count are treated as having zero comments and therefore do not qualify.

## Output

Use the existing terminal table formatting. Most-commented mode adds a `Comments` column so the sort order is visible. Its heading reports the mode and number of matching results. If no deals qualify, retain the existing `No matching deals found.` message.

## Testing

Add automated tests using static HTML snippets rather than live network access. Cover:

- Parsing all homepage cards, including comment counts and hot status.
- Excluding deals with exactly five comments.
- Including deals with more than five comments.
- Descending numeric ordering, including multi-digit counts.
- Handling missing or malformed comment counts.
- CLI mode incompatibility between `--most-commented` and `--all-hot`.
- Preservation of existing hot-deal and price-filter behavior.
