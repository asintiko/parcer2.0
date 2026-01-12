-- Normalize check IDs to sequential order (1, 2, 3...)
-- Based on datetime from oldest to newest

-- Step 1: Create temporary table with new sequential IDs
CREATE TEMP TABLE checks_normalized AS
SELECT
    ROW_NUMBER() OVER (ORDER BY datetime ASC) as new_id,
    check_id,
    datetime,
    weekday,
    date_display,
    time_display,
    operator,
    app,
    amount,
    balance,
    card_last4,
    is_p2p,
    transaction_type,
    currency,
    source,
    raw_text,
    added_via,
    is_duplicate,
    duplicate_of_id,
    created_at,
    updated_at,
    metadata,
    source_chat_id,
    source_message_id,
    notify_message_id,
    fingerprint,
    source_bot_username,
    source_bot_title,
    source_app
FROM checks
ORDER BY datetime ASC;

-- Step 2: Truncate original table (delete all data but keep structure)
TRUNCATE TABLE checks RESTART IDENTITY CASCADE;

-- Step 3: Insert data back with new sequential IDs
INSERT INTO checks (
    id, check_id, datetime, weekday, date_display, time_display,
    operator, app, amount, balance, card_last4, is_p2p,
    transaction_type, currency, source, raw_text, added_via,
    is_duplicate, duplicate_of_id, created_at, updated_at,
    metadata, source_chat_id, source_message_id, notify_message_id,
    fingerprint, source_bot_username, source_bot_title, source_app
)
SELECT
    new_id as id, check_id, datetime, weekday, date_display, time_display,
    operator, app, amount, balance, card_last4, is_p2p,
    transaction_type, currency, source, raw_text, added_via,
    is_duplicate, duplicate_of_id, created_at, updated_at,
    metadata, source_chat_id, source_message_id, notify_message_id,
    fingerprint, source_bot_username, source_bot_title, source_app
FROM checks_normalized
ORDER BY new_id;

-- Step 4: Update sequence to continue from max ID + 1
SELECT setval('checks_id_seq', (SELECT MAX(id) FROM checks) + 1, false);

-- Verify results
SELECT COUNT(*) as total_records FROM checks;
SELECT MIN(id) as min_id, MAX(id) as max_id FROM checks;
SELECT id, datetime FROM checks ORDER BY id LIMIT 5;
