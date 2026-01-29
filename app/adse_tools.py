"""
ADSE Tools Module

Implements the ADSE toolchain for tracking and auditing AI-generated code:
- P2C (Prompt-to-Code) Tracking Matrix
- Logic Coverage Audit
- ADSE Project Control Table 2.0

Based on the ADSE methodology by @超哥践行
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional, List
from datetime import datetime

from .db import fetchone, fetchall, execute
from .utils import now_iso
from .adse import get_quadrants, ADSEQuadrants


# =============================================================================
# P2C Tracking Matrix
# =============================================================================

@dataclass
class P2CTrackingItem:
    """P2C tracking item data class."""
    id: Optional[int]
    slice_id: int
    instruction_id: str
    instruction_desc: str
    instruction_category: str
    target_files: Optional[str] = None
    code_hash: Optional[str] = None
    status: str = "pending"  # pending, compliant, non_compliant, needs_audit
    audit_result: Optional[str] = None
    audit_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def extract_instruction_id(category: str, index: int) -> str:
    """Generate instruction ID from category and index."""
    category_map = {
        "functional": "FC",
        "physical": "PC",
        "semantic": "SC",  # Most important
        "exception": "EX",
    }
    prefix = category_map.get(category, "MP")
    return f"{prefix}-{index:03d}"


def parse_semantic_contract(quadrants: ADSEQuadrants) -> List[dict]:
    """
    Parse semantic contract text into structured instructions.

    Args:
        quadrants: ADSEQuadrants object

    Returns:
        List of instruction dictionaries
    """
    instructions = []
    semantic_text = quadrants.semantic_contract or ""

    # Split by common delimiters (newlines, bullets, dashes)
    lines = re.split(r'\n[-*•]\s*|\n(?=[A-Z])', semantic_text)

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Extract the core instruction
        # Remove common prefixes
        clean_line = re.sub(r'^[-*•]\s*', '', line)
        clean_line = re.sub(r'^\d+[\.\)]\s*', '', clean_line)

        instructions.append({
            "id": extract_instruction_id("semantic", i),
            "desc": clean_line,
            "category": "semantic",
        })

    # Also parse other quadrants
    if quadrants.functional_core:
        instructions.append({
            "id": extract_instruction_id("functional", 1),
            "desc": f"实现功能核心: {quadrants.functional_core[:100]}...",
            "category": "functional",
        })

    if quadrants.physical_constraints:
        # Extract technical constraints
        tech_lines = re.split(r'\n[-*•]\s*', quadrants.physical_constraints)
        for i, line in enumerate(tech_lines, 1):
            line = line.strip()
            if line and len(line) > 5:
                instructions.append({
                    "id": extract_instruction_id("physical", i),
                    "desc": line,
                    "category": "physical",
                })

    if quadrants.exceptions_edges:
        # Extract exception handling requirements
        exc_lines = re.split(r'\n[-*•]\s*', quadrants.exceptions_edges)
        for i, line in enumerate(exc_lines, 1):
            line = line.strip()
            if line and len(line) > 5:
                instructions.append({
                    "id": extract_instruction_id("exception", i),
                    "desc": line,
                    "category": "exception",
                })

    return instructions


def create_p2c_tracking_items(slice_id: int) -> int:
    """
    Create P2C tracking items from ADSE quadrants.

    Args:
        slice_id: Slice ID

    Returns:
        Number of items created
    """
    quadrants = get_quadrants(slice_id)
    if not quadrants:
        return 0

    instructions = parse_semantic_contract(quadrants)

    now = now_iso()
    count = 0

    for inst in instructions:
        # Check if already exists
        existing = fetchone(
            "SELECT id FROM p2c_tracking WHERE slice_id = ? AND instruction_id = ?",
            (slice_id, inst["id"])
        )

        if not existing:
            execute(
                """INSERT INTO p2c_tracking
                   (slice_id, instruction_id, instruction_desc, instruction_category, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
                (slice_id, inst["id"], inst["desc"], inst["category"], now, now)
            )
            count += 1

    return count


def get_p2c_tracking_matrix(slice_id: int) -> List[dict]:
    """
    Get P2C tracking matrix for a slice.

    Args:
        slice_id: Slice ID

    Returns:
        List of P2C tracking dictionaries
    """
    rows = fetchall(
        """SELECT * FROM p2c_tracking
           WHERE slice_id = ?
           ORDER BY instruction_category, instruction_id""",
        (slice_id,)
    )
    return [dict(r) for r in rows]


def update_p2c_tracking(
    tracking_id: int,
    target_files: Optional[str] = None,
    code_hash: Optional[str] = None,
    status: str = "pending",
    audit_result: Optional[str] = None,
    audit_notes: Optional[str] = None,
) -> bool:
    """
    Update P2C tracking item.

    Args:
        tracking_id: Tracking item ID
        target_files: Comma-separated list of target files
        code_hash: Git commit hash
        status: New status
        audit_result: Audit result
        audit_notes: Audit notes

    Returns:
        True if updated, False otherwise
    """
    now = now_iso()
    rows = execute(
        """UPDATE p2c_tracking
           SET target_files = ?, code_hash = ?, status = ?,
               audit_result = ?, audit_notes = ?, updated_at = ?
           WHERE id = ?""",
        (target_files, code_hash, status, audit_result, audit_notes, now, tracking_id)
    )
    return rows > 0


def update_p2c_from_artifacts(slice_id: int, artifacts: List[dict]) -> int:
    """
    Update P2C tracking from generated artifacts.

    Args:
        slice_id: Slice ID
        artifacts: List of artifact dictionaries from runs

    Returns:
        Number of tracking items updated
    """
    # Group artifacts by file path
    file_map = {}
    for artifact in artifacts:
        path = artifact.get("path", "")
        kind = artifact.get("kind", "")
        if path:
            if path not in file_map:
                file_map[path] = []
            file_map[path].append(kind)

    # Get pending tracking items
    tracking_items = fetchall(
        "SELECT * FROM p2c_tracking WHERE slice_id = ? AND status = 'pending'",
        (slice_id,)
    )

    updated = 0
    now = now_iso()

    for item in tracking_items:
        item_dict = dict(item)

        # Try to match instruction with files
        matched_files = []
        category = item_dict.get("instruction_category", "")

        # Simple matching based on category
        for file_path in file_map:
            if category == "functional" and any(k in file_path.lower() for k in ["prd", "doc"]):
                matched_files.append(file_path)
            elif category == "physical" and any(k in file_path for k in ["config", "setup", "requirement"]):
                matched_files.append(file_path)
            elif category == "semantic" and any(k in file_path for k in [".py", ".js", ".ts"]):
                matched_files.append(file_path)
            elif category == "exception" and any(k in file_path for k in ["error", "exception", "handler"]):
                matched_files.append(file_path)

        if matched_files:
            execute(
                """UPDATE p2c_tracking
                   SET target_files = ?, status = 'needs_audit', updated_at = ?
                   WHERE id = ?""",
                (",".join(matched_files), now, item_dict["id"])
            )
            updated += 1

    return updated


# =============================================================================
# Logic Coverage Audit
# =============================================================================

@dataclass
class LogicAuditFinding:
    """Logic audit finding data class."""
    instruction_id: str
    instruction_desc: str
    code_snippet: Optional[str]
    result: str  # pass, fail, partial
    notes: Optional[str]


@dataclass
class LogicAuditReport:
    """Logic audit report data class."""
    slice_id: int
    run_id: Optional[int]
    audit_type: str
    total_rules: int
    passed_rules: int
    failed_rules: int
    coverage_percent: float
    findings: List[LogicAuditFinding]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "slice_id": self.slice_id,
            "run_id": self.run_id,
            "audit_type": self.audit_type,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "coverage_percent": self.coverage_percent,
            "findings": [asdict(f) for f in self.findings],
            "created_at": self.created_at,
        }


def run_semantic_audit(slice_id: int, worktree_path: Path, run_id: Optional[int] = None) -> int:
    """
    Run semantic contract audit on generated code.

    Args:
        slice_id: Slice ID
        worktree_path: Path to the worktree
        run_id: Optional run ID

    Returns:
        Audit report ID
    """
    tracking_items = get_p2c_tracking_matrix(slice_id)

    findings = []
    passed = 0
    failed = 0
    partial = 0

    for item in tracking_items:
        instruction_id = item["instruction_id"]
        instruction_desc = item["instruction_desc"]
        target_files = item.get("target_files", "")

        # Default finding
        finding = LogicAuditFinding(
            instruction_id=instruction_id,
            instruction_desc=instruction_desc,
            code_snippet=None,
            result="fail",
            notes="未找到对应代码实现"
        )

        if target_files:
            # Check files
            files = target_files.split(",")
            found_files = []
            for f in files:
                file_path = worktree_path / f.lstrip("/")
                if file_path.exists():
                    found_files.append(str(file_path))

                    # Try to find relevant code snippet
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        # Extract a snippet around relevant keywords
                        snippet = extract_relevant_snippet(content, instruction_desc)
                        if snippet:
                            finding.code_snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                    except Exception:
                        pass

            if found_files:
                # Simple heuristic: if file exists, mark as pass
                finding.result = "pass"
                finding.notes = f"在 {len(found_files)} 个文件中找到实现"
                passed += 1
            else:
                failed += 1
        else:
            finding.notes = "未映射到任何文件"
            failed += 1

        findings.append(finding)

    total = len(findings)
    coverage = (passed / total * 100) if total > 0 else 0

    report = LogicAuditReport(
        slice_id=slice_id,
        run_id=run_id,
        audit_type="semantic_contract",
        total_rules=total,
        passed_rules=passed,
        failed_rules=failed,
        coverage_percent=coverage,
        findings=findings,
        created_at=now_iso(),
    )

    # Save report
    findings_json = json.dumps(report.to_dict(), ensure_ascii=False)
    report_id = execute(
        """INSERT INTO logic_audit_reports
           (slice_id, run_id, audit_type, total_rules, passed_rules, failed_rules, coverage_percent, findings_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slice_id, run_id, report.audit_type, report.total_rules,
         report.passed_rules, report.failed_rules, report.coverage_percent,
         findings_json, report.created_at)
    )

    return report_id


def extract_relevant_snippet(content: str, instruction: str) -> Optional[str]:
    """Extract relevant code snippet based on instruction keywords."""
    # Extract keywords from instruction
    keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', instruction)

    # Try to find lines with keywords
    lines = content.split("\n")
    for i, line in enumerate(lines):
        for kw in keywords[:3]:  # Check first 3 keywords
            if kw in line and len(line.strip()) > 10:
                # Get context (2 lines before and after)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                return "\n".join(lines[start:end])

    return None


def get_audit_reports(slice_id: int, limit: int = 10) -> List[dict]:
    """
    Get audit reports for a slice.

    Args:
        slice_id: Slice ID
        limit: Maximum number of reports

    Returns:
        List of audit report dictionaries
    """
    rows = fetchall(
        """SELECT * FROM logic_audit_reports
           WHERE slice_id = ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (slice_id, limit)
    )
    reports = []
    for row in rows:
        report = dict(row)
        try:
            report["findings"] = json.loads(report["findings_json"])
        except:
            report["findings"] = []
        reports.append(report)

    return reports


# =============================================================================
# ADSE Project Control Table 2.0
# =============================================================================

@dataclass
class ProjectControlItem:
    """ADSE project control item data class."""
    slice_id: int
    control_layer: str  # base, contract, slot, protection
    control_item: str
    requirement_source: Optional[str] = None
    tracking_mechanism: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: str = "pending"
    verified_at: Optional[str] = None
    verified_by: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


def initialize_project_control_table(slice_id: int) -> int:
    """
    Initialize ADSE project control table for a slice.

    Based on ADSE methodology, creates control items across 4 layers:
    1. Base Layer (基础层): Environment and physical constraints
    2. Contract Layer (契约层): Semantic contract and dark knowledge
    3. Slot Layer (插槽层): Hooks definition
    4. Protection Layer (防护层): Negative constraints

    Args:
        slice_id: Slice ID

    Returns:
        Number of control items created
    """
    quadrants = get_quadrants(slice_id)
    if not quadrants:
        return 0

    now = now_iso()
    count = 0

    # Layer 1: Base Layer - Physical Constraints
    if quadrants.physical_constraints:
        # Extract key physical constraints
        constraints = [
            "技术栈规范",
            "性能要求",
            "环境约束",
            "依赖管理",
        ]
        for item in constraints:
            _create_control_item(
                slice_id, "base", item,
                "physical_constraints",
                "路径隔离校验清单",
                "/core 严禁被业务 Hook 修改",
                now
            )
            count += 1

    # Layer 2: Contract Layer - Semantic Contract
    if quadrants.semantic_contract:
        instructions = parse_semantic_contract(quadrants)
        semantic_count = 0
        for inst in instructions:
            if inst["category"] == "semantic" and semantic_count < 5:  # Limit to 5 key items
                _create_control_item(
                    slice_id, "contract", f"语义契约: {inst['desc'][:30]}...",
                    "semantic_contract",
                    f"P2C追踪ID: {inst['id']}",
                    "核心逻辑必须符合语义契约中的「确定性」",
                    now
                )
                count += 1
                semantic_count += 1

    # Layer 3: Slot Layer - Hooks
    slot_items = [
        "状态变更Hook",
        "数据验证Hook",
        "错误处理Hook",
        "日志记录Hook",
    ]
    for item in slot_items:
        _create_control_item(
            slice_id, "slot", item,
            "functional_core",
            "钩子调用链分析图",
            "所有状态变更必须触发对应的Hook",
            now
        )
        count += 1

    # Layer 4: Protection Layer - Anti-patterns
    if quadrants.semantic_contract:
        protection_items = [
            "禁止使用的Anti-pattern",
            "安全边界检查",
            "异常处理覆盖",
        ]
        for item in protection_items:
            _create_control_item(
                slice_id, "protection", item,
                "semantic_contract",
                "自动化静态代码扫描",
                "代码中不得出现Anti-pattern清单内容",
                now
            )
            count += 1

    return count


def _create_control_item(
    slice_id: int,
    layer: str,
    item: str,
    source: str,
    tracking: str,
    acceptance: str,
    created_at: str,
) -> int:
    """Helper to create a control item."""
    return execute(
        """INSERT INTO adse_project_control
           (slice_id, control_layer, control_item, requirement_source,
            tracking_mechanism, acceptance_criteria, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (slice_id, layer, item, source, tracking, acceptance, created_at, created_at)
    )


def get_project_control_table(slice_id: int) -> List[dict]:
    """
    Get ADSE project control table for a slice.

    Args:
        slice_id: Slice ID

    Returns:
        List of control item dictionaries
    """
    rows = fetchall(
        """SELECT * FROM adse_project_control
           WHERE slice_id = ?
           ORDER BY control_layer, id""",
        (slice_id,)
    )
    return [dict(r) for r in rows]


def update_control_item_status(
    control_id: int,
    status: str,
    verified_by: Optional[int] = None,
) -> bool:
    """
    Update control item verification status.

    Args:
        control_id: Control item ID
        status: New status (pending, verified, failed)
        verified_by: User ID who verified

    Returns:
        True if updated
    """
    now = now_iso()
    rows = execute(
        """UPDATE adse_project_control
           SET status = ?, verified_at = ?, verified_by = ?, updated_at = ?
           WHERE id = ?""",
        (status, now, verified_by, now, control_id)
    )
    return rows > 0


def get_control_summary(slice_id: int) -> dict:
    """
    Get summary of project control table.

    Args:
        slice_id: Slice ID

    Returns:
        Summary dictionary with counts by layer and status
    """
    items = get_project_control_table(slice_id)

    summary = {
        "total": len(items),
        "by_layer": {
            "base": 0,
            "contract": 0,
            "slot": 0,
            "protection": 0,
        },
        "by_status": {
            "pending": 0,
            "verified": 0,
            "failed": 0,
        },
        "coverage_percent": 0,
    }

    for item in items:
        layer = item.get("control_layer", "")
        status = item.get("status", "pending")

        if layer in summary["by_layer"]:
            summary["by_layer"][layer] += 1

        if status in summary["by_status"]:
            summary["by_status"][status] += 1

    # Calculate coverage
    total = summary["total"]
    verified = summary["by_status"]["verified"]
    summary["coverage_percent"] = (verified / total * 100) if total > 0 else 0

    return summary
