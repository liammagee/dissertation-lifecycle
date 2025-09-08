from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

from django.contrib.auth.password_validation import (
    MinimumLengthValidator as BaseMinLength,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """Require a mix of character classes.

    Policy: password must contain at least 3 of 4 categories:
    - lowercase letters
    - uppercase letters
    - digits
    - symbols (non-alphanumeric)
    """

    def validate(self, password: str, user=None) -> None:  # type: ignore[no-untyped-def]
        cats = 0
        cats += 1 if re.search(r"[a-z]", password) else 0
        cats += 1 if re.search(r"[A-Z]", password) else 0
        cats += 1 if re.search(r"\d", password) else 0
        cats += 1 if re.search(r"[^\w]", password) else 0
        if cats < 3:
            raise ValidationError(
                _("Try a stronger password: include at least three of these: lowercase, uppercase, digits, symbols."),
                code='password_no_complexity',
            )

    def get_help_text(self) -> str:  # type: ignore[no-untyped-def]
        return _("Use a mix of character types (lowercase, uppercase, digits, symbols).")


class FriendlyMinLengthValidator(BaseMinLength):
    """Minimum length with a more helpful error/help message."""

    def validate(self, password: str, user=None) -> None:  # type: ignore[no-untyped-def]
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"Use at least {self.min_length} characters (a short passphrase works well)."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self) -> str:  # type: ignore[no-untyped-def]
        return _(f"Minimum length: {self.min_length} characters.")


class FriendlyUserAttributeSimilarityValidator:
    """Friendlier variant of Django's UserAttributeSimilarityValidator.

    Warns when the password is too similar to the username, email, etc.,
    and suggests concrete remedies.
    """

    def __init__(self, user_attributes: Iterable[str] | None = None, max_similarity: float = 0.7):
        self.user_attributes = list(user_attributes or ('username', 'email'))
        self.max_similarity = float(max_similarity)

    def validate(self, password: str, user=None) -> None:  # type: ignore[no-untyped-def]
        if not user:
            return
        pw = (password or '').lower()
        for attr in self.user_attributes:
            val = getattr(user, attr, None)
            if not val or not isinstance(val, str):
                continue
            # Compare against the whole value and its parts split on non-word characters
            parts = set(re.split(r"\W+", val) + [val])
            for part in parts:
                part = (part or '').strip()
                if len(part) < 3:
                    continue
                ratio = SequenceMatcher(a=pw, b=part.lower()).quick_ratio()
                if ratio >= self.max_similarity:
                    label = 'username' if attr == 'username' else attr.replace('_', ' ')
                    raise ValidationError(
                        _(
                            f"Password looks too similar to your {label}. Try adding unrelated words, numbers, or symbols, or choose a different phrase."
                        ),
                        code='password_too_similar',
                    )

    def get_help_text(self) -> str:  # type: ignore[no-untyped-def]
        return _("Avoid using your username or email inside your password.")
