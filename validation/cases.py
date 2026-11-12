"""
cases.py - Test strings with their EXPECTED verdicts.

The "report" lists come from Table 3 of the assignment report.  The expected results are
derived by hand from the formal rules, never copied from the program's own output.
"""
from __future__ import annotations

# ---------------------------------------------------------------- PIN ---
PIN_REPORT_ACCEPT = ["4821", "0000", "9375", "1234", "0042"]
PIN_REPORT_REJECT = ["482", "48211", "48a1", "12 34", "", "-123"]
PIN_BOUNDARY_ACCEPT = ["9999", "0001", "1000"]
PIN_BOUNDARY_REJECT = [
    "1", "12", "123", "12345", "12345678", " 1234", "1234 ", "12.4", "+123", "12e3", "abcd",
    "١٢٣٤",    # Arabic-Indic digits are NOT ASCII digits
    "１２３４",  # full-width digits are NOT ASCII digits
    "1234\n",
]

# ---------------------------------------------------------- card lock ---
CARD_REPORT_USABLE = ["", "C", "WC", "WWC", "CW", "W", "WW"]
CARD_REPORT_LOCKED = ["WWW", "WWWC", "WWCWWW", "WWWW"]
CARD_EXTRA_USABLE = ["CCC", "WCWCWC", "WWCWWCWW", "CWWCWW", "WCW", "CCW"]
CARD_EXTRA_LOCKED = ["WWWCCC", "CWWW", "WCWWW", "WWCWWWC", "WWWWWWWW"]

# ----------------------------------------------------------- password ---
PW_REPORT_ACCEPT = ["Srm@2026", "Trichy#Aiml5", "aB3$efgh", "P@ssw0rdX"]
PW_REPORT_REJECT = [
    "srm@2026",              # no uppercase
    "SRM@2026",              # no lowercase
    "Srm@Trichy",            # no digit
    "Srm20266",              # no special
    "Sr@1",                  # too short
    "Aa1!Aa1!Aa1!Aa1!A",     # 17 characters, all four classes
]
# Extra hand-checked boundary cases: (text, expected_accept, why)
PW_EXTRA = [
    ("Aa1!Aa1!", True, "exactly 8 characters, all classes"),
    ("Aa1!Aa1!Aa1!Aa1!", True, "exactly 16 characters, all classes"),
    ("Aa1!Aa1", False, "7 characters"),
    ("Srm@ 2026", True, "space is class O: it only counts towards the length"),
    ("Srm@2026é", True, "non-ASCII letter is class O: it only counts towards the length"),
    ("        ", False, "eight spaces: length ok but no class satisfied"),
    ("", False, "empty password"),
    ("ABCDEFGH", False, "uppercase only"),
    ("abcdefgh", False, "lowercase only"),
    ("12345678", False, "digits only"),
    ("!@#$%^&*", False, "special characters only"),
    ("Aa1~Aa1~", True, "'~' counts as printable ASCII punctuation"),
    ("Aa1_Aa1_", True, "'_' counts as printable ASCII punctuation"),
]

# --------------------------------------------------------------- e-mail ---
EMAIL_REPORT_ACCEPT = [
    "harshini.rk@srmist.edu.in", "ra2411026050232@srmist.edu.in",
    "srm_student@gmail.com", "a-b.c@my-site.co", "x@y.io",
]
EMAIL_REPORT_REJECT = [
    "harshini@srmist",
    ".hHarshini@gmail.com",       # as typed in the task statement (leading dot)
    ".harshini@gmail.com",        # corrected spelling from the report
    "harshini..rk@gmail.com", "harshini@-srm.in", "harshini@srm.c0m", "harshini@@gmail.com",
]
EMAIL_BOUNDARY_ACCEPT = [
    "a@b.cc", "a@b.ccc", "a1@b2.co", "a_b@c.io", "a-b@c.io", "a.b@c.io", "a@b-c.io", "a@b--c.io",
    "a@b.c.io", "A@B.COM", "1@2.io", "a@b.cd.ef", "a_b-c.d@e-f.g-h.ij", "a@1.io", "a@b.cd-ef.gh",
]
EMAIL_BOUNDARY_REJECT = [
    "a@b.c",            # TLD with one letter
    "a@b.c1", "a@b.1c", "a@b.12",   # TLD must be letters only
    ".a@b.co", "a.@b.co", "-a@b.co", "a-@b.co", "_a@b.co",  # separators at the edges of the local part
    "a__b@c.co", "a._b@c.co", "a..b@c.co",                   # two separators in a row
    "a@.b.co", "a@b..co", "a@b.co.", "a@b.-co", "a@b-.co", "a@-b.co", "a@b.co-", "a@b.c-o",
    "a@b", "a@", "@b.co", "", "@", "a@@b.co", "a@b@c.co",   # '@' problems
    "a b@c.co", "a@b c.co", "é@b.co", "a@é.co", "a@b.cé",   # forbidden characters
    "a@b_c.co", "a@b.co_m", "user+tag@b.co",
]

# --------------------------------------------- expected transition tables ---
# Table 1 of the report, typed in from the report text.
PIN_TABLE_FROM_REPORT = {
    ("q0", "D"): "q1", ("q0", "O"): "qD",
    ("q1", "D"): "q2", ("q1", "O"): "qD",
    ("q2", "D"): "q3", ("q2", "O"): "qD",
    ("q3", "D"): "q4", ("q3", "O"): "qD",
    ("q4", "D"): "qD", ("q4", "O"): "qD",
    ("qD", "D"): "qD", ("qD", "O"): "qD",
}
# Card-lock rules from the task statement.
CARD_TABLE_FROM_RULES = {
    ("s0", "C"): "s0", ("s0", "W"): "s1",
    ("s1", "C"): "s0", ("s1", "W"): "s2",
    ("s2", "C"): "s0", ("s2", "W"): "LOCK",
    ("LOCK", "C"): "LOCK", ("LOCK", "W"): "LOCK",
}


def password_boundary_cases() -> list[tuple[str, bool, str]]:
    """
    Lengths 7, 8, 16, 17, each with all classes present and with each class missing in turn.
    Expected verdict (from the policy text): accepted only if length is 8..16 AND nothing is missing.
    """
    pools = {"U": "A", "L": "b", "D": "7", "S": "!"}
    cases = []
    for length in (7, 8, 16, 17):
        for missing in (None, "U", "L", "D", "S"):
            used = [c for c in "ULDS" if c != missing]
            text = "".join(pools[c] for c in used)                # one of each available class
            i = 0
            while len(text) < length:                            # pad using only available classes
                text += pools[used[i % len(used)]]
                i += 1
            expected = (7 < length < 17) and missing is None
            why = f"length {length}, " + ("all classes present" if missing is None else f"{missing} missing")
            cases.append((text, expected, why))
    return cases
