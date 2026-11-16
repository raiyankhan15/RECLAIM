"""
core/tracking.py - Browser Tracking, Privacy-Preserving Domain Sanitization & Categorization
Guarantees strict privacy: strips query strings, auth tokens, and document bodies.
Only retains sanitized domains and high-level behavioral task categories.
"""

from urllib.parse import urlparse
from typing import Tuple

# Predefined domain category mappings
CATEGORY_RULES = {
    "Development & Coding": [
        "github.com", "gitlab.com", "stackoverflow.com", "stackexchange.com",
        "leetcode.com", "hackerrank.com", "localhost", "127.0.0.1", "replit.com",
        "codepen.io", "kaggle.com", "colab.research.google.com"
    ],
    "Documentation & Research": [
        "docs.python.org", "developer.mozilla.org", "arxiv.org", "wikipedia.org",
        "w3schools.com", "geeksforgeeks.org", "medium.com", "scikit-learn.org",
        "streamlit.io", "pytorch.org", "tensorflow.org", "fastapi.tiangolo.com"
    ],
    "Communication & Messaging": [
        "web.whatsapp.com", "slack.com", "discord.com", "mail.google.com",
        "outlook.office.com", "teams.microsoft.com", "telegram.org", "web.telegram.org"
    ],
    "Social Media & Entertainment": [
        "instagram.com", "twitter.com", "x.com", "youtube.com", "reddit.com",
        "netflix.com", "twitch.tv", "tiktok.com", "facebook.com", "linkedin.com"
    ],
    "General Productivity": [
        "docs.google.com", "drive.google.com", "notion.so", "figma.com",
        "trello.com", "linear.app", "atlassian.net", "jira.atlassian.com", "canva.com"
    ]
}

def sanitize_url(raw_url: str) -> Tuple[str, str]:
    """
    Strips query parameters, anchors, auth tokens, and private paths.
    Returns (sanitized_domain, high_level_category).
    """
    if not raw_url:
        return "blank", "Other / Unclassified"

    try:
        parsed = urlparse(raw_url)
        netloc = parsed.netloc.lower()

        # Handle chrome://, about:, file:// or port-based URLs
        if not netloc:
            if raw_url.startswith("chrome://"):
                return "chrome://internal", "Browser Internal"
            if raw_url.startswith("file://"):
                return "local_file", "Local Workspace"
            return "unknown", "Other / Unclassified"

        # Remove default www.
        if netloc.startswith("www."):
            clean_domain = netloc[4:]
        else:
            clean_domain = netloc

        # Classify domain
        for category, domain_list in CATEGORY_RULES.items():
            for d in domain_list:
                if clean_domain == d or clean_domain.endswith("." + d):
                    return clean_domain, category

        return clean_domain, "Other / General Browsing"

    except Exception:
        return "unparseable_url", "Other / Unclassified"

