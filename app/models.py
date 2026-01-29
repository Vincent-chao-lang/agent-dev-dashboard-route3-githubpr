"""
SQLAlchemy ORM Models

Defines all database models for the application.
Supports both SQLite (development) and PostgreSQL (production).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Float, DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    owned_projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    slices = relationship("Slice", back_populates="created_by", cascade="all, delete-orphan")
    context_packs = relationship("ContextPack", back_populates="created_by", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="created_by", cascade="all, delete-orphan")
    gates = relationship("Gate", back_populates="created_by", cascade="all, delete-orphan")
    invitations_created = relationship("Invitation", foreign_keys="Invitation.created_by_user_id", back_populates="created_by", cascade="all, delete-orphan")
    invitations_used = relationship("Invitation", foreign_keys="Invitation.used_by_user_id", back_populates="used_by")
    llm_configs = relationship("UserLLMConfig", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(200), nullable=False)
    local_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # GitHub integration
    github_owner: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    github_repo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    slices = relationship("Slice", back_populates="project", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="project", cascade="all, delete-orphan")
    llm_configs = relationship("ProjectLLMConfig", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'owner' or 'member'
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")


class Slice(Base):
    __tablename__ = "slices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    out_of_scope: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)  # 'low', 'medium', 'high'
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    branch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # GitHub PR integration
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # ADSE enhancement
    adse_enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 or 1

    # Relationships
    project = relationship("Project", back_populates="slices")
    created_by = relationship("User", back_populates="slices")
    acceptance_criteria = relationship("AcceptanceCriteria", back_populates="slice", cascade="all, delete-orphan")
    context_packs = relationship("ContextPack", back_populates="slice", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="slice", cascade="all, delete-orphan")
    gates = relationship("Gate", back_populates="slice", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="slice", cascade="all, delete-orphan")
    adse_quadrant = relationship("SliceADSEQuadrant", back_populates="slice", uselist=False, cascade="all, delete-orphan")
    meta_prompts = relationship("SliceMetaPrompt", back_populates="slice", cascade="all, delete-orphan")
    p2c_tracking = relationship("P2CTracking", back_populates="slice", cascade="all, delete-orphan")
    logic_audit_reports = relationship("LogicAuditReport", back_populates="slice", cascade="all, delete-orphan")
    adse_controls = relationship("ADSEProjectControl", back_populates="slice", cascade="all, delete-orphan")


class AcceptanceCriteria(Base):
    __tablename__ = "acceptance_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    verification: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="acceptance_criteria")


class ContextPack(Base):
    __tablename__ = "context_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="context_packs")
    created_by = relationship("User", back_populates="context_packs")
    runs = relationship("Run", back_populates="context_pack")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pm', 'architect', 'dev', 'qa', 'ops'
    context_pack_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("context_packs.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'running', 'success', 'failure'
    worktree_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    started_at: Mapped[str] = mapped_column(String(100), nullable=False)
    ended_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    log: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="runs")
    context_pack = relationship("ContextPack", back_populates="runs")
    created_by = relationship("User", back_populates="runs")
    gates = relationship("Gate", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")
    logic_audit_reports = relationship("LogicAuditReport", back_populates="run", cascade="all, delete-orphan")


class Gate(Base):
    __tablename__ = "gates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'lint', 'type', 'contract', 'test'
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pass', 'fail'
    output: Mapped[str] = mapped_column(Text, nullable=False)
    ran_at: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="gates")
    run = relationship("Run", back_populates="gates")
    created_by = relationship("User", back_populates="gates")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # 'doc', 'code', 'test', 'config'
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="artifacts")
    run = relationship("Run", back_populates="artifacts")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    used_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # 'pending', 'used', 'expired'
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    expires_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    used_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="invitations")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="invitations_created")
    used_by = relationship("User", foreign_keys=[used_by_user_id], back_populates="invitations_used")


class UserLLMConfig(Base):
    __tablename__ = "user_llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="glm")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    user = relationship("User", back_populates="llm_configs")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class ProjectLLMConfig(Base):
    __tablename__ = "project_llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="glm")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="llm_configs")

    __table_args__ = (
        UniqueConstraint("project_id", "provider", name="uq_project_provider"),
    )


class SliceADSEQuadrant(Base):
    __tablename__ = "slice_adse_quadrants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), unique=True, nullable=False)
    functional_core: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    physical_constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semantic_contract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exceptions_edges: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="adse_quadrant")


class SliceMetaPrompt(Base):
    __tablename__ = "slice_meta_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pm', 'architect', 'dev', 'qa', 'ops'
    prompt_content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="meta_prompts")


class P2CTracking(Base):
    __tablename__ = "p2c_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    instruction_id: Mapped[str] = mapped_column(String(200), nullable=False)
    instruction_desc: Mapped[str] = mapped_column(Text, nullable=False)
    instruction_category: Mapped[str] = mapped_column(String(100), nullable=False)
    target_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    code_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    audit_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audit_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="p2c_tracking")


class LogicAuditReport(Base):
    __tablename__ = "logic_audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    audit_type: Mapped[str] = mapped_column(String(100), nullable=False)
    total_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    findings_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="logic_audit_reports")
    run = relationship("Run", back_populates="logic_audit_reports")


class ADSEProjectControl(Base):
    __tablename__ = "adse_project_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slice_id: Mapped[int] = mapped_column(Integer, ForeignKey("slices.id", ondelete="CASCADE"), unique=True, nullable=False)
    control_layer: Mapped[str] = mapped_column(String(100), nullable=False)
    control_item: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tracking_mechanism: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    verified_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    slice = relationship("Slice", back_populates="adse_controls")
