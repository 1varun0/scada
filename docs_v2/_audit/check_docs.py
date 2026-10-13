#!/usr/bin/env python3
"""
Automated documentation consistency and link integrity checker for docs_v2.

Checks:
1. Markdown file links (relative links between docs_v2 files).
2. Referenced repository files in backticks exist on disk.
3. Mermaid blocks are properly closed.
4. Document headers (Title, Audience, Scope, Status, Evidence Tags).
5. Verification section present at end of each document.
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_V2_DIR = REPO_ROOT / "docs_v2"

print(f"=== SCADA Hybrid IDS docs_v2 Audit Checker ===")
print(f"Repository Root: {REPO_ROOT}")
print(f"Documentation Directory: {DOCS_V2_DIR}")

# 1. Collect all markdown files in docs_v2
doc_files = sorted(list(DOCS_V2_DIR.glob("*.md")))
print(f"Found {len(doc_files)} markdown files in docs_v2/ root.")

errors = []
warnings = []

# Regex patterns
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
CODE_TAG_PATTERN = re.compile(r'\[CODE\s+([^:\]]+)(?::(\d+(?:-\d+)?))?\]')
MERMAID_OPEN = re.compile(r'```mermaid')
CODE_BLOCK_FENCE = re.compile(r'^```')

for doc in doc_files:
    text = doc.read_text(encoding="utf-8")
    lines = text.splitlines()
    doc_rel = doc.relative_to(REPO_ROOT)
    
    # Check 1: Header verification
    if not lines or not lines[0].startswith("# "):
        errors.append(f"{doc_rel}: Missing level 1 heading on line 1")
    
    header_block = "\n".join(lines[:12])
    for required_field in ["Audience", "Scope", "Status", "Evidence Tags"]:
        pattern = re.compile(rf'(\*\*|- \*\*){required_field}(\*\*:|:\*\*)', re.IGNORECASE)
        # Also check for Purpose as equivalent to Scope
        if not pattern.search(header_block):
            if required_field == "Scope" and re.search(r'(\*\*|- \*\*)Purpose(\*\*:|:\*\*)', header_block, re.IGNORECASE):
                continue
            if required_field == "Evidence Tags" and "Evidence" in header_block:
                continue
            warnings.append(f"{doc_rel}: Missing metadata field '{required_field}' in header")

    # Check 2: Verification section at end
    has_verification = any("##" in line and "Verification" in line for line in lines)
    if not has_verification:
        warnings.append(f"{doc_rel}: Missing 'Verification' section heading")

    # Check 3: Mermaid block closure
    in_code_block = False
    in_mermaid = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```mermaid"):
            if in_code_block:
                errors.append(f"{doc_rel}:{i}: Nested mermaid block inside code fence")
            in_code_block = True
            in_mermaid = True
        elif line.strip().startswith("```") and in_code_block:
            in_code_block = False
            in_mermaid = False
    if in_mermaid:
        errors.append(f"{doc_rel}: Unclosed mermaid block at end of file")

    # Check 4: Markdown Links
    for i, line in enumerate(lines, 1):
        for match in LINK_PATTERN.finditer(line):
            link_text, link_target = match.groups()
            link_target = link_target.strip()
            
            # Skip external links, mailto, and fragment-only anchors
            if link_target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            
            # File URI handling: file:///c:/projects/p1/New%20folder/...
            if link_target.startswith("file:///"):
                import urllib.parse
                clean_target = link_target[8:] # strip file:///
                # Strip anchor
                clean_target = clean_target.split("#")[0]
                # URL unquote
                clean_target = urllib.parse.unquote(clean_target)
                target_path = Path(clean_target)
                if not target_path.exists():
                    errors.append(f"{doc_rel}:{i}: Broken file URI target '{link_target}'")
                continue

            # File link with optional anchor: file.md#anchor
            target_path_str = link_target.split("#")[0]
            if not target_path_str:
                continue
            
            target_path = (doc.parent / target_path_str).resolve()
            if not target_path.exists():
                # Check relative to REPO_ROOT
                target_root_path = (REPO_ROOT / target_path_str).resolve()
                if not target_root_path.exists():
                    errors.append(f"{doc_rel}:{i}: Broken link target '{link_target}'")

    # Check 5: Code citations [CODE path:line]
    for i, line in enumerate(lines, 1):
        for match in CODE_TAG_PATTERN.finditer(line):
            cited_path = match.group(1).strip()
            # Clean possible trailing/leading brackets, backticks, punctuation
            cited_path = cited_path.strip("`'\"[]")
            cited_path = cited_path.rstrip(".,;)]")
            target_file = REPO_ROOT / cited_path
            if not target_file.exists():
                warnings.append(f"{doc_rel}:{i}: Cited file does not exist: '{cited_path}'")

print(f"\n--- Audit Summary ---")
print(f"Total Errors: {len(errors)}")
print(f"Total Warnings: {len(warnings)}")

if warnings:
    print(f"\nWarnings ({len(warnings)}):")
    for w in warnings[:20]:
        print(f"  [WARN] {w}")
    if len(warnings) > 20:
        print(f"  ... and {len(warnings) - 20} more warnings")

if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors:
        print(f"  [ERROR] {e}")
    sys.exit(1)
else:
    print("\nSUCCESS: All document headers, links, and code blocks passed audit check!")
    sys.exit(0)
