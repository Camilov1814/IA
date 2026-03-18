"""
test_nao.py - Connection, speech, and language understanding test for NAO via SSH.

Port 9559 uses the qi binary protocol (not HTTP).
The solution for Windows Python 3 is SSH: connect to the robot
and execute commands using its own built-in Python 2.7 + naoqi.

Includes voice understanding test:
  - NAO asks the player which position to move to
  - Listens for the response (ALSpeechRecognition)
  - Confirms the understood position by voice
  - Asks which cell to block
  - Listens and confirms

Dependency:
    pip install paramiko
"""

import os
import socket
import paramiko
import time

NAO_IP       = "172.16.10.47"
NAO_USER     = "nao"
NAO_PASSWORD = "nao"


# ─── STEP 1: Verify network connectivity ─────────────────────────────────────
def test_puerto(ip, port, nombre):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    ok = sock.connect_ex((ip, port)) == 0
    sock.close()
    estado = "[OK]   " if ok else "[FAIL] "
    print(f"  {estado} Port {port} ({nombre})")
    return ok


# ─── STEP 2: Connect via SSH and speak ───────────────────────────────────────
def nao_celebrate_ssh(ip, user, password):
    """
    1. Uploads dance-moves.mp3 to the robot via SFTP.
    2. NAO speaks, plays the audio from its own speakers
       and executes the celebration animation at the same time.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mp3_local  = os.path.join(script_dir, "dance-moves.mp3")
    mp3_remoto = "/home/nao/dance-moves.mp3"

    cmd = (
        "python -c \""
        "import naoqi; "
        "tts = naoqi.ALProxy('ALTextToSpeech', '127.0.0.1', 9559); "
        "ap  = naoqi.ALProxy('ALAudioPlayer',  '127.0.0.1', 9559); "
        "bm  = naoqi.ALProxy('ALBehaviorManager', '127.0.0.1', 9559); "
        "tts.setLanguage('English'); "
        "tts.say('I won!'); "
        "ap.post.playFile('/home/nao/dance-moves.mp3'); "
        "bm.runBehavior('animations/Stand/Gestures/Enthusiastic_5')"
        "\""
    )
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password, timeout=5,
                    allow_agent=False, look_for_keys=False)

        if os.path.exists(mp3_local):
            sftp = ssh.open_sftp()
            sftp.put(mp3_local, mp3_remoto)
            sftp.close()
            print(f"  [OK]  dance-moves.mp3 uploaded to robot.")
        else:
            print(f"  [WARN] {mp3_local} not found, only the dance will run.")

        _, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        errores = stderr.read().decode().strip()
        ssh.close()
        if errores:
            print(f"  [WARN] Stderr: {errores}")
        else:
            print(f"  [OK]  Celebration complete.")
        return True
    except Exception as e:
        print(f"  [FAIL] Error in celebration: {e}")
        return False


def nao_say_ssh(ip, user, password, text):
    """
    Connects to the robot via SSH and executes ALTextToSpeech.say
    using the NAO's own Python 2.7 + naoqi.
    """
    cmd = (
        f"python -c \""
        f"import naoqi; "
        f"tts = naoqi.ALProxy('ALTextToSpeech', '127.0.0.1', 9559); "
        f"tts.setLanguage('English'); "
        f"tts.say('{text}')"
        f"\""
    )
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password, timeout=5,
                        allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        errores = stderr.read().decode().strip()
        ssh.close()
        if errores:
            print(f"  [WARN] Stderr: {errores}")
        else:
            print(f"  [OK]  NAO said: '{text}'")
        return True
    except paramiko.AuthenticationException:
        print(f"  [FAIL] Authentication failed. Check user/password.")
        return False
    except Exception as e:
        print(f"  [FAIL] SSH error: {e}")
        return False


# ─── STEP 3: Voice recognition ───────────────────────────────────────────────

# Board position vocabulary for 5x5 grid (A1..E5)
POSICIONES_VALIDAS = []
for col_letra in ["A", "B", "C", "D", "E"]:
    for fila_num in ["1", "2", "3", "4", "5"]:
        POSICIONES_VALIDAS.append(f"{col_letra}{fila_num}")

# Confirmation vocabulary
CONFIRMACION = ["yes", "no"]

# Vocabulary mapping so NAO understands spoken positions in English.
# Using NATO phonetic alphabet for letters — much easier to recognize than single letters.
# Positions are spoken as "alpha one", "bravo two", "charlie three", etc.
NUMEROS_TEXTO    = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five"}
LETRAS_FONETICAS = {"A": "alpha", "B": "bravo", "C": "charlie", "D": "delta", "E": "echo"}

VOCAB_POSICIONES_HABLADAS = []
for col_letra in ["A", "B", "C", "D", "E"]:
    for fila_num in ["1", "2", "3", "4", "5"]:
        hablado = f"{LETRAS_FONETICAS[col_letra]} {NUMEROS_TEXTO[fila_num]}"
        VOCAB_POSICIONES_HABLADAS.append(hablado)

# Mapping from spoken text to board position
HABLADO_A_POSICION = {}
idx = 0
for col_letra in ["A", "B", "C", "D", "E"]:
    for fila_num in ["1", "2", "3", "4", "5"]:
        hablado = VOCAB_POSICIONES_HABLADAS[idx]
        HABLADO_A_POSICION[hablado] = f"{col_letra}{fila_num}"
        idx += 1


def nao_listen_ssh(ip, user, password, vocabulario, timeout_sec=15):
    """
    Uses NAO's ALSpeechRecognition to listen for a word from the given vocabulary.
    Returns the recognized word or None if nothing was understood.

    Writes the script as a temp file on the NAO via SFTP to avoid
    shell escaping issues with python -c.
    """
    vocab_str = str(vocabulario)

    script = (
        "import naoqi\n"
        "import time\n"
        "\n"
        "IP = '127.0.0.1'\n"
        "PORT = 9559\n"
        "\n"
        "asr = naoqi.ALProxy('ALSpeechRecognition', IP, PORT)\n"
        "mem = naoqi.ALProxy('ALMemory', IP, PORT)\n"
        "\n"
        "asr.setLanguage('English')\n"
        "\n"
        "try:\n"
        "    asr.unsubscribe('TestNaoASR')\n"
        "except:\n"
        "    pass\n"
        "\n"
        "# Pause the ASR engine before changing vocabulary (required by NAOqi)\n"
        "asr.pause(True)\n"
        f"asr.setVocabulary({vocab_str}, True)\n"
        "asr.subscribe('TestNaoASR')\n"
        "asr.pause(False)\n"
        "\n"
        "mem.insertData('WordRecognized', [])\n"
        "time.sleep(1.0)\n"
        "\n"
        "resultado = None\n"
        "t0 = time.time()\n"
        f"while time.time() - t0 < {timeout_sec}:\n"
        "    val = mem.getData('WordRecognized')\n"
        "    if val and len(val) >= 2 and val[1] > 0.25:\n"
        "        resultado = val[0]\n"
        "        break\n"
        "    time.sleep(0.3)\n"
        "\n"
        "asr.pause(True)\n"
        "asr.unsubscribe('TestNaoASR')\n"
        "asr.pause(False)\n"
        "\n"
        "if resultado:\n"
        "    print('RECOGNIZED:' + resultado)\n"
        "else:\n"
        "    print('RECOGNIZED:NONE')\n"
    )

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password, timeout=5,
                    allow_agent=False, look_for_keys=False)

        # Write script to a temp file on the NAO to avoid shell escaping issues
        sftp = ssh.open_sftp()
        with sftp.open('/tmp/nao_asr.py', 'w') as f:
            f.write(script)
        sftp.close()

        _, stdout, stderr = ssh.exec_command('python /tmp/nao_asr.py',
                                             timeout=timeout_sec + 15)
        salida = stdout.read().decode().strip()
        errores = stderr.read().decode().strip()
        ssh.close()

        if errores:
            print(f"  [WARN] ASR Stderr: {errores}")

        for linea in salida.split('\n'):
            if linea.startswith('RECOGNIZED:'):
                raw = linea.split('RECOGNIZED:')[1].strip()
                if not raw or raw == 'NONE':
                    print(f"  [INFO] NAO did not recognize any word.")
                    return None
                # Word spotting returns "<...> alpha three <...>" — find the
                # exact vocab word contained in the result
                raw_lower = raw.lower()
                for v in vocabulario:
                    if v in raw_lower:
                        print(f"  [OK]  NAO heard: '{v}'")
                        return v
                # Fallback: return raw if no vocab match found
                print(f"  [OK]  NAO heard (raw): '{raw}'")
                return raw

        print(f"  [INFO] No recognition result.")
        return None

    except Exception as e:
        print(f"  [FAIL] Voice recognition error: {e}")
        return None


def nao_ask_and_confirm(ip, user, password, question, vocabulario, mapeo=None, max_intentos=3):
    """
    Full question -> listen -> confirmation flow via voice.

    1. NAO asks the question (TTS)
    2. NAO listens for the answer (ASR with given vocabulary)
    3. NAO repeats what it understood and asks for confirmation
    4. NAO listens for "yes" or "no"
    5. If "yes", returns the position. If "no", repeats from step 1.

    Parameters:
        question:     text NAO says to ask for the position
        vocabulario:  list of words NAO can recognize
        mapeo:        optional dict to convert recognized text to position (e.g. "a one" -> "A1")
        max_intentos: maximum number of attempts before giving up

    Returns: the confirmed position (str) or None if unsuccessful.
    """
    for intento in range(1, max_intentos + 1):
        print(f"\n  --- Attempt {intento}/{max_intentos} ---")

        nao_say_ssh(ip, user, password, question)
        time.sleep(1.5)  # Give the user time to get ready after NAO speaks

        print(f"  [INFO] Listening for response... (up to 15 seconds)")
        reconocido = nao_listen_ssh(ip, user, password, vocabulario)

        if reconocido is None:
            nao_say_ssh(ip, user, password,
                        "I did not understand. Please repeat the position.")
            continue

        if mapeo and reconocido in mapeo:
            posicion = mapeo[reconocido]
        else:
            posicion = reconocido

        nao_say_ssh(ip, user, password, f"I heard {posicion}. Is that correct?")
        time.sleep(1.5)  # Give the user time to get ready to answer yes or no

        print(f"  [INFO] Waiting for confirmation (yes/no)... (up to 10 seconds)")
        respuesta = nao_listen_ssh(ip, user, password, CONFIRMACION, timeout_sec=10)

        if respuesta and "yes" in respuesta.lower():
            nao_say_ssh(ip, user, password, f"Perfect. {posicion} confirmed.")
            print(f"  [OK]  Position confirmed: {posicion}")
            return posicion
        elif respuesta and "no" in respuesta.lower():
            nao_say_ssh(ip, user, password, "Alright, I will ask again.")
            continue
        else:
            nao_say_ssh(ip, user, password,
                        "I did not understand your confirmation. I will ask again.")
            continue

    nao_say_ssh(ip, user, password,
                "I could not understand after several attempts. Let us continue.")
    print(f"  [FAIL] Could not confirm position in {max_intentos} attempts.")
    return None


def test_voice_understanding(ip, user, password):
    """
    Full voice understanding test.
    Simulates the Isolation game flow where NAO asks the player for positions.
    """
    print("\n" + "=" * 60)
    print("  VOICE UNDERSTANDING TEST")
    print("  NAO will ask for positions and confirm by voice")
    print("=" * 60)

    nao_say_ssh(ip, user, password,
                "Let us test the voice recognition. "
                "I will ask you about board positions. "
                "Use the NATO phonetic alphabet for the column, then the row number. "
                "For example: alpha one, bravo three, charlie five, delta two, or echo four.")
    time.sleep(1)

    # ── Test 1: Ask for move position ─────────────────────────────────────────
    print("\n[TEST 1] Asking for move position...")
    pos_mover = nao_ask_and_confirm(
        ip, user, password,
        question="Which position do you want to move your piece to?",
        vocabulario=VOCAB_POSICIONES_HABLADAS,
        mapeo=HABLADO_A_POSICION,
        max_intentos=3
    )

    if pos_mover:
        print(f"  [RESULT] Move position: {pos_mover}")
    else:
        print(f"  [RESULT] No move position obtained.")

    time.sleep(1)

    # ── Test 2: Ask for cell to block ─────────────────────────────────────────
    print("\n[TEST 2] Asking for cell to block...")
    pos_bloquear = nao_ask_and_confirm(
        ip, user, password,
        question="Which cell do you want to block?",
        vocabulario=VOCAB_POSICIONES_HABLADAS,
        mapeo=HABLADO_A_POSICION,
        max_intentos=3
    )

    if pos_bloquear:
        print(f"  [RESULT] Cell to block: {pos_bloquear}")
    else:
        print(f"  [RESULT] No cell to block obtained.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  VOICE TEST SUMMARY")
    print("-" * 60)
    print(f"  Move:   {pos_mover or 'Not recognized'}")
    print(f"  Block:  {pos_bloquear or 'Not recognized'}")

    if pos_mover and pos_bloquear:
        resumen = (f"Perfect. You want to move to {pos_mover} "
                   f"and block cell {pos_bloquear}.")
        nao_say_ssh(ip, user, password, resumen)
        print(f"  [OK] Test completed successfully.")
    elif pos_mover or pos_bloquear:
        nao_say_ssh(ip, user, password,
                    "I only understood part of your instructions. "
                    "But voice recognition is partially working.")
        print(f"  [PARTIAL] At least one position was recognized.")
    else:
        nao_say_ssh(ip, user, password,
                    "I could not understand the positions. "
                    "We may need to adjust the voice recognition settings.")
        print(f"  [FAIL] No position was recognized.")

    return pos_mover, pos_bloquear


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print(f"  NAO Connection & Voice Test -> {NAO_IP}")
    print("=" * 60)

    print("\n[1] Checking network ports...")
    sdk_ok = test_puerto(NAO_IP, 9559, "NAOqi SDK")
    ssh_ok = test_puerto(NAO_IP, 22,   "SSH")

    print("\n[2] Testing text-to-speech via SSH...")
    if ssh_ok:
        nao_say_ssh(NAO_IP, NAO_USER, NAO_PASSWORD,
                    "Hello, I am ready to play.")
    else:
        print("  [SKIP] SSH not available.")

    print("\n[3] Testing voice understanding...")
    if ssh_ok:
        test_voice_understanding(NAO_IP, NAO_USER, NAO_PASSWORD)
    else:
        print("  [SKIP] SSH not available.")

    print("\n[4] Testing celebration (dance + audio from NAO speakers)...")
    if ssh_ok:
        nao_celebrate_ssh(NAO_IP, NAO_USER, NAO_PASSWORD)
    else:
        print("  [SKIP] SSH not available.")

    print("\n" + "=" * 60)
    if ssh_ok:
        print("  SSH connection OK. The game can communicate with NAO.")
    else:
        print("  Could not connect via SSH.")
        print(f"  Make sure the robot is on at {NAO_IP}")
    print("=" * 60)
