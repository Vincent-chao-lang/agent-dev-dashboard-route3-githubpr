"""
Invitation code management system for user registration.
Only project owners can generate invitation codes.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from .db import fetchone, fetchall, execute
from .utils import now_iso


def generate_invite_code(length: int = 12) -> str:
    """
    Generate a random invitation code.

    Args:
        length: Code length (default 12 characters)

    Returns:
        Random code consisting of uppercase letters and numbers
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_invitation(project_id: int, created_by_user_id: int, expires_days: int = 7) -> str:
    """
    Create a new invitation code.

    Args:
        project_id: Project ID (optional, for project-specific invites)
        created_by_user_id: User ID who creates the invitation
        expires_days: Days until expiration (default 7)

    Returns:
        The invitation code
    """
    code = generate_invite_code()

    # Calculate expiration time
    expires_at = None
    if expires_days > 0:
        expiry = datetime.utcnow() + timedelta(days=expires_days)
        expires_at = expiry.isoformat()

    invitation_id = execute(
        """INSERT INTO invitations (code, project_id, created_by_user_id, status, created_at, expires_at)
           VALUES (?, ?, ?, 'pending', ?, ?)""",
        (code, project_id, created_by_user_id, now_iso(), expires_at)
    )

    return code


def validate_invitation(code: str) -> Optional[dict]:
    """
    Validate an invitation code and return invitation details.

    Args:
        code: Invitation code to validate

    Returns:
        Invitation dict if valid, None otherwise
    """
    invitation = fetchone(
        """SELECT * FROM invitations
           WHERE code = ? AND status = 'pending'
           ORDER BY created_at DESC LIMIT 1""",
        (code,)
    )

    if not invitation:
        return None

    # Check expiration
    if invitation["expires_at"]:
        try:
            expiry = datetime.fromisoformat(invitation["expires_at"])
            if datetime.utcnow() > expiry:
                return None  # Expired
        except ValueError:
            return None  # Invalid date format

    return dict(invitation)


def use_invitation(code: str, user_id: int) -> bool:
    """
    Mark an invitation code as used.

    Args:
        code: Invitation code
        user_id: User ID who used the code

    Returns:
        True if successful, False otherwise
    """
    invitation = fetchone(
        "SELECT * FROM invitations WHERE code = ? AND status = 'pending'",
        (code,)
    )

    if not invitation:
        return False

    # Check expiration
    if invitation["expires_at"]:
        try:
            expiry = datetime.fromisoformat(invitation["expires_at"])
            if datetime.utcnow() > expiry:
                return False  # Expired
        except ValueError:
            pass

    # Mark as used
    execute(
        """UPDATE invitations
           SET status = 'used', used_by_user_id = ?, used_at = ?
           WHERE code = ?""",
        (user_id, now_iso(), code)
    )

    return True


def get_project_invitations(project_id: int) -> list:
    """
    Get all invitations for a project.

    Args:
        project_id: Project ID

    Returns:
        List of invitation dictionaries
    """
    invitations = fetchall(
        """SELECT i.*, u1.username as created_by_username, u2.username as used_by_username
           FROM invitations i
           LEFT JOIN users u1 ON u1.id = i.created_by_user_id
           LEFT JOIN users u2 ON u2.id = i.used_by_user_id
           WHERE i.project_id = ?
           ORDER BY i.created_at DESC""",
        (project_id,)
    )

    return [dict(inv) for inv in invitations]


def get_user_invitations(user_id: int) -> list:
    """
    Get all invitations created by a user.

    Args:
        user_id: User ID

    Returns:
        List of invitation dictionaries
    """
    invitations = fetchall(
        """SELECT i.*, p.name as project_name
           FROM invitations i
           LEFT JOIN projects p ON p.id = i.project_id
           WHERE i.created_by_user_id = ?
           ORDER BY i.created_at DESC""",
        (user_id,)
    )

    return [dict(inv) for inv in invitations]


def revoke_invitation(code: int) -> bool:
    """
    Revoke an invitation code by marking it as cancelled.

    Args:
        code: Invitation ID

    Returns:
        True if successful, False otherwise
    """
    rows = execute(
        "UPDATE invitations SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
        (code,)
    )

    return rows > 0
