from parsers.operator_mapper import OperatorMapper
from database.models import OperatorMapping


def seed_mappings(session):
    mappings = [
        OperatorMapping(pattern="OQ", app_name="OQ Generic", priority=5, is_active=True),
        OperatorMapping(pattern="OQ P2P", app_name="OQ P2P", priority=8, is_active=True),
        OperatorMapping(pattern="PAYNET", app_name="Paynet", priority=2, is_active=True),
        OperatorMapping(pattern="PAY", app_name="CatchAll Pay", priority=1, is_active=True),
        OperatorMapping(pattern="REGEX ONLY", app_name="RegexOnly", priority=1, is_active=False),  # inactive ignored
    ]
    session.add_all(mappings)
    session.commit()


def test_operator_mapper_exact_match_wins(db_session):
    seed_mappings(db_session)
    mapper = OperatorMapper(db_session)

    result = mapper.map_operator("OQ P2P>TASHKENT")
    # Exact pattern "OQ P2P" should win even though "OQ" is higher priority
    assert result == "OQ P2P"


def test_operator_mapper_highest_priority_substring(db_session):
    seed_mappings(db_session)
    mapper = OperatorMapper(db_session)

    result = mapper.map_operator("PAYNET HUM2UZC")
    # Should pick PAYNET over generic PAY because of higher priority
    assert result == "Paynet"


def test_operator_mapper_returns_none_for_inactive_or_no_match(db_session):
    seed_mappings(db_session)
    mapper = OperatorMapper(db_session)

    result = mapper.map_operator("REGEX ONLY")
    assert result is None

    result_unknown = mapper.map_operator("UNKNOWN OPERATOR")
    assert result_unknown is None
