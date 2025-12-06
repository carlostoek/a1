# Testing Infrastructure

This project includes a comprehensive testing suite for the gamification and referral modules using pytest.

## 🧪 Running Tests

### Quick Test Run
To run the test script that executes all gamification tests:
```bash
python run_tests.py
```

### Specific Test Execution
To run only the gamification tests:
```bash
python -m pytest tests/test_gamification.py -v
```

To run all tests in the project:
```bash
python -m pytest -v
```

## 📁 Test Structure

- `tests/` - Main test directory
- `tests/conftest.py` - Test fixtures for mock bot, database session, and services
- `tests/test_gamification.py` - Tests for gamification and referral functionality

## 🧩 Test Fixtures

- `mock_bot`: Mock aiogram.Bot object that intercepts `send_message` and `ban_chat_member` calls
- `db_session`: SQLite in-memory database session that creates all tables before each test and closes after
- `services`: Real ServiceContainer with injected mock_bot and test db_session

## 🧪 Test Coverage

The test suite includes 4 comprehensive test cases:

1. **test_points_flow**: Tests user gaining 100 points and achieving appropriate rank
2. **test_referral_success**: Tests happy path for referral system (referrer +100 pts, referred +50 pts)
3. **test_referral_fraud**: Tests anti-fraud scenarios (self-referral prevention, existing user referral)
4. **test_daily_cooldown**: Tests daily reward cooldown mechanism

## 🛠️ Dependencies

Required packages (already in requirements.txt):
- pytest
- pytest-asyncio
- aiosqlite

## 📝 Configuration

The testing suite uses the following configuration files:
- `pytest.ini` - pytest configuration
- `pyproject.toml` - Additional pytest configuration

## 🚀 Usage in Development

This testing infrastructure provides:
- Volatile in-memory databases for each test
- Complete test isolation
- Fast execution
- Comprehensive coverage of gamification logic