from __future__ import annotations

import re
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
                _("Password must include at least three of: lowercase, uppercase, digits, symbols."),
                code='password_no_complexity',
            )

    def get_help_text(self) -> str:  # type: ignore[no-untyped-def]
        return _("Your password should include at least three of the following: lowercase, uppercase, digits, symbols.")

