# NAO Robot Integration — Documentation

## 1. Connectivity

### Why SSH instead of NAOqi SDK?

The NAOqi SDK uses port `9559` with a **binary qi protocol** that is incompatible with Python 3 on Windows. Rather than running NAOqi on the PC, all commands are executed **inside the robot itself** using NAO's own Python 2.7 + naoqi installation via SSH.

```
Windows PC (Python 3)
        │
        │  SSH (port 22) via paramiko
        ▼
NAO Robot (Python 2.7 + naoqi)
  → ALTextToSpeech
  → ALSpeechRecognition
  → ALAudioPlayer
  → ALBehaviorManager
```

### Connection details

| Parameter | Value |
|-----------|-------|
| IP | `172.16.10.47` |
| SSH port | `22` |
| NAOqi port | `9559` (used internally by the robot only) |
| User | `nao` |
| Password | `nao` |

---

## 2. NaoSpeaker class (`Isolation_Game_Individual_Tiles.py`)

Central class that wraps all robot communication. Instantiated once globally at startup:

```python
nao = NaoSpeaker(NAO_IP, NAO_USER, NAO_PASSWORD)
```

If the robot is unreachable, `nao.available = False` and every method silently does nothing — **the game always runs**, with or without the robot.

---

## 3. Functions

### 3.1 `_connect()`

Called once at startup. Opens a test SSH connection to verify the robot is reachable and sets `self.available = True` on success.

---

### 3.2 `say(text)` — non-blocking TTS

```python
nao.say("Thinking")
```

Launches `_say_ssh` in a **background daemon thread**. Returns immediately — the game loop is not blocked. Used for announcements that run in parallel with computation (e.g. NAO says "Thinking" while Alpha-Beta runs).

---

### 3.3 `say_blocking(text)` — blocking TTS

```python
nao.say_blocking("I move to alpha three. I block bravo two.")
```

Calls `_say_ssh` with `wait=True` — the calling thread **blocks until NAO finishes speaking**. Used when the board must not update before NAO announces a move.

---

### 3.4 `_say_ssh(text, wait=False)` — internal

Connects via SSH and runs:

```python
python -c "
import naoqi
tts = naoqi.ALProxy('ALTextToSpeech', '127.0.0.1', 9559)
tts.setLanguage('English')
tts.say('<text>')
"
```

If `wait=True`, it calls `stdout.channel.recv_exit_status()` to block until the command finishes on the robot.

---

### 3.5 `celebrate()` — non-blocking celebration

```python
nao.celebrate()
```

Launches `_celebrate_ssh` in a background thread. Called when the AI wins.

---

### 3.6 `_celebrate_ssh()` — internal

Does three things in sequence on the robot:

1. **Uploads** `dance-moves.mp3` from the PC to `/home/nao/dance-moves.mp3` via SFTP.
2. **Speaks** `"I won! You have no more moves."` via `ALTextToSpeech`.
3. **Plays** the MP3 from NAO's own speakers via `ALAudioPlayer.post.playFile` (non-blocking on the robot side so audio and dance overlap).
4. **Dances** with `ALBehaviorManager.runBehavior('animations/Stand/Gestures/Enthusiastic_4')`.

---

### 3.7 `listen(vocabulario, timeout_sec=15)` — voice recognition

```python
result = nao.listen(["alpha one", "bravo two", ...], timeout_sec=15)
```

The most complex function. Because multi-line Python scripts cannot be passed reliably via `python -c` (shell escaping corrupts newlines), the script is **written as a temp file on the robot** via SFTP and then executed directly.

**Script flow on the robot (`/tmp/nao_asr.py`):**

```python
asr.setLanguage('English')
asr.unsubscribe('IsolationASR')   # clean up any previous session

asr.pause(True)                    # required before changing vocabulary
asr.setVocabulary(vocab, True)     # True = word spotting mode
asr.subscribe('IsolationASR')
asr.pause(False)                   # resume listening

mem.insertData('WordRecognized', [])  # clear stale results
time.sleep(1.0)                       # let ASR initialize

# Poll ALMemory until a word is recognized or timeout
while time.time() - t0 < timeout_sec:
    val = mem.getData('WordRecognized')
    if val and val[1] > 0.25:         # confidence threshold
        resultado = val[0]
        break
    time.sleep(0.3)

asr.pause(True)
asr.unsubscribe('IsolationASR')
asr.pause(False)
```

**Key design decisions:**

| Decision | Reason |
|----------|--------|
| `asr.pause(True)` before `setVocabulary` | NAOqi requires the engine to be paused before vocabulary changes; skipping this causes a `RuntimeError` |
| `setVocabulary(vocab, True)` — word spotting ON | Allows recognition of multi-word phrases like "alpha three" and is more flexible than exact matching |
| `mem.insertData('WordRecognized', [])` | Clears any word left in memory from a previous recognition session |
| `time.sleep(1.0)` after subscribe | Gives the ASR engine time to fully initialize before polling starts |
| Confidence threshold `> 0.25` | Lower values (e.g. 0.35) caused too many missed recognitions in practice |
| Write to `/tmp/nao_asr.py` via SFTP | `python -c` with a multi-line script escaped via `json.dumps` produces literal `\n` in the shell — syntax error on Python 2.7 |

**Result parsing:**

Word spotting returns results with context markers: `"<...> alpha three <...>"`. The function strips these by checking which vocabulary word is **contained within** the raw result string:

```python
for v in vocabulario:
    if v in raw.lower():
        return v
```

---

### 3.8 `ask_and_confirm(question, vocabulario, mapeo, max_attempts=3)`

Full conversational loop:

```
NAO asks question
    → listen() for vocabulary word
    → map recognized word to board position ("alpha three" → "A3")
    → NAO says "I heard A3. Is that correct?"
    → listen() for ["yes", "no"]
        if "yes" → return position
        if "no"  → repeat from start
        if None  → repeat from start
    (up to max_attempts times)
```

Used in `human_voice_move()` for both the move position and the cell to block.

---

## 4. Voice flow in the game

When it is the human's turn, `human_voice_move()` runs in a background thread:

```
1. Get valid moves for the human player
   └─ if none → AI wins, nao.celebrate()

2. ask_and_confirm("Which position do you want to move to?")
   └─ validate result is in valid_moves
   └─ if invalid → NAO says valid options, retry
   └─ apply move to board

3. ask_and_confirm("Which cell do you want to block?")
   └─ validate result is in removable_cells
   └─ if invalid → NAO asks again
   └─ remove cell from board

4. end_human_turn()
```

Mouse clicks remain active as a **fallback** — if voice returns `None` after all attempts, NAO says `"Voice failed. Use the mouse to make your move."` and `voice_thinking` is set to `False`, re-enabling clicks.

---

## 5. NAO speech in the AI turn

```python
nao.say("Thinking")          # non-blocking, plays while Alpha-Beta runs
...
nao.say_blocking(message)    # blocking, board updates only after NAO finishes
```

Position names are converted to NATO phonetic form for natural speech:

```python
cell_spoken((2, 0))  →  "alpha three"   # col A = alpha, row 3 = three
cell_spoken((1, 3))  →  "delta two"     # col D = delta, row 2 = two
```

---

## 6. Dependency

```
pip install paramiko
```

`paramiko` is the only external dependency for NAO connectivity. `pygame` handles the game interface.
