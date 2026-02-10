CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    full_name TEXT,
    hashed_password TEXT,

    age INTEGER,
    gender TEXT,
    energy_level TEXT,

    budget_min INTEGER,
    budget_max INTEGER,

    preferences_json TEXT, -- user-selected tags

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS long_memory (
    user_id INTEGER PRIMARY KEY,
    data_json TEXT,          -- JSON: preferences with scores, spending style, favorite categories
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS short_memory (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER,
    data_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,           -- user | assistant
    content TEXT,
    itinerary_data_json TEXT, -- attached itinerary (if agent responded with a plan)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    payload_json TEXT,           -- The entire itinerary structure
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preference_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    preference TEXT,
    score INTEGER DEFAULT 1,
    signal_type TEXT, -- explicit_ask | itinerary_click | restaurant_added | plan_modified
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
