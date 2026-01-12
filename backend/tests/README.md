# Parser & Mapping Tests

## What is covered
- RegexParser: Humo notification, SMS inline, semicolon format, noisy text, missing fields.
- OperatorMapper: deterministic resolution (exact vs substring), priority handling, no-match cases.

## Running tests
```bash
cd backend
pytest
```

## Adding new samples
1. Copy a real (anonymized) receipt snippet into `test_regex_parser.py`.
2. Add an assertion for every parsed field you expect (`amount`, `operator_raw`, `card_last_4`, `transaction_date`, `parsing_method`, `parsing_confidence` if present).
3. For mapping collisions, add new OperatorMapping rows in `test_operator_mapper.py` and assert the chosen `app_name`.
4. Keep samples minimal but representative (include separators, different date formats, and noisy prefixes/suffixes).
