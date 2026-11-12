"""Tests for Module 1: PIN DFA and card-lock DFA."""
from itertools import product

import pytest

from automata.dfa import AutomatonError
from automata.pin_automata import (CardLock, build_card_lock_dfa, build_pin_dfa, card_usable,
                                   classify_pin_char, run_card_events, validate_pin)
from validation import cases as C
from validation.reference import ref_card_state, ref_pin


# ---------------------------------------------------------------- PIN DFA ---
@pytest.mark.parametrize("pin", C.PIN_REPORT_ACCEPT + C.PIN_BOUNDARY_ACCEPT)
def test_pin_accepted(pin):
    assert validate_pin(pin).accepted


@pytest.mark.parametrize("pin", C.PIN_REPORT_REJECT + C.PIN_BOUNDARY_REJECT)
def test_pin_rejected(pin):
    assert not validate_pin(pin).accepted


def test_pin_dfa_has_six_states_and_one_accepting():
    dfa = build_pin_dfa()
    assert dfa.states == ["q0", "q1", "q2", "q3", "q4", "qD"]
    assert dfa.accepting == {"q4"}
    assert dfa.dead_states() == {"qD"}


def test_pin_transition_table_matches_report_table_1():
    assert build_pin_dfa().delta == C.PIN_TABLE_FROM_REPORT


def test_pin_trace_of_valid_pin():
    res = validate_pin("4821")
    assert [(r["From"], r["To"]) for r in res.steps] == [("q0", "q1"), ("q1", "q2"), ("q2", "q3"), ("q3", "q4")]
    assert res.final_state == "q4"


def test_pin_fifth_digit_goes_to_trap():
    res = validate_pin("48211")
    assert res.final_state == "qD" and "fifth digit" in res.reason


def test_pin_non_digit_goes_to_trap_and_stays():
    res = validate_pin("48a1")
    assert [r["To"] for r in res.steps] == ["q1", "q2", "qD", "qD"]


def test_pin_empty_string_stays_in_start_state():
    res = validate_pin("")
    assert res.final_state == "q0" and not res.accepted and res.steps == []


def test_unicode_digits_are_not_pin_digits():
    assert classify_pin_char("٣") == "O" and classify_pin_char("5") == "D"


def test_pin_dfa_rejects_symbol_outside_alphabet():
    with pytest.raises(AutomatonError):
        build_pin_dfa().step("q0", "X")


def test_pin_matches_reference_exhaustively():
    dfa, chars = build_pin_dfa(), ["0", "9", "x", " ", "-"]
    for n in range(7):
        for tup in product(chars, repeat=n):
            s = "".join(tup)
            assert validate_pin(s, dfa).accepted == ref_pin(s), s


# -------------------------------------------------------------- card lock ---
@pytest.mark.parametrize("events", C.CARD_REPORT_USABLE + C.CARD_EXTRA_USABLE)
def test_card_usable(events):
    assert card_usable(events)


@pytest.mark.parametrize("events", C.CARD_REPORT_LOCKED + C.CARD_EXTRA_LOCKED)
def test_card_locked(events):
    assert not card_usable(events)


def test_example_from_report_state_sequence():
    assert run_card_events("WWCWWW") == ["s0", "s1", "s2", "s0", "s1", "s2", "LOCK"]


def test_card_lock_transition_table():
    assert build_card_lock_dfa().delta == C.CARD_TABLE_FROM_RULES


def test_lock_is_absorbing_for_both_events():
    dfa = build_card_lock_dfa()
    assert dfa.step("LOCK", "C") == "LOCK" and dfa.step("LOCK", "W") == "LOCK"


def test_card_object_reports_state_after_every_event_and_needs_reset():
    card = CardLock()
    for e in "WWW":
        card.apply(e)
    assert card.locked and [h["To"] for h in card.history] == ["s1", "s2", "LOCK"]
    card.apply("C")
    assert card.locked                       # a correct PIN does not unlock
    card.reset()
    assert not card.locked and card.state == "s0"


def test_card_rejects_unknown_event():
    with pytest.raises(AutomatonError):
        CardLock().apply("X")


def test_card_matches_independent_rule_exhaustively():
    for n in range(11):
        for tup in product("CW", repeat=n):
            s = "".join(tup)
            assert run_card_events(s)[-1] == ref_card_state(s), s
