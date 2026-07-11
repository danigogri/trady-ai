from decimal import Decimal

import pytest

from trady_ai.core.persistence import (
    append_event,
    count_events,
    get_events,
    get_max_seq,
    init_event_store,
    reset_event_store,
)

SAMPLE_EVENT = {
    "event_id": "0xabc:2026-07-08T12:00:00Z:tick",
    "market_id": "0xabc",
    "price": "0.65",
    "volume": "1500.00",
    "timestamp": "2026-07-08T12:00:00Z",
    "event_type": "tick",
    "source": "polymarket",
    "raw_payload": '{"market_id": "0xabc", "price": "0.65"}',
}


class TestAppendEvent:
    def test_append_event_returns_seq(self, tmp_event_store_db):
        """Appending a new event returns its seq (1 for first insert)."""
        seq = append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert seq == 1, "First insert should return seq=1"

    def test_append_event_inserts_row(self, tmp_event_store_db):
        """After append, the store has 1 row with correct values."""
        append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert count_events(tmp_event_store_db) == 1

    def test_append_event_dedup_returns_none(self, tmp_event_store_db):
        """Same event_id appended twice → second returns None, store still has 1."""
        seq1 = append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert seq1 == 1

        seq2 = append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert seq2 is None, "Duplicate should return None"

        assert count_events(tmp_event_store_db) == 1

    def test_append_event_different_ids_both_inserted(self, tmp_event_store_db):
        """Different event_ids → both inserted with sequential seq."""
        e1 = dict(SAMPLE_EVENT, event_id="id:1")
        e2 = dict(SAMPLE_EVENT, event_id="id:2")

        assert append_event(tmp_event_store_db, e1) == 1
        assert append_event(tmp_event_store_db, e2) == 2
        assert count_events(tmp_event_store_db) == 2

    def test_append_event_missing_key_raises(self, tmp_event_store_db):
        """Missing required key (e.g. market_id) raises KeyError."""
        bad = dict(SAMPLE_EVENT)
        del bad["market_id"]
        with pytest.raises(KeyError):
            append_event(tmp_event_store_db, bad)


class TestGetEvents:
    def test_get_events_returns_market_input_list(self, tmp_event_store_db):
        """get_events returns MarketInput objects ordered by seq ASC."""
        e1 = dict(SAMPLE_EVENT, event_id="id:1", market_id="m1", price="1.00",
                  volume="100", timestamp="2026-01-01T00:00:00Z")
        e2 = dict(SAMPLE_EVENT, event_id="id:2", market_id="m2", price="2.00",
                  volume="200", timestamp="2026-01-02T00:00:00Z")
        append_event(tmp_event_store_db, e1)
        append_event(tmp_event_store_db, e2)

        results = get_events(tmp_event_store_db)
        assert len(results) == 2
        assert results[0].market_id == "m1"
        assert results[1].market_id == "m2"
        assert results[0].price == Decimal("1.00")
        assert results[1].price == Decimal("2.00")
        assert results[0].source == "polymarket"

    def test_get_events_empty_store(self, tmp_event_store_db):
        """Empty store → empty list."""
        assert get_events(tmp_event_store_db) == []

    def test_get_events_with_since_seq(self, tmp_event_store_db):
        """since_seq filters out events with seq <= since_seq."""
        for i in range(1, 4):
            e = dict(SAMPLE_EVENT, event_id=f"id:{i}", market_id=f"m{i}",
                     price=f"{i}.00", volume="100", timestamp="2026-01-01T00:00:00Z")
            append_event(tmp_event_store_db, e)

        results = get_events(tmp_event_store_db, since_seq=1)
        assert len(results) == 2
        assert results[0].market_id == "m2"

    def test_get_events_with_limit(self, tmp_event_store_db):
        """limit caps the number of returned events."""
        for i in range(1, 6):
            e = dict(SAMPLE_EVENT, event_id=f"id:{i}", market_id=f"m{i}",
                     price=f"{i}.00", volume="100", timestamp="2026-01-01T00:00:00Z")
            append_event(tmp_event_store_db, e)

        results = get_events(tmp_event_store_db, limit=2)
        assert len(results) == 2

    def test_get_events_invalid_since_seq(self, tmp_event_store_db):
        """since_seq < 0 raises ValueError."""
        with pytest.raises(ValueError, match="since_seq must be >= 0"):
            get_events(tmp_event_store_db, since_seq=-1)

    def test_get_events_invalid_limit(self, tmp_event_store_db):
        """limit <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="limit must be > 0"):
            get_events(tmp_event_store_db, limit=0)


class TestGetMaxSeq:
    def test_get_max_seq_on_empty_store(self, tmp_event_store_db):
        """Empty store → 0."""
        assert get_max_seq(tmp_event_store_db) == 0

    def test_get_max_seq_after_inserts(self, tmp_event_store_db):
        """After 3 inserts, max seq is 3."""
        for i in range(1, 4):
            e = dict(SAMPLE_EVENT, event_id=f"id:{i}")
            append_event(tmp_event_store_db, e)
        assert get_max_seq(tmp_event_store_db) == 3


class TestCountEvents:
    def test_count_events_empty(self, tmp_event_store_db):
        """Empty store → 0."""
        assert count_events(tmp_event_store_db) == 0

    def test_count_events_after_inserts(self, tmp_event_store_db):
        """After 2 inserts, count is 2."""
        append_event(tmp_event_store_db, dict(SAMPLE_EVENT, event_id="id:1"))
        append_event(tmp_event_store_db, dict(SAMPLE_EVENT, event_id="id:2"))
        assert count_events(tmp_event_store_db) == 2


class TestResetEventStore:
    def test_reset_clears_all_data(self, tmp_event_store_db):
        """reset drops data and recreates table."""
        append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert count_events(tmp_event_store_db) == 1

        reset_event_store(tmp_event_store_db)
        assert count_events(tmp_event_store_db) == 0

    def test_reset_is_idempotent(self, tmp_event_store_db):
        """reset on empty store does not error."""
        reset_event_store(tmp_event_store_db)
        assert count_events(tmp_event_store_db) == 0


class TestInitEventStore:
    def test_init_event_store_idempotent(self, tmp_event_store_db):
        """Calling init_event_store twice does not error."""
        # First init is done by the fixture
        init_event_store(tmp_event_store_db)  # Second call
        # Table should still work
        append_event(tmp_event_store_db, SAMPLE_EVENT)
        assert count_events(tmp_event_store_db) == 1
