#!/usr/bin/env python3
"""
Import verified fixes from fixes.json into the database.

This script imports only manually verified fixes with improved responses
and keywords for better AI matching.
"""

import json
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Document, Keyword
from database.session import SessionLocal
from sqlalchemy.orm import Session


# Verified fixes with improved responses
VERIFIED_FIXES = [
    {
        "id": "verified-001",
        "original_id": "416f35f3-0f49-48c8-b178-371638c78010",
        "title": "Macro fails when monitor turns off",
        "content_short": "Use dummy plug to emulate monitor when display is off",
        "content_full": """**Problem:** Macro stops working when monitor is turned off because Windows loses the 1920x1080 resolution.

**Solution:**
1. Use a "dummy plug" or "headless HDMI adapter" to emulate a monitor (costs $5-10 on Amazon)
2. Alternative: Configure Windows to keep display active when monitor is off
3. Check Roblox settings for background operation permissions

**Why this works:** The macro relies on screen capture at specific resolution. When monitor turns off, Windows changes resolution/display state, breaking image recognition.

**Prevention:** Keep dummy plug permanently installed, or adjust Windows power settings to never turn off display.""",
        "keywords": [
            "monitor",
            "display",
            "dummy",
            "hdmi",
            "resolution",
            "turn off",
            "screen off",
            "black screen",
            "rdp",
            "remote",
            "closes",
            "stops",
        ],
        "tags": ["monitor", "resolution", "dummy-plug", "verified"],
        "category": "display_issues",
    },
    {
        "id": "verified-002",
        "original_id": "514232d4-4d04-41ce-9a02-773376607513",
        "title": "Game Load Timeout error when game already loaded",
        "content_short": "Change Windows display scale to 100%",
        "content_full": """**Problem:** Macro shows "Game Load Timeout Exceeded" error even though Roblox is already fully loaded.

**Root Cause:** Windows display scaling is not set to 100%. The macro uses image recognition that fails when Windows scales the display (125%, 150%, etc.).

**Solution:**
1. Right-click on desktop → Display settings
2. Under "Scale and layout", change to 100%
3. Restart Roblox and macro
4. Verify macro capture settings match your resolution

**Note:** This is the #1 cause of timeout errors. Always ensure 100% scaling before troubleshooting other issues.

**Additional check:** If using multiple monitors, ensure they all use 100% scaling.""",
        "keywords": [
            "timeout",
            "load time",
            "game load",
            "exceeded",
            "100%",
            "display scale",
            "scaling",
            "already loaded",
            "loaded",
        ],
        "tags": ["timeout", "display-scale", "100-percent", "verified"],
        "category": "timeout_errors",
    },
    {
        "id": "verified-003",
        "original_id": "5f65d83d-0aa7-433d-99ac-7d89903ef285",
        "title": "Macro not updating field selection",
        "content_short": "Close and reopen macro to fix field selection bug",
        "content_full": """**Problem:** Macro continues going to the previous/old field even after you changed the field selection in settings.

**Known Bug:** This is a field selection caching issue in the macro.

**Solution:**
1. Close the macro completely (not minimize, actually close)
2. Reopen the macro
3. The field selection will now work correctly

**Workaround:** If you need to change fields frequently, consider using different macro profiles for each field.

**Developer Note:** This bug occurs because the macro caches the field coordinates on startup. A fix is planned for a future update.""",
        "keywords": [
            "field",
            "selection",
            "doesn't change",
            "wrong field",
            "previous field",
            "old field",
            "not updating",
            "cache",
            "stuck",
        ],
        "tags": ["field-selection", "cache-bug", "restart-fix", "verified"],
        "category": "field_issues",
    },
    {
        "id": "verified-004",
        "original_id": "5ff477e7-6a4a-4d13-84cd-def676eb186f",
        "title": "Coconut dispenser feature locked",
        "content_short": "Must defeat Coconut Crab before enabling dispenser feature",
        "content_full": """**Problem:** Cannot enable the coconut dispenser feature in macro settings.

**Prerequisite:** You must defeat the Coconut Crab boss at least once in-game before this feature becomes available.

**Solution:**
1. Go to Coconut Field in-game
2. Defeat the Coconut Crab boss (appears every 2 hours)
3. After defeating it once, the macro feature will unlock

**Note:** This is a game progression requirement, not a macro bug. The macro checks if you've unlocked the dispenser in-game before allowing the feature.

**Help:** If you need help defeating the crab, check Bee Swarm Simulator guides or ask in general chat.""",
        "keywords": [
            "coconut",
            "dispenser",
            "crab",
            "locked",
            "can't enable",
            "prerequisite",
            "defeat",
            "boss",
            "unlocked",
        ],
        "tags": ["coconut-crab", "prerequisite", "progression", "verified"],
        "category": "progression_requirements",
    },
    {
        "id": "verified-005",
        "original_id": "29450df5-d313-4363-bc80-efeb72cc393d",
        "title": "Game Load Timeout (Alternative Fix)",
        "content_short": "Settings → System → Display → Scale = 100%",
        "content_full": """**Problem:** Error: "Game Load Timeout Exceeded"

**Confirmed Fix:**
1. Open Windows Settings
2. Go to System → Display
3. Under "Scale and layout", set to 100%
4. Apply and restart Roblox

**This is the same fix as timeout-002 but with different search keywords.**

**Additional Checks:**
- Ensure Roblox is in windowed or fullscreen mode (not minimized)
- Check that Windows UI scaling is also at 100%
- Verify your monitor's native resolution matches the macro settings""",
        "keywords": ["error", "game load", "timeout", "scale", "settings", "system", "display"],
        "tags": ["timeout", "display-scale", "settings-path", "verified"],
        "category": "timeout_errors",
    },
]


def create_document(db: Session, fix: Dict[str, Any]) -> Document:
    """Create a document entry from a verified fix."""
    doc = Document(
        id=fix["id"],
        title=fix["title"],
        content=fix["content_full"],
        summary=fix["content_short"],
        source="verified_fixes",
        doc_type="fix",
        metadata={
            "original_id": fix["original_id"],
            "tags": fix["tags"],
            "category": fix["category"],
            "verified": True,
            "imported_at": datetime.utcnow().isoformat(),
        },
    )

    # Add keywords
    for keyword_text in fix["keywords"]:
        keyword = db.query(Keyword).filter(Keyword.keyword == keyword_text).first()
        if not keyword:
            keyword = Keyword(keyword=keyword_text)
            db.add(keyword)
        doc.keywords.append(keyword)

    return doc


def import_verified_fixes():
    """Import all verified fixes into the database."""
    logger.info("Importing verified fixes into database...")

    db = SessionLocal()
    try:
        imported_count = 0

        for fix in VERIFIED_FIXES:
            # Check if already exists
            existing = db.query(Document).filter(Document.id == fix["id"]).first()
            if existing:
                logger.warning(f"  ⚠️  Skipping {fix['id']} - already exists")
                continue

            # Create document
            doc = create_document(db, fix)
            db.add(doc)
            imported_count += 1
            logger.info(f"  ✓ Imported: {fix['title']}")
            logger.debug(f"    Keywords: {', '.join(fix['keywords'][:5])}...")

        db.commit()
        logger.info(f"\n✅ Successfully imported {imported_count} verified fixes")
        logger.info(f"   Total keywords added: {db.query(Keyword).count()}")

    except Exception as e:
        db.rollback()
        logger.exception(f"\n❌ Error importing fixes: {e}")
        raise
    finally:
        db.close()


def generate_keyword_summary():
    """Generate a summary of all keywords for reference."""
    db = SessionLocal()
    try:
        logger.info("\n" + "=" * 60)
        logger.info("KEYWORD SUMMARY FOR VERIFIED FIXES")
        logger.info("=" * 60)

        for fix in VERIFIED_FIXES:
            logger.info(f"\n{fix['title']}")
            logger.info(f"  Category: {fix['category']}")
            logger.info(f"  Keywords: {', '.join(fix['keywords'])}")
            logger.info(f"  Tags: {', '.join(fix['tags'])}")

        logger.info("\n" + "=" * 60)
        logger.info("AI MATCHING NOTES:")
        logger.info("=" * 60)
        logger.info("- Use content_short for quick AI responses")
        logger.info("- Use content_full when user needs detailed explanation")
        logger.info("- Keywords trigger automatic fix suggestions")
        logger.info("- Tags help categorize and filter fixes")
        logger.info("- All fixes marked as 'verified' = confirmed working solutions")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        generate_keyword_summary()
    else:
        import_verified_fixes()
        logger.info("\nRun with --summary to see keyword reference")
