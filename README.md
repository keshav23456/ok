# LiveKit Agent with Filler Word Filtering

## Overview

This is an enhanced version of the basic LiveKit voice agent that intelligently filters filler words (like "umm", "hmm", "uh", etc.) to prevent them from interrupting the agent while it's speaking. The filler words are stored in a SQLite database and can be managed dynamically without restarting the agent.

---

## What Changed

### 1. **Code Organization - Modular Structure**
- **New file: `filler_utils.py`** - Utility module containing all filler word filtering logic
  - Database setup and models
  - Filler word management functions
  - Text filtering logic
- **Modified: `basic_agent.py`** - Main agent code now imports from `filler_utils.py`
  - Cleaner and more maintainable
  - Separated concerns (agent logic vs. filtering logic)

### 2. **New Imports (in filler_utils.py)**
- `sqlalchemy` - For database operations
- `sqlalchemy.ext.declarative` - For ORM model definitions
- `sqlalchemy.orm` - For session management

### 3. **Database Setup (in filler_utils.py)**
- **SQLite Database**: `filler_words.db` (auto-created on first run)
- **SQLAlchemy Model**: `FillerWord` class with `id` and `word` columns
- **Table**: `filler_words` stores all filler words

### 4. **New Functions (in filler_utils.py)**
- `initialize_filler_words()` - Populates database with default filler words on first run
- `get_filler_words()` - Fetches all filler words from database
- `is_only_filler_words(text: str)` - Checks if transcribed text contains only filler words

### 5. **Modified Agent Logic (in basic_agent.py)**
- **Override `stt_node()` method** - Intercepts speech-to-text events
- **Filler word filtering** - Filters out both interim and final transcripts containing only filler words
- **Imports from filler_utils** - Uses `is_only_filler_words()` function
- **Dynamic reload** - Fetches latest filler words from database on each check

### 6. **STT Provider Change**
- **Changed from**: Deepgram (`stt="deepgram/nova-3"`)
- **Changed to**: Azure Speech (`stt=azure.STT(language=["en-US", "hi-IN"])`)
- **Multilingual support**: English and Hindi language detection

### 7. **Session Configuration Updates**
- `min_interruption_words=1` - Requires at least 1 word to trigger interruption
- `false_interruption_timeout=2.0` - Increased timeout for false interruption detection
- `allow_interruptions=True` - Enabled (filler words filtered at STT level)

### 8. **New Management Script**
- `manage_filler_words.py` - Interactive CLI tool to add/remove/view filler words
- Imports `FillerWord` and `Base` from `filler_utils.py`

---

## What Works

### ✅ **Verified Features**

1. **Filler Word Detection**
   - Agent continues speaking when user says only filler words ("umm", "hmm", "uh", etc.)
   - Real words properly interrupt the agent
   - Works with both English and Hindi filler words

2. **Database Management**
   - SQLite database auto-creates on first run
   - Default filler words loaded automatically
   - Words can be added/removed using `manage_filler_words.py`

3. **Multilingual STT**
   - Azure Speech recognizes both English (en-US) and Hindi (hi-IN)
   - Automatic language detection between the two languages

4. **Dynamic Updates**
   - Filler words are reloaded from database on each speech check
   - Changes take effect without agent restart

5. **Agent Core Functions**
   - LLM conversation flow works normally
   - Function tools (e.g., `lookup_weather`) work as expected
   - Turn detection and VAD function properly

6. **Modular Code Structure**
   - Clean separation between agent logic and filtering logic
   - `filler_utils.py` can be imported by other scripts
   - Easier to maintain and extend

---

## Known Issues

### ⚠️ **Potential Edge Cases**

1. **Database Query Performance**
   - Database is queried for every speech event (interim + final transcripts)
   - May cause slight latency with very large filler word lists (>1000 words)
   - **Mitigation**: Keep filler word list reasonably sized (<100 words)

2. **Mixed Speech Handling**
   - If user says filler word + real word together (e.g., "umm hello"), it will interrupt
   - Current logic only filters when ALL words are fillers
   - This is **intentional behavior** to avoid missing real speech

3. **Punctuation Sensitivity**
   - Current implementation removes basic punctuation (. , ? !)
   - Other punctuation might affect word matching
   - Filler words stored without punctuation work best

4. **Case Sensitivity**
   - All comparisons are case-insensitive (converted to lowercase)
   - Database stores words in lowercase
   - Should not cause issues in practice

5. **Database Locking**
   - SQLite may lock during concurrent writes
   - Not an issue for single-agent deployments
   - For multi-agent deployments, consider PostgreSQL

6. **No Duration Filtering**
   - Filtering is based on transcribed text, not audio duration
   - Very short sounds (<0.1s) may not be detected by VAD or transcribed by STT
   - This is generally good behavior as such sounds are usually noise

---

## Steps to Test

### **1. Install Dependencies**

```bash
uv add sqlalchemy
```

### **2. Configure Environment Variables**

Create/edit `.env` file with:

```env
# LiveKit credentials
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Azure Speech credentials
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=centralindia  # or your region
```

### **3. Start the Agent**

```bash
uv run python basic_agent.py console
```

On first run, it will:
- Create `filler_words.db` in the project directory
- Initialize with default filler words (updated to 18 words)
- Log: `Initialized database with 18 filler words`

### **4. Test Filler Word Filtering**

**Test Case 1: Filler words should NOT interrupt**
1. Let the agent speak
2. While agent is speaking, say: "umm"
3. ✅ **Expected**: Agent continues speaking
4. Check logs for: `🛑 Detected only filler words: 'umm' - will be filtered`

**Test Case 2: Real words should interrupt**
1. Let the agent speak
2. While agent is speaking, say: "hello"
3. ✅ **Expected**: Agent stops and listens to you
4. Agent responds to your real speech

**Test Case 3: Mixed speech should interrupt**
1. Let the agent speak
2. While agent is speaking, say: "umm hello"
3. ✅ **Expected**: Agent stops (because "hello" is a real word)

**Test Case 4: Hindi filler words**
1. Let the agent speak
2. While agent is speaking, say: "haan" or "acha"
3. ✅ **Expected**: Agent continues speaking

**Test Case 5: Compound filler words**
1. Let the agent speak
2. While agent is speaking, say: "uh-huh"
3. ✅ **Expected**: Agent continues speaking

### **5. Manage Filler Words**

Run the management script:

```bash
uv run python manage_filler_words.py
```

**Test adding a word:**
1. Choose option 2 (Add a single filler word)
2. Enter: "yeah"
3. ✅ **Expected**: `Successfully added 'yeah' to the database!`
4. Test that "yeah" now filters correctly during agent speech

**Test viewing words:**
1. Choose option 1 (View all filler words)
2. ✅ **Expected**: List of all current filler words

**Test removing a word:**
1. Choose option 4 (Remove a filler word)
2. Enter: "ok"
3. ✅ **Expected**: `Successfully removed 'ok' from the database!`
4. Test that "ok" now interrupts the agent

---

## Environment Details

### **Python Version**
- **Required**: Python ≥ 3.9
- **Tested**: Python 3.12, 3.13

### **Dependencies**

```toml
dependencies = [
    "livekit-agents[azure,silero,turn-detector]~=1.2",
    "python-dotenv",
    "numpy",
    "sounddevice",
    "sqlalchemy>=2.0.44",
]
```

### **Key Libraries**
- `livekit-agents` - LiveKit voice agent framework
- `livekit-plugins-azure` - Azure Speech STT/TTS
- `livekit-plugins-silero` - VAD (Voice Activity Detection)
- `livekit-plugins-turn-detector` - Multilingual turn detection
- `sqlalchemy` - Database ORM
- `python-dotenv` - Environment variable management

### **Configuration Files**

**`.env`** (required):
```env
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=centralindia
```

**`filler_words.db`** (auto-created):
- SQLite database file
- Created automatically on first run
- Located in project root directory

### **File Structure**

```
gen_ai/
├── .env                      # Environment variables
├── basic_agent.py            # Main agent code (imports from filler_utils)
├── filler_utils.py           # Filler word filtering utilities (NEW)
├── manage_filler_words.py    # Database management CLI
├── filler_words.db           # SQLite database (auto-created)
├── pyproject.toml            # Project dependencies
└── README.md                 # This file
```

---

## Module Documentation

### **filler_utils.py**

Utility module for filler word filtering and database management.

**Classes:**
- `FillerWord(Base)` - SQLAlchemy model for storing filler words

**Functions:**
- `initialize_filler_words()` - Initialize database with default words
- `get_filler_words() -> set` - Fetch all filler words from database
- `is_only_filler_words(text: str) -> bool` - Check if text contains only filler words

**Usage Example:**
```python
from filler_utils import is_only_filler_words, get_filler_words

# Check if text is only filler words
if is_only_filler_words("umm"):
    print("This is a filler word!")

# Get current filler words
words = get_filler_words()
print(f"Current filler words: {words}")
```

### **manage_filler_words.py**

Interactive command-line tool for managing filler words database.

**Features:**
1. View all filler words
2. Add a single filler word
3. Add multiple filler words (comma-separated)
4. Remove a filler word
5. Clear all filler words
6. Exit

**Usage:**
```bash
uv run python manage_filler_words.py
```

---

## Quick Reference

### **Default Filler Words**
English: umm, uh, um, so, hmm, hm, ah, er, erm, ok, ahhh, hmmm, eh, ehh, uhh, uh-huh

Hindi: haan, acha

### **Running Commands**

```bash
# Start agent
uv run python basic_agent.py dev
# or
uv run python basic_agent.py console

# Manage filler words
uv run python manage_filler_words.py

# Install dependencies
uv add sqlalchemy

# Sync all dependencies
uv sync
```

---

## Comparison to Original `basic_agent.py`

### **Original Code**
- Used Deepgram STT
- No filler word filtering
- Static configuration
- English only
- All code in single file

### **Enhanced Code**
- Uses Azure Speech STT
- Dynamic filler word filtering via SQLite database
- Runtime-configurable filler words
- English + Hindi support
- Custom `stt_node()` override for filtering
- Management CLI tool included
- Modular structure with `filler_utils.py` utility module

---

## License

This project uses LiveKit Agents SDK. See LiveKit's license for details.
