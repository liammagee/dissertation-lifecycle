"""Make tests a package so Django's runner (`manage.py test`) discovers them.

Django imports `<app>.tests` (a module or package). Without this file,
`tracker/tests/` is just a directory and the default runner finds 0 tests.
"""

