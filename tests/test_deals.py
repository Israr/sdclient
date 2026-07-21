import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import deals

scrape_deals = deals.scrape_deals
scrape_hot_deals = deals.scrape_hot_deals
select_most_commented = deals.select_most_commented


def deal_card(title, comments=None, *, hot=False, link="/deal"):
    fire_icon = '<span class="dealCard__fireIcon"></span>' if hot else ""
    comments_count = (
        f'<span class="dealCardSocialControls__commentsCount">{comments}</span>'
        if comments is not None
        else ""
    )
    return f"""
        <div class="dealCard">
            <div class="dealCard__content">
                {fire_icon}
                <a href="{link}"><span class="dealCard__title">{title}</span></a>
                <span class="dealCard__price">$10</span>
                <span class="dealCard__originalPrice">$20</span>
            </div>
            <footer class="dealCard__footer">{comments_count}</footer>
        </div>
    """


class DealParsingTests(unittest.TestCase):
    def setUp(self):
        self.html = "".join(
            [
                deal_card("Twelve", "12", hot=True, link="/f/123"),
                deal_card("Boundary", "5"),
                deal_card("Eight", "8"),
                deal_card("Missing"),
                deal_card("Malformed", "many"),
            ]
        )

    def test_scrape_deals_parses_all_homepage_cards(self):
        deals = scrape_deals(self.html)

        self.assertEqual(
            [deal["title"] for deal in deals],
            ["Twelve", "Boundary", "Eight", "Missing", "Malformed"],
        )
        self.assertEqual(
            [deal["comments"] for deal in deals],
            [12, 5, 8, 0, 0],
        )
        self.assertTrue(deals[0]["is_hot"])
        self.assertFalse(deals[1]["is_hot"])
        self.assertEqual(deals[0]["link"], "https://slickdeals.net/f/123")

    def test_select_most_commented_excludes_boundary_and_sorts_descending(self):
        selected = select_most_commented(scrape_deals(self.html))

        self.assertEqual(
            [(deal["title"], deal["comments"]) for deal in selected],
            [("Twelve", 12), ("Eight", 8)],
        )

    def test_scrape_hot_deals_preserves_hot_only_behavior(self):
        hot_deals = scrape_hot_deals(self.html)

        self.assertEqual([deal["title"] for deal in hot_deals], ["Twelve"])

    def test_query_filters_titles_case_insensitively(self):
        all_deals = scrape_deals(self.html)

        self.assertEqual(deals.filter_by_query(all_deals, ""), all_deals)
        self.assertEqual(
            [deal["title"] for deal in deals.filter_by_query(all_deals, "tWeLvE")],
            ["Twelve"],
        )
        self.assertEqual(
            [deal["title"] for deal in deals.filter_by_query(
                scrape_hot_deals(self.html), "twelve"
            )],
            ["Twelve"],
        )
        self.assertEqual(
            [deal["title"] for deal in deals.filter_by_query(
                select_most_commented(all_deals), "eight"
            )],
            ["Eight"],
        )


class CliTests(unittest.TestCase):
    def test_most_commented_is_separate_from_all_hot_mode(self):
        parser = deals.build_parser()

        self.assertTrue(parser.parse_args(["--most-commented"]).most_commented)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--most-commented", "--all-hot"])

    def test_comments_table_displays_comment_count(self):
        deal = {
            "title": "Popular",
            "price": "$10",
            "original_price": "$20",
            "link": "https://slickdeals.net/f/123",
            "comments": 12,
            "is_hot": False,
        }
        output = io.StringIO()

        with (
            patch.object(deals, "HAVE_TABULATE", False),
            redirect_stdout(output),
        ):
            deals.print_table([deal], include_comments=True)

        self.assertIn("Comments", output.getvalue())
        self.assertIn("12", output.getvalue())

    def test_query_argument_defaults_to_empty_string(self):
        parser = deals.build_parser()

        self.assertEqual(parser.parse_args([]).query, "")
        self.assertEqual(parser.parse_args(["--query", "laptop"]).query, "laptop")


if __name__ == "__main__":
    unittest.main()
