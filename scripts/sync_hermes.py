#!/usr/bin/env python3
"""Sync unified astro-gatekeeper skill, domain card references, and SOUL.md to Hermes Agent.

This script:
1. Creates local references/ symlinks in astrology_kb/astro-gatekeeper/ for portable skill navigation.
2. Updates SKILL.md links to use the references/ standard (supported by Hermes & Antigravity).
3. Deploys the self-contained astro-gatekeeper skill package to ~/.hermes/skills/astrology/ and
   active Hermes profiles, pruning legacy split skills (astrology-writer, astrology-report-gatekeeper).
4. Synchronizes ~/.hermes/profiles/astro-gatekeeper/SOUL.md with the unified astro-gatekeeper rules.
5. Validates the installation using Hermes Agent's skill_view runtime.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = REPO_ROOT / "astrology_kb"
UNIFIED_SKILL_NAME = "astro-gatekeeper"
UNIFIED_SKILL_DIR = KB_ROOT / UNIFIED_SKILL_NAME
LEGACY_SKILL_NAMES = ("astrology-writer", "astrology-report-gatekeeper")

HERMES_ROOT = Path.home() / ".hermes"
HERMES_GLOBAL_SKILLS = HERMES_ROOT / "skills" / "astrology"
HERMES_PROFILES_DIR = HERMES_ROOT / "profiles"
HERMES_ASTRO_PROFILE = HERMES_PROFILES_DIR / "astro-gatekeeper"

EXCLUDE_FILENAMES = {
    "SKILL.md", "README.md", "index.md", "INDEX.md",
    "astro_gatekeeper.md", "astrology_writer.md", "astrology_report_gatekeeper.md",
    "example-report.md", "example-output.md",
}


def find_domain_cards() -> dict[str, Path]:
    """Find all domain markdown cards in astrology_kb mapped by filename."""
    cards: dict[str, Path] = {}
    for path in KB_ROOT.rglob("*.md"):
        if path.name in EXCLUDE_FILENAMES:
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if "references" in path.parts:
            continue
        cards[path.name] = path
    return cards


def setup_local_references_symlinks(skill_dir: Path, cards: dict[str, Path]) -> None:
    """Populate skill_dir/references/ with relative symlinks to domain cards."""
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for name, target in cards.items():
        symlink_path = ref_dir / name
        rel_target = os.path.relpath(target, ref_dir)
        if symlink_path.is_symlink() or symlink_path.exists():
            symlink_path.unlink()
        symlink_path.symlink_to(rel_target)
    print(f"  ✓ Created {len(cards)} relative symlinks in {ref_dir.relative_to(REPO_ROOT)}")


def rewrite_markdown_links(content: str, cards: dict[str, Path]) -> str:
    """Rewrite links like [Title](../category/filename.md) to [Title](references/filename.md)."""
    def _replace_link(match: re.Match) -> str:
        text = match.group(1)
        target = match.group(2)
        target_name = Path(target).name
        if target_name in cards:
            return f"[{text}](references/{target_name})"
        return match.group(0)

    return re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', _replace_link, content)


def update_master_skill(cards: dict[str, Path]) -> None:
    """Update SKILL.md in astrology_kb/astro-gatekeeper with references/ links and local symlinks."""
    setup_local_references_symlinks(UNIFIED_SKILL_DIR, cards)
    skill_file = UNIFIED_SKILL_DIR / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    updated = rewrite_markdown_links(content, cards)
    if updated != content:
        skill_file.write_text(updated, encoding="utf-8")
        print(f"  ✓ Updated links in {skill_file.relative_to(REPO_ROOT)}")
    else:
        print(f"  ✓ Links already up to date in {skill_file.relative_to(REPO_ROOT)}")


def build_soul_md(skill_content: str) -> str:
    """Derive the Hermes SOUL.md system prompt directly from the unified SKILL.md."""
    # Strip YAML frontmatter
    body = re.sub(r"^---\n.*?\n---\n+", "", skill_content, count=1, flags=re.DOTALL)
    # Replace the generic H1 intro + When to Use with the Hermes SOUL persona header
    header_replacement = (
        "# Astro Gatekeeper (Master Astrologer & Verification Engine)\n\n"
        "You are **Astro Gatekeeper** (profile `astro-gatekeeper`), a specialized astrology "
        "consultation writer, 4-pillar Q&A analyst, and quality-control auditor. All core "
        "decoding rules, 4-pillar synthesis protocols, and verification rubrics (`astro-gatekeeper` v2.0.0) "
        "are embedded directly in your system prompt below—you do **not** need the user to name a skill, "
        "and you do **not** need to call `skill_view` to load `SKILL.md` before writing or auditing a "
        "report or answering follow-up questions."
    )
    body = re.sub(
        r"^# Astro Gatekeeper.*?(?=\n---\n)",
        header_replacement,
        body,
        count=1,
        flags=re.DOTALL,
    )
    return body


def deploy_to_hermes(cards: dict[str, Path]) -> None:
    """Deploy self-contained astro-gatekeeper package to Hermes global skills and profile skills."""
    target_skill_roots = [HERMES_GLOBAL_SKILLS]

    if HERMES_PROFILES_DIR.exists():
        for prof in HERMES_PROFILES_DIR.iterdir():
            if prof.is_dir():
                prof_skills = prof / "skills" / "astrology"
                if prof_skills.exists():
                    target_skill_roots.append(prof_skills)

    src_skill_md = UNIFIED_SKILL_DIR / "SKILL.md"
    raw_content = src_skill_md.read_text(encoding="utf-8")
    rewritten_content = rewrite_markdown_links(raw_content, cards)

    for base_dir in target_skill_roots:
        if not base_dir.parent.exists():
            continue
        print(f"\nDeploying to: {base_dir}")

        # Remove legacy split skills if present
        for legacy_name in LEGACY_SKILL_NAMES:
            legacy_dir = base_dir / legacy_name
            if legacy_dir.exists():
                shutil.rmtree(legacy_dir)
                print(f"  ✓ Removed legacy split skill: {legacy_dir}")

        dest_skill_dir = base_dir / UNIFIED_SKILL_NAME
        dest_skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        dest_skill_md = dest_skill_dir / "SKILL.md"
        dest_skill_md.write_text(rewritten_content, encoding="utf-8")

        # Copy physical files into references/ (required for Hermes validate_within_dir)
        dest_ref_dir = dest_skill_dir / "references"
        if dest_ref_dir.exists():
            shutil.rmtree(dest_ref_dir)
        dest_ref_dir.mkdir(parents=True, exist_ok=True)

        for card_name, card_src in cards.items():
            shutil.copy2(card_src, dest_ref_dir / card_name)

        print(f"  ✓ {UNIFIED_SKILL_NAME}: SKILL.md + {len(cards)} reference files deployed")

    # Sync SOUL.md and profile.yaml in ~/.hermes/profiles/astro-gatekeeper if profile exists
    if HERMES_ASTRO_PROFILE.exists():
        soul_path = HERMES_ASTRO_PROFILE / "SOUL.md"
        soul_content = build_soul_md(rewritten_content)
        soul_path.write_text(soul_content, encoding="utf-8")
        print(f"  ✓ Synchronized {soul_path} with unified {UNIFIED_SKILL_NAME} v2.0.0")

        profile_yaml = HERMES_ASTRO_PROFILE / "profile.yaml"
        if profile_yaml.exists():
            prof_text = profile_yaml.read_text(encoding="utf-8")
            updated_prof = prof_text.replace(
                "use the astrology-writer and astrology-report-gatekeeper skills to write and verify astrology reports.",
                "use the unified astro-gatekeeper skill to write, analyze, and verify astrology reports.",
            )
            if updated_prof != prof_text:
                profile_yaml.write_text(updated_prof, encoding="utf-8")
                print(f"  ✓ Updated description in {profile_yaml}")


def verify_hermes_skills() -> None:
    """Verify that Hermes Agent's skill_view can load astro-gatekeeper and its linked files."""
    hermes_python = Path.home() / ".hermes" / "tools" / "python-3.14.7+20260901-darwin-arm64" / "bin" / "python3"
    if not hermes_python.exists():
        print("\nNote: Hermes standalone python binary not found, skipping runtime check.")
        return

    check_code = """
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
import hermes_bootstrap
from tools.skills_tool import skill_view

res_skill = json.loads(skill_view('astro-gatekeeper'))
assert res_skill.get('success'), f'Failed loading astro-gatekeeper: {res_skill}'
linked = res_skill.get('linked_files', {}).get('references', [])
print(f'Hermes runtime check: astro-gatekeeper loaded successfully with {len(linked)} linked reference files.')

# Test viewing one reference card
res_file = json.loads(skill_view('astro-gatekeeper', file_path='references/the_12_bhavas.md'))
assert res_file.get('success'), f'Failed reading reference card: {res_file}'
print(f'Hermes runtime check: references/the_12_bhavas.md read successfully ({len(res_file.get("content", ""))} bytes).')
"""
    print("\nRunning Hermes Agent verification check...")
    try:
        proc = subprocess.run([str(hermes_python), "-c", check_code], capture_output=True, text=True, check=True)
        print(proc.stdout.strip())
        print("  ✓ Hermes skill verification PASSED!")
    except subprocess.CalledProcessError as err:
        print(f"  ✗ Verification failed: {err.stderr}")


def main() -> None:
    print("=== Astrology Knowledge Base -> Hermes Unified Skill Synchronizer ===")
    cards = find_domain_cards()
    print(f"Found {len(cards)} domain cards in {KB_ROOT.relative_to(REPO_ROOT)}.")

    print("\n1. Updating master repository skill & local references...")
    update_master_skill(cards)

    print("\n2. Deploying unified skill & SOUL.md to Hermes Agent directories...")
    deploy_to_hermes(cards)

    print("\n3. Verifying Hermes runtime compatibility...")
    verify_hermes_skills()

    print("\n=== Sync Complete! ===")


if __name__ == "__main__":
    main()
