"""Backward-compatible entry point for the corrected oral formalization acceptance.

The former implementation reconstructed runtime inputs from reference targets and
therefore measured copying instead of generation.  Keep this filename for old
commands, but route it to the leakage-free short-field acceptance suite.
"""

from evaluate_oral_formalization import main


if __name__ == "__main__":
    main()
