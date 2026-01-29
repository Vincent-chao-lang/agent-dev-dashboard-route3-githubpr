"""
Online Help Module

Simple help system that renders the user guide markdown directly.
"""
import re
from pathlib import Path
from typing import Optional, List
import markdown as md
from markdown.extensions import toc, tables, fenced_code, nl2br, sane_lists


# Get the docs directory
DOCS_DIR = Path(__file__).parent.parent / "docs"
USER_GUIDE_PATH = DOCS_DIR / "用户指南.md"


def get_help_toc() -> List[dict]:
    """
    Extract table of contents from the user guide.

    Returns:
        List of TOC items with id and title
    """
    try:
        content = USER_GUIDE_PATH.read_text(encoding="utf-8")

        toc_items = []
        lines = content.split('\n')

        in_toc = False
        for line in lines:
            # Detect TOC section
            if '📖 目录' in line or '目录' in line:
                in_toc = True
                continue

            # End of TOC
            if in_toc and line.startswith('---'):
                break

            # Parse TOC entries: [title](#anchor)
            if in_toc:
                match = re.match(r'^\s*\d+\.\s+\[([^\]]+)\]\(#([^\)]+)\)', line)
                if match:
                    title = match.group(1)
                    anchor = match.group(2)
                    toc_items.append({
                        "title": title,
                        "anchor": anchor,
                    })

        return toc_items

    except Exception:
        return []


def get_help_html(lang: str = "zh", section: Optional[str] = None) -> dict:
    """
    Get the complete help documentation as HTML.

    Args:
        lang: Language code (currently only zh supported)
        section: Optional section anchor to jump to

    Returns:
        Dictionary with title and HTML content
    """
    try:
        # Read the markdown file
        content = USER_GUIDE_PATH.read_text(encoding="utf-8")

        # Remove the TOC section from markdown (since we have sidebar navigation)
        # Find and remove the ## 📖 目录 section
        toc_match = re.search(r'## 📖 目录\n.*?(?=---|\n## )', content, re.DOTALL)
        if toc_match:
            content = content[:toc_match.start()] + content[toc_match.end():]

        # Add IDs to all headings for anchor linking
        lines = content.split('\n')
        processed_lines = []
        anchor_map = {}

        for line in lines:
            # Match ## headings
            heading_match = re.match(r'^(##+)\s+(.+)', line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Generate anchor from title
                # Remove emoji and special chars, convert to lowercase
                anchor = title.lower()
                anchor = re.sub(r'[^\w\s-]', '', anchor)
                anchor = re.sub(r'[\s_]+', '-', anchor)
                anchor = anchor.strip('-')

                # Store mapping for TOC
                anchor_map[title] = anchor

                # Add anchor attribute
                processed_lines.append(f'{heading_match.group(1)} {title} {{#{anchor}}}')
            else:
                processed_lines.append(line)

        content = '\n'.join(processed_lines)

        # Configure markdown with extensions
        md_extensions = [
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists',
            'toc',
            'attr_list',  # For adding IDs to headings
        ]

        # Convert to HTML
        html_content = md.markdown(content, extensions=md_extensions)

        # Extract title
        title_match = re.search(r'# (.+)', content)
        title = title_match.group(1) if title_match else "用户指南"

        # Get TOC
        toc_items = get_help_toc()

        return {
            "title": title,
            "content": html_content,
            "toc": toc_items,
            "section": section,
        }

    except Exception as e:
        return {
            "title": "帮助文档",
            "content": f"<p>无法加载帮助文档: {str(e)}</p>",
            "toc": [],
            "section": section,
        }


def search_help(query: str, lang: str = "zh") -> list[dict]:
    """
    Search help documentation.

    Args:
        query: Search query
        lang: Language code

    Returns:
        List of search results
    """
    results = []

    try:
        content = USER_GUIDE_PATH.read_text(encoding="utf-8")

        # Simple text search
        query_lower = query.lower()
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # Extract context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = '\n'.join(lines[start:end])

                # Find section title
                section_title = "未知章节"
                for j in range(max(0, i - 50), i):
                    if lines[j].startswith('## '):
                        section_title = lines[j][3:].strip()
                        break

                # Generate section ID
                section_id = section_title.lower().replace(' ', '_').replace(':', '').replace('【', '').replace('】', '')

                # Clean up context
                context = context.replace(query, f"<strong>{query}</strong>")
                context = context[:300] + "..." if len(context) > 300 else context

                results.append({
                    "section": section_title,
                    "section_id": section_id,
                    "context": context,
                })

                if len(results) >= 10:  # Limit results
                    break

    except Exception:
        pass

    return results
