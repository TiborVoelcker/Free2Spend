"""Generated demo data.

A shipped module, not a test fixture: it lets the whole app run end to end with
no bank connection, and lets the strategy be judged across a full year before
any real data exists (docs/stack.md section 8).
"""

from demo.generator import generate_year

__all__ = ["generate_year"]
