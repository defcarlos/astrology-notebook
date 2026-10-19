#!/usr/bin/env python3
"""Sync astrology skills and domain card references to Hermes Agent and local profiles.

This script:
1. Creates local references/ symlinks in astrology_kb/ for portable skill navigation.
2. Updates SKILL.md links to use the references/ standard (supported by Hermes & Antigravity).
3. Deploys self-contained skill packages to ~/.hermes/skills/astrology/ and active Hermes profiles.
4. Copies reference markdown files into Hermes references/ directories so that Hermes Agent's
   internal validate_within_dir security checks pass without path traversal errors.
5. Validates the installation using Hermes Agent's skill_view runtime.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = REPO_ROOT / "astrology_kb"
WRITER_DIR = KB_ROOT / "astrology-writer"
GATEKEEPER_DIR = KB_ROOT / "astrology-report-gatekeeper"

HERMES_ROOT = Path.home() / ".hermes"
HERMES_GLOBAL_SKILLS = HERMES_ROOT / "skills" / "astrology"
HERMES_PROFILES_DIR = HERMES_ROOT / "profiles"

EXCLUDE_FILENAMES = {
    "SKILL.md", "README.md", "index.md", "INDEX.md",
    "astrology_writer.md", "astrology_report_gatekeeper.md",
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
        # Check if target ends with one of our domain card filenames
        target_name = Path(target).name
        if target_name in cards:
            return f"[{text}](references/{target_name})"
        return match.group(0)

    # Match markdown links: [text](path.md)
    return re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', _replace_link, content)


def update_master_skills(cards: dict[str, Path]) -> None:
    """Update SKILL.md in astrology_kb with references/ links and local symlinks."""
    for skill_dir in [WRITER_DIR, GATEKEEPER_DIR]:
        setup_local_references_symlinks(skill_dir, cards)
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        updated = rewrite_markdown_links(content, cards)
        if updated != content:
            skill_file.write_text(updated, encoding="utf-8")
            print(f"  ✓ Updated links in {skill_file.relative_to(REPO_ROOT)}")
        else:
            print(f"  ✓ Links already up to date in {skill_file.relative_to(REPO_ROOT)}")


def deploy_to_hermes(cards: dict[str, Path]) -> None:
    """Deploy self-contained packages to Hermes global skills and profile skills."""
    target_skill_roots = [HERMES_GLOBAL_SKILLS]

    if HERMES_PROFILES_DIR.exists():
        for prof in HERMES_PROFILES_DIR.iterdir():
            if prof.is_dir():
                prof_skills = prof / "skills" / "astrology"
                if prof_skills.exists():
                    target_skill_roots.append(prof_skills)

    for base_dir in target_skill_roots:
        print(f"\nDeploying to: {base_dir}")
        for skill_name, src_dir in [("astrology-writer", WRITER_DIR), ("astrology-report-gatekeeper", GATEKEEPER_DIR)]:
            dest_skill_dir = base_dir / skill_name
            dest_skill_dir.mkdir(parents=True, exist_ok=True)

            # Copy SKILL.md
            src_skill_md = src_dir / "SKILL.md"
            dest_skill_md = dest_skill_dir / "SKILL.md"
            content = src_skill_md.read_text(encoding="utf-8")
            rewritten = rewrite_markdown_links(content, cards)
            dest_skill_md.write_text(rewritten, encoding="utf-8")

            # Copy physical files into references/ (physical copy required for Hermes validate_within_dir)
            dest_ref_dir = dest_skill_dir / "references"
            if dest_ref_dir.exists():
                shutil.rmtree(dest_ref_dir)
            dest_ref_dir.mkdir(parents=True, exist_ok=True)

            for card_name, card_src in cards.items():
                shutil.copy2(card_src, dest_ref_dir / card_name)

            print(f"  ✓ {skill_name}: SKILL.md + {len(cards)} reference files deployed")


def verify_hermes_skills() -> None:
    """Verify that Hermes Agent's skill_view can load astrology-writer and its linked files."""
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

res_writer = json.loads(skill_view('astrology-writer'))
assert res_writer.get('success'), f'Failed loading astrology-writer: {res_writer}'
linked = res_writer.get('linked_files', {}).get('references', [])
print(f'Hermes runtime check: astrology-writer loaded successfully with {len(linked)} linked reference files.')

# Test viewing one reference card
res_file = json.loads(skill_view('astrology-writer', file_path='references/the_12_bhavas.md'))
assert res_file.get('success'), f'Failed reading reference card: {res_file}'
print(f'Hermes runtime check: references/the_12_bhavas.md read successfully ({len(res_file.get(\"content\", \"\"))} bytes).')
"""
    print("\nRunning Hermes Agent verification check...")
    try:
        proc = subprocess.run([str(hermes_python), "-c", check_code], capture_output=True, text=True, check=True)
        print(proc.stdout.strip())
        print("  ✓ Hermes skill verification PASSED!")
    except subprocess.CalledProcessError as err:
        print(f"  ✗ Verification failed: {err.stderr}")


def main() -> None:
    print("=== Astrology Knowledge Base -> Hermes Skill Synchronizer ===")
    cards = find_domain_cards()
    print(f"Found {len(cards)} domain cards in {KB_ROOT.relative_to(REPO_ROOT)}.")
    
    print("\n1. Updating master repository skills & local references...")
    update_master_skills(cards)

    print("\n2. Deploying to Hermes Agent directories...")
    deploy_to_hermes(cards)

    print("\n3. Verifying Hermes runtime compatibility...")
    verify_hermes_skills()

    print("\n=== Sync Complete! ===")


if __name__ == "__main__":
    main()
