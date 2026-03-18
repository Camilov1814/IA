import pygame
import threading
import time
import os
import copy
import paramiko

# ─── NAO Configuration ────────────────────────────────────────────────────────
NAO_IP       = "172.16.10.47"
NAO_USER     = "nao"
NAO_PASSWORD = "nao"

# ─── Voice vocabulary ─────────────────────────────────────────────────────────
# Positions are spoken using the NATO phonetic alphabet + number:
#   "alpha one" = A1, "bravo three" = B3, "charlie five" = C5, etc.
NUMEROS_TEXTO    = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five"}
LETRAS_FONETICAS = {"A": "alpha", "B": "bravo", "C": "charlie", "D": "delta", "E": "echo"}
CONFIRMACION     = ["yes", "no"]

VOCAB_POSICIONES_HABLADAS = []
for _col in ["A", "B", "C", "D", "E"]:
    for _row in ["1", "2", "3", "4", "5"]:
        VOCAB_POSICIONES_HABLADAS.append(f"{LETRAS_FONETICAS[_col]} {NUMEROS_TEXTO[_row]}")

# spoken ("alpha one") → board label ("A1")
HABLADO_A_POSICION = {}
_idx = 0
for _col in ["A", "B", "C", "D", "E"]:
    for _row in ["1", "2", "3", "4", "5"]:
        HABLADO_A_POSICION[VOCAB_POSICIONES_HABLADAS[_idx]] = f"{_col}{_row}"
        _idx += 1

# board label ("A1") → board position (row, col)
POSICION_A_BOARD = {}
for _ci, _cl in enumerate(["A", "B", "C", "D", "E"]):
    for _ri in range(5):
        POSICION_A_BOARD[f"{_cl}{_ri+1}"] = (_ri, _ci)

# Column/row label maps
COLUMNAS = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}
FILAS    = {0: "1", 1: "2", 2: "3", 3: "4", 4: "5"}


def cell_name(pos):
    """Converts board position (row, col) to label like 'A1', 'B3'."""
    r, c = pos
    return f"{COLUMNAS[c]}{FILAS[r]}"


def cell_spoken(pos):
    """Converts board position (row, col) to NATO spoken form like 'alpha one'."""
    r, c = pos
    return f"{LETRAS_FONETICAS[COLUMNAS[c]]} {NUMEROS_TEXTO[FILAS[r]]}"


def detect_removed_cell(board_before, board_after, pos1, pos2):
    """Returns the cell that was removed between two board states, if any."""
    for r in range(5):
        for c in range(5):
            if board_before[r][c] == 1 and board_after[r][c] == 0:
                if (r, c) != pos1 and (r, c) != pos2:
                    return (r, c)
    return None


# ─── NAO Speaker & Listener ───────────────────────────────────────────────────
class NaoSpeaker:
    """
    Connects the game to the NAO robot via SSH.
    Runs commands using NAO's own Python 2.7 + naoqi.
    If the robot is unavailable, the game continues without errors.
    """
    def __init__(self, ip, user, password):
        self.ip       = ip
        self.user     = user
        self.password = password
        self.available = False
        self._connect()

    def _connect(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user,
                        password=self.password, timeout=5,
                        allow_agent=False, look_for_keys=False)
            ssh.close()
            self.available = True
            print(f"[NAO] Connected via SSH at {self.ip}")
        except Exception as e:
            print(f"[NAO] Could not connect ({e}). Game runs without robot.")

    # ── Text-to-speech ────────────────────────────────────────────────────────
    def say(self, text):
        """Non-blocking TTS — fires and forgets."""
        if self.available:
            threading.Thread(target=self._say_ssh, args=(text, False), daemon=True).start()

    def say_blocking(self, text):
        """Blocking TTS — waits until NAO finishes speaking."""
        if self.available:
            self._say_ssh(text, wait=True)

    def _say_ssh(self, text, wait=False):
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
            ssh.connect(self.ip, username=self.user,
                        password=self.password, timeout=5,
                        allow_agent=False, look_for_keys=False)
            _, stdout, _ = ssh.exec_command(cmd)
            if wait:
                stdout.channel.recv_exit_status()
            ssh.close()
        except Exception as e:
            print(f"[NAO] Speech error: {e}")

    # ── Celebration ───────────────────────────────────────────────────────────
    def celebrate(self):
        """Non-blocking celebration: speech + audio + dance."""
        if self.available:
            threading.Thread(target=self._celebrate_ssh, daemon=True).start()

    def _celebrate_ssh(self):
        mp3_local  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dance-moves.mp3")
        mp3_remote = "/home/nao/dance-moves.mp3"
        cmd = (
            "python -c \""
            "import naoqi; "
            "tts = naoqi.ALProxy('ALTextToSpeech',    '127.0.0.1', 9559); "
            "ap  = naoqi.ALProxy('ALAudioPlayer',     '127.0.0.1', 9559); "
            "bm  = naoqi.ALProxy('ALBehaviorManager', '127.0.0.1', 9559); "
            "tts.setLanguage('English'); "
            "tts.say('I won! You have no more moves.'); "
            "ap.post.playFile('/home/nao/dance-moves.mp3'); "
            "bm.runBehavior('animations/Stand/Gestures/Enthusiastic_4')"
            "\""
        )
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.user,
                        password=self.password, timeout=5,
                        allow_agent=False, look_for_keys=False)
            if os.path.exists(mp3_local):
                sftp = ssh.open_sftp()
                sftp.put(mp3_local, mp3_remote)
                sftp.close()
            _, stdout, _ = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
            ssh.close()
            print("[NAO] Celebration complete.")
        except Exception as e:
            print(f"[NAO] Celebration error: {e}")

    # ── Voice recognition ─────────────────────────────────────────────────────
    def listen(self, vocabulario, timeout_sec=15):
        """
        Listens for one word/phrase from the given vocabulary.
        Writes a temp Python 2.7 script to the NAO and runs it via SSH.
        Returns the matched vocabulary item, or None on timeout.
        """
        if not self.available:
            return None

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
            "    asr.unsubscribe('IsolationASR')\n"
            "except:\n"
            "    pass\n"
            "\n"
            "asr.pause(True)\n"
            f"asr.setVocabulary({vocab_str}, True)\n"
            "asr.subscribe('IsolationASR')\n"
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
            "asr.unsubscribe('IsolationASR')\n"
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
            ssh.connect(self.ip, username=self.user,
                        password=self.password, timeout=5,
                        allow_agent=False, look_for_keys=False)
            sftp = ssh.open_sftp()
            with sftp.open('/tmp/nao_asr.py', 'w') as f:
                f.write(script)
            sftp.close()
            _, stdout, stderr = ssh.exec_command('python /tmp/nao_asr.py',
                                                 timeout=timeout_sec + 15)
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            ssh.close()
            if errors:
                print(f"  [WARN] ASR: {errors}")
            for line in output.split('\n'):
                if line.startswith('RECOGNIZED:'):
                    raw = line.split('RECOGNIZED:')[1].strip()
                    if not raw or raw == 'NONE':
                        return None
                    raw_lower = raw.lower()
                    for v in vocabulario:
                        if v in raw_lower:
                            print(f"[NAO] Heard: '{v}'")
                            return v
                    return None
        except Exception as e:
            print(f"[NAO] Listen error: {e}")
        return None

    def ask_and_confirm(self, question, vocabulario, mapeo=None, max_attempts=3):
        """
        Full ask → listen → confirm loop via voice.
        Returns the confirmed mapped value (e.g. 'A3'), or None if unsuccessful.
        """
        for attempt in range(1, max_attempts + 1):
            print(f"[NAO] Attempt {attempt}/{max_attempts}")
            self.say_blocking(question)
            time.sleep(1.5)

            recognized = self.listen(vocabulario)
            if recognized is None:
                self.say_blocking("I did not understand. Please try again.")
                continue

            value = mapeo[recognized] if (mapeo and recognized in mapeo) else recognized

            self.say_blocking(f"I heard {value}. Is that correct?")
            time.sleep(1.5)

            confirm = self.listen(CONFIRMACION, timeout_sec=10)
            if confirm and "yes" in confirm.lower():
                self.say_blocking(f"Perfect. {value} confirmed.")
                return value
            elif confirm and "no" in confirm.lower():
                self.say_blocking("Alright, let me ask again.")
            else:
                self.say_blocking("I did not understand your confirmation. Let me ask again.")

        self.say_blocking("I could not understand. Please use the mouse to make your move.")
        return None


# Global NAO instance (connects at startup)
nao = NaoSpeaker(NAO_IP, NAO_USER, NAO_PASSWORD)


# ─── AI classes ───────────────────────────────────────────────────────────────
class Node():
    def __init__(self, state, value, operators, operator=None, parent=None, objective=None):
        self.state = state
        self.value = value
        self.children = []
        self.parent = parent
        self.operator = operator
        self.objective = objective
        self.level = 0
        self.operators = operators
        self.v = 0

    def add_child(self, value, state, operator):
        node = type(self)(value=value, state=state, operator=operator, parent=self, operators=self.operators)
        node.level = node.parent.level + 1
        self.children.append(node)
        return node

    def add_node_child(self, node):
        node.level = node.parent.level + 1
        self.children.append(node)
        return node

    def getchildrens(self):
        return [
            self.getState(i)
            if not self.repeatStatePath(self.getState(i))
            else None for i, _ in enumerate(self.operators)
        ]

    def getState(self, index):
        pass

    def __eq__(self, other):
        return self.state == other.state

    def __lt__(self, other):
        return self.f() < other.f()

    def repeatStatePath(self, state):
        n = self
        while n is not None and n.state != state:
            n = n.parent
        return n is not None

    def pathObjective(self):
        n = self
        result = []
        while n is not None:
            result.append(n)
            n = n.parent
        return result

    def heuristic(self):
        return 0

    def cost(self):
        return 1

    def f(self):
        return self.cost() + self.heuristic()

    def isObjective(self):
        return self.state == self.objective.state


class Tree():
    def __init__(self, root, operators):
        self.root = root
        self.operators = operators
        self.nodes_explored = 0

    def alphaBeta(self, depth):
        self.nodes_explored = 0
        is_max = self.root.player
        self.root.v = self.alphaBetaR(self.root, depth, is_max, float('-inf'), float('inf'))
        values = [c.v for c in self.root.children]
        if is_max:
            best = max(values)
        else:
            best = min(values)
        index = values.index(best)
        return self.root.children[index]

    def alphaBetaR(self, node, depth, maxPlayer, a, b):
        self.nodes_explored += 1

        if depth == 0 or node.isObjective():
            node.v = node.heuristic()
            return node.heuristic()

        children = node.getchildrens()

        if maxPlayer:
            value = float('-inf')
            for i, child in enumerate(children):
                if child is not None:
                    newChild = type(self.root)(value=node.value+'-'+str(i), state=child, operator=i, parent=node,
                        operators=node.operators, player=False)
                    newChild = node.add_node_child(newChild)
                    valor_hijo = self.alphaBetaR(newChild, depth-1, False, a, b)
                    value = max(value, valor_hijo)
                    a = max(a, value)
                    if a >= b:
                        break
        else:
            value = float('inf')
            for i, child in enumerate(children):
                if child is not None:
                    newChild = type(self.root)(value=node.value + '-' + str(i), state=child, operator=i, parent=node,
                        operators=node.operators, player=True)
                    newChild = node.add_node_child(newChild)
                    valor_hijo = self.alphaBetaR(newChild, depth-1, True, a, b)
                    value = min(value, valor_hijo)
                    b = min(b, value)
                    if a >= b:
                        break
        node.v = value
        return value


class NodeIsolation(Node):
    MOVES = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    def __init__(self, player=True, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.v = float('-inf') if player else float('inf')

    def _board(self):
        return self.state['board']

    def _pos1(self):
        return self.state['pos1']

    def _pos2(self):
        return self.state['pos2']

    def _max_turn(self):
        return self.state.get('max_turn', True)

    def _valid_moves(self, pos, board, other_pos=None):
        r, c = pos
        return [
            (r+dr, c+dc)
            for dr, dc in self.MOVES
            if (0 <= r+dr < 5 and 0 <= c+dc < 5 and
                board[r+dr][c+dc] == 1 and
                (other_pos is None or (r+dr, c+dc) != other_pos))
        ]

    def _removable_cells(self, board, pos1, pos2):
        return [
            (r, c)
            for r in range(5) for c in range(5)
            if board[r][c] == 1 and (r,c) != pos1 and (r,c) != pos2
        ]

    def getchildrens(self):
        board  = self._board()
        pos1   = self._pos1()
        pos2   = self._pos2()
        is_max = self._max_turn()

        current = pos1 if is_max else pos2
        other   = pos2 if is_max else pos1

        moves = self._valid_moves(current, board, other)
        if not moves:
            return []

        children_states = []
        for (nr, nc) in moves:
            new_pos1 = (nr, nc) if is_max else pos1
            new_pos2 = pos2     if is_max else (nr, nc)
            removable = self._removable_cells(board, new_pos1, new_pos2)
            if not removable:
                children_states.append({
                    'board':    [row[:] for row in board],
                    'pos1':     new_pos1,
                    'pos2':     new_pos2,
                    'max_turn': not is_max,
                })
            else:
                for (er, ec) in removable:
                    new_board = [row[:] for row in board]
                    new_board[er][ec] = 0
                    children_states.append({
                        'board':    new_board,
                        'pos1':     new_pos1,
                        'pos2':     new_pos2,
                        'max_turn': not is_max,
                    })
        return children_states

    def getState(self, index):
        return None

    def isObjective(self):
        board   = self._board()
        pos1    = self._pos1()
        pos2    = self._pos2()
        is_max  = self._max_turn()
        current = pos1 if is_max else pos2
        other   = pos2 if is_max else pos1
        return len(self._valid_moves(current, board, other)) == 0

    def offensive(self, playerMoves, opponentMoves):
        return 15 * (len(playerMoves) - len(opponentMoves))

    def defensive(self, playerMoves, opponentMoves):
        return 10 * len(playerMoves) - 20 * len(opponentMoves)

    def offensiveToDefensive(self, playerMoves, opponentMoves, available_cells):
        return self.offensive(playerMoves, opponentMoves) if available_cells > 12 else self.defensive(playerMoves, opponentMoves)

    def heuristic(self):
        board = self._board()
        pos1  = self._pos1()
        pos2  = self._pos2()

        moves_max = self._valid_moves(pos1, board, pos2)
        moves_min = self._valid_moves(pos2, board, pos1)
        n_max = len(moves_max)
        n_min = len(moves_min)

        if n_max == 0 and n_min == 0:
            return 0
        if n_max == 0:
            return -200
        if n_min == 0:
            return 200

        current_cells = sum(sum(row) for row in board)
        strategy_score = self.offensiveToDefensive(moves_max, moves_min, current_cells)

        center = 2.0
        dist_max = abs(pos1[0]-center) + abs(pos1[1]-center)
        dist_min = abs(pos2[0]-center) + abs(pos2[1]-center)
        centre_score = 2 * (dist_min - dist_max)

        return strategy_score + centre_score

    def cost(self):
        return self.level


# ─── Game ─────────────────────────────────────────────────────────────────────
class IsolationGameWithDifficulty:
    def __init__(self, width=600, height=700):
        pygame.init()

        self.width  = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Isolation Game - Individual Tiles")

        self.board_size    = 5
        self.cell_size     = 80
        self.board_offset_x = (width - self.board_size * self.cell_size) // 2
        self.board_offset_y = 150

        self.load_tile_images()

        self.font       = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font  = pygame.font.Font(None, 20)

        self.WHITE      = (255, 255, 255)
        self.BLACK      = (0, 0, 0)
        self.GREEN      = (0, 255, 0)
        self.RED        = (255, 0, 0)
        self.BLUE       = (0, 0, 255)
        self.LIGHT_GRAY = (200, 200, 200)
        self.YELLOW     = (255, 255, 0)
        self.DARK_GRAY  = (100, 100, 100)

        self.difficulties = {
            "Easy":       {"depth": 1, "name": "EASY"},
            "Medium":     {"depth": 2, "name": "MEDIUM"},
            "Hard":       {"depth": 3, "name": "HARD"},
            "Impossible": {"depth": 4, "name": "IMPOSSIBLE"},
        }
        self.current_difficulty = "Medium"
        self.game_started = False

        self.reset_game()

        self.selected_pos  = None
        self.valid_moves   = []
        self.game_phase    = "move"
        self.removable_cells = []
        self.ai_thinking   = False
        self.voice_thinking = False   # True while human voice-input thread is running
        self.nao_message   = ""
        self.last_nodes_explored  = 0
        self.last_processing_time = 0.0

    # ── Asset loading ─────────────────────────────────────────────────────────
    def load_tile_images(self):
        assets_dir = "game_assets"
        try:
            blue_path = os.path.join(assets_dir, "blueTile.png")
            red_path  = os.path.join(assets_dir, "redTile.png")

            if os.path.exists(blue_path):
                self.blue_tile = pygame.transform.scale(pygame.image.load(blue_path), (self.cell_size, self.cell_size))
            else:
                self.create_fallback_blue_tile()

            if os.path.exists(red_path):
                self.red_tile = pygame.transform.scale(pygame.image.load(red_path), (self.cell_size, self.cell_size))
            else:
                self.create_fallback_red_tile()

            jugador_path = os.path.join(assets_dir, "jugador.png")
            ia_path      = os.path.join(assets_dir, "IA.png")

            if os.path.exists(jugador_path):
                self.player1_piece = pygame.transform.scale(pygame.image.load(jugador_path), (self.cell_size, self.cell_size))
            else:
                self.create_fallback_player1_piece()

            if os.path.exists(ia_path):
                self.player2_piece = pygame.transform.scale(pygame.image.load(ia_path), (self.cell_size, self.cell_size))
            else:
                self.create_fallback_player2_piece()

            self.blocked_cell = pygame.Surface((self.cell_size, self.cell_size))
            self.blocked_cell.fill((20, 20, 20))

            self.valid_move_overlay = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.valid_move_overlay.fill((0, 255, 0, 100))

            self.removable_overlay = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.removable_overlay.fill((255, 255, 0, 100))

        except Exception as e:
            print(f"Error loading images: {e}")
            self.create_fallback_graphics()

    def create_fallback_blue_tile(self):
        self.blue_tile = pygame.Surface((self.cell_size, self.cell_size))
        self.blue_tile.fill((50, 50, 200))

    def create_fallback_red_tile(self):
        self.red_tile = pygame.Surface((self.cell_size, self.cell_size))
        self.red_tile.fill((200, 50, 50))

    def create_fallback_player1_piece(self):
        self.player1_piece = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        pygame.draw.circle(self.player1_piece, (200, 100, 255), (self.cell_size//2, self.cell_size//2), 30)

    def create_fallback_player2_piece(self):
        self.player2_piece = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        pygame.draw.circle(self.player2_piece, (255, 150, 50), (self.cell_size//2, self.cell_size//2), 30)

    def create_fallback_graphics(self):
        self.create_fallback_blue_tile()
        self.create_fallback_red_tile()
        self.create_fallback_player1_piece()
        self.create_fallback_player2_piece()

    # ── Game state ────────────────────────────────────────────────────────────
    def reset_game(self):
        self.game_state = {
            'board':    [[1]*5 for _ in range(5)],
            'pos1':     (0, 2),   # Human player
            'pos2':     (4, 2),   # AI
            'max_turn': True
        }
        self.game_over      = False
        self.winner         = None
        self.human_turn     = True
        self.voice_thinking = False
        self.selected_pos   = None
        self.game_phase     = "move"
        self.nao_message    = ""
        self.last_nodes_explored  = 0
        self.last_processing_time = 0.0

    def get_valid_moves(self, pos, board, other_pos=None):
        MOVES = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        r, c = pos
        return [
            (r+dr, c+dc)
            for dr, dc in MOVES
            if (0 <= r+dr < 5 and 0 <= c+dc < 5 and
                board[r+dr][c+dc] == 1 and
                (other_pos is None or (r+dr, c+dc) != other_pos))
        ]

    def get_removable_cells(self, board, pos1, pos2):
        return [
            (r, c)
            for r in range(5) for c in range(5)
            if board[r][c] == 1 and (r,c) != pos1 and (r,c) != pos2
        ]

    # ── Coordinate helpers ────────────────────────────────────────────────────
    def screen_to_board(self, screen_pos):
        x, y = screen_pos
        bx = (x - self.board_offset_x) // self.cell_size
        by = (y - self.board_offset_y) // self.cell_size
        if 0 <= bx < 5 and 0 <= by < 5:
            return (by, bx)
        return None

    def board_to_screen(self, board_pos):
        r, c = board_pos
        return (self.board_offset_x + c * self.cell_size,
                self.board_offset_y + r * self.cell_size)

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw_difficulty_selection(self):
        self.screen.fill(self.WHITE)
        title = self.font.render("ISOLATION - Select Difficulty", True, self.BLACK)
        self.screen.blit(title, title.get_rect(center=(self.width//2, 100)))

        y_start = 200
        for i, (key, info) in enumerate(self.difficulties.items()):
            y = y_start + i * 60
            if key == self.current_difficulty:
                rect = pygame.Rect(self.width//2 - 150, y - 20, 300, 50)
                pygame.draw.rect(self.screen, self.LIGHT_GRAY, rect)
                pygame.draw.rect(self.screen, self.BLACK, rect, 2)
            text = self.small_font.render(f"{info['name']} (Depth {info['depth']})", True, self.BLACK)
            self.screen.blit(text, text.get_rect(center=(self.width//2, y)))

        instructions = [
            "Use UP/DOWN arrows to select difficulty",
            "Press ENTER to start the game",
            "Press ESC to quit",
        ]
        for i, inst in enumerate(instructions):
            text = self.tiny_font.render(inst, True, self.DARK_GRAY)
            self.screen.blit(text, text.get_rect(center=(self.width//2, 450 + i * 30)))

    def draw_board(self):
        board = self.game_state['board']
        pos1  = self.game_state['pos1']
        pos2  = self.game_state['pos2']
        current_cells = sum(sum(row) for row in board)
        tile = self.red_tile if current_cells > 12 else self.blue_tile

        col_labels = ["A", "B", "C", "D", "E"]
        row_labels  = ["1", "2", "3", "4", "5"]

        for c in range(5):
            x = self.board_offset_x + c * self.cell_size + self.cell_size // 2
            y = self.board_offset_y - 18
            lbl = self.small_font.render(col_labels[c], True, self.DARK_GRAY)
            self.screen.blit(lbl, lbl.get_rect(center=(x, y)))

        for r in range(5):
            x = self.board_offset_x - 18
            y = self.board_offset_y + r * self.cell_size + self.cell_size // 2
            lbl = self.small_font.render(row_labels[r], True, self.DARK_GRAY)
            self.screen.blit(lbl, lbl.get_rect(center=(x, y)))

        for r in range(5):
            for c in range(5):
                x, y = self.board_to_screen((r, c))
                if board[r][c] == 0:
                    self.screen.blit(self.blocked_cell, (x, y))
                else:
                    self.screen.blit(tile, (x, y))
                    if (r, c) in self.valid_moves:
                        self.screen.blit(self.valid_move_overlay, (x, y))
                    elif (r, c) in self.removable_cells:
                        self.screen.blit(self.removable_overlay, (x, y))
                if (r, c) == pos1:
                    self.screen.blit(self.player1_piece, (x, y))
                elif (r, c) == pos2:
                    self.screen.blit(self.player2_piece, (x, y))

    def draw_game_ui(self):
        # Title
        title_text = self.font.render(
            f"ISOLATION - {self.difficulties[self.current_difficulty]['name']}", True, self.BLACK)
        self.screen.blit(title_text, title_text.get_rect(center=(self.width//2, 30)))

        # Status
        if self.game_over:
            if self.winner == "human":
                status, color = "YOU WIN!", self.GREEN
            elif self.winner == "ai":
                status, color = "AI WINS!", self.RED
            else:
                status, color = "DRAW", self.BLACK
        elif self.ai_thinking:
            depth = self.difficulties[self.current_difficulty]['depth']
            status, color = f"AI thinking... (Depth {depth})", self.RED
        elif self.voice_thinking:
            if self.game_phase == "move":
                status = "Your turn - Say your move (e.g. alpha three)"
            else:
                status = "Your turn - Say the cell to block"
            color = self.BLUE
        elif self.human_turn:
            if self.game_phase == "move":
                status = "Your turn - Click or speak your move"
            else:
                status = "Your turn - Click or speak to block a cell"
            color = self.BLUE
        else:
            status, color = "AI turn", self.RED

        status_text = self.small_font.render(status, True, color)
        self.screen.blit(status_text, status_text.get_rect(center=(self.width//2, 60)))

        # NAO message
        if self.nao_message:
            nao_text = self.tiny_font.render(f"NAO: {self.nao_message}", True, self.DARK_GRAY)
            self.screen.blit(nao_text, nao_text.get_rect(center=(self.width//2, 110)))

        # Strategy indicator
        if not self.game_over:
            current_cells = sum(sum(row) for row in self.game_state['board'])
            strategy  = "OFFENSIVE" if current_cells > 12 else "DEFENSIVE"
            tile_color = "RED" if current_cells > 12 else "BLUE"
            strat_text = self.small_font.render(
                f"AI: {current_cells} cells -> {strategy} | Tiles {tile_color}", True, self.BLACK)
            self.screen.blit(strat_text, strat_text.get_rect(center=(self.width//2, 85)))

        # Performance metrics
        if self.last_nodes_explored > 0:
            metrics = self.tiny_font.render(
                f"Last AI move: {self.last_nodes_explored} nodes | {self.last_processing_time:.3f}s",
                True, self.DARK_GRAY)
            self.screen.blit(metrics, metrics.get_rect(center=(self.width//2, self.height - 50)))

        # Instructions
        if self.game_over:
            instructions = ["Press R to restart", "Press D to change difficulty", "Press ESC to quit"]
        else:
            instructions = ["Click or speak to move/block", "Press D to change difficulty"]

        y_offset = self.board_offset_y + 5 * self.cell_size + 30
        for i, inst in enumerate(instructions):
            text = self.small_font.render(inst, True, self.BLACK)
            self.screen.blit(text, text.get_rect(center=(self.width//2, y_offset + i * 25)))

    # ── Human turn: mouse input ───────────────────────────────────────────────
    def handle_human_move(self, board_pos):
        """Apply a human move from mouse click."""
        if self.game_phase == "move":
            if board_pos in self.valid_moves:
                self.game_state['pos1'] = board_pos
                self.removable_cells = self.get_removable_cells(
                    self.game_state['board'], self.game_state['pos1'], self.game_state['pos2'])
                if self.removable_cells:
                    self.game_phase = "remove"
                else:
                    self.end_human_turn()
        elif self.game_phase == "remove":
            if board_pos in self.removable_cells:
                r, c = board_pos
                self.game_state['board'][r][c] = 0
                self.end_human_turn()

    def end_human_turn(self):
        self.game_state['max_turn'] = False
        self.human_turn     = False
        self.voice_thinking = False
        self.game_phase     = "move"
        self.valid_moves    = []
        self.removable_cells = []

    # ── Human turn: voice input ───────────────────────────────────────────────
    def human_voice_move(self):
        """
        Runs in a background thread.
        Asks the human for their move and block via voice, then applies them.
        Falls back gracefully to mouse if NAO is unavailable or voice fails.
        """
        self.voice_thinking = True

        pos1  = self.game_state['pos1']
        pos2  = self.game_state['pos2']
        board = self.game_state['board']
        valid = self.get_valid_moves(pos1, board, pos2)

        if not valid:
            self.game_over  = True
            self.winner     = "ai"
            self.nao_message = "I win! You have no valid moves."
            nao.celebrate()
            self.voice_thinking = False
            return

        # ── Ask for move position ─────────────────────────────────────────────
        board_pos = None
        while board_pos is None:
            if self.game_over:
                self.voice_thinking = False
                return

            label = nao.ask_and_confirm(
                "Which position do you want to move your piece to? "
                "Say the NATO letter and number, for example alpha three.",
                VOCAB_POSICIONES_HABLADAS,
                HABLADO_A_POSICION,
            )

            if label is None:
                # Voice failed — let player use mouse
                self.nao_message = "Voice failed. Use the mouse to move."
                self.voice_thinking = False
                return

            candidate = POSICION_A_BOARD.get(label)
            if candidate is None or candidate not in valid:
                spoken_valid = ", ".join(cell_spoken(m) for m in valid[:4])
                nao.say_blocking(
                    f"{label} is not a valid move. "
                    f"Valid positions include {spoken_valid}. Please try again."
                )
            else:
                board_pos = candidate

        # Apply move
        self.game_state['pos1'] = board_pos
        self.nao_message = f"Player moved to {cell_name(board_pos)}"
        self.valid_moves = []

        # ── Ask for cell to block ─────────────────────────────────────────────
        removable = self.get_removable_cells(
            self.game_state['board'], self.game_state['pos1'], self.game_state['pos2'])

        if removable:
            self.removable_cells = removable
            self.game_phase = "remove"

            block_pos = None
            while block_pos is None:
                if self.game_over:
                    self.voice_thinking = False
                    return

                label = nao.ask_and_confirm(
                    "Which cell do you want to block? Say the NATO letter and number.",
                    VOCAB_POSICIONES_HABLADAS,
                    HABLADO_A_POSICION,
                )

                if label is None:
                    self.nao_message = "Voice failed. Click the cell to block."
                    self.voice_thinking = False
                    return

                candidate = POSICION_A_BOARD.get(label)
                if candidate is None or candidate not in removable:
                    nao.say_blocking(f"{label} cannot be blocked. Please choose another cell.")
                else:
                    block_pos = candidate

            r, c = block_pos
            self.game_state['board'][r][c] = 0
            self.nao_message = f"Player blocked {cell_name(block_pos)}"

        self.end_human_turn()

    # ── AI turn ───────────────────────────────────────────────────────────────
    def ai_move(self):
        self.ai_thinking = True

        pos2  = self.game_state['pos2']
        pos1  = self.game_state['pos1']
        board = self.game_state['board']
        valid_ai = self.get_valid_moves(pos2, board, pos1)

        if not valid_ai:
            self.game_over   = True
            self.winner      = "human"
            self.ai_thinking = False
            self.nao_message = "I have no moves. You win!"
            nao.say_blocking("I have no valid moves. You win! Congratulations.")
            return

        self.nao_message = "Thinking..."
        nao.say("Thinking")

        depth = self.difficulties[self.current_difficulty]['depth']
        ia_state = copy.deepcopy(self.game_state)
        ia_state['max_turn'] = False

        root = NodeIsolation(state=ia_state, value='root',
                             operators=['move+remove'], player=False)

        start_time = time.time()
        tree = Tree(root=root, operators=['move+remove'])
        best_child = tree.alphaBeta(depth=depth)
        end_time = time.time()

        self.last_nodes_explored  = tree.nodes_explored
        self.last_processing_time = end_time - start_time

        if best_child:
            board_before = [row[:] for row in self.game_state['board']]
            new_state    = copy.deepcopy(best_child.state)
            pos2_new     = new_state['pos2']
            removed      = detect_removed_cell(board_before, new_state['board'],
                                               new_state['pos1'], pos2_new)

            dest = cell_name(pos2_new)
            dest_spoken = cell_spoken(pos2_new)
            if removed:
                removed_spoken = cell_spoken(removed)
                message = f"I move to {dest_spoken}. I block {removed_spoken}."
                ui_msg  = f"AI moved to {dest}. Blocked {cell_name(removed)}."
            else:
                message = f"I move to {dest_spoken}."
                ui_msg  = f"AI moved to {dest}."

            self.nao_message = ui_msg
            print(f"[NAO] {ui_msg}")
            nao.say_blocking(message)

            self.game_state = {
                'board':    new_state['board'],
                'pos1':     new_state['pos1'],
                'pos2':     new_state['pos2'],
                'max_turn': True,
            }

        self.human_turn  = True
        self.ai_thinking = False

        pos1_new = self.game_state['pos1']
        pos2_new = self.game_state['pos2']
        if not self.get_valid_moves(pos1_new, self.game_state['board'], pos2_new):
            self.game_over   = True
            self.winner      = "ai"
            self.nao_message = "I win!"
            nao.celebrate()

    def update_valid_moves(self):
        if self.human_turn and self.game_phase == "move" and not self.game_over:
            pos1 = self.game_state['pos1']
            pos2 = self.game_state['pos2']
            self.valid_moves = self.get_valid_moves(pos1, self.game_state['board'], pos2)
            if not self.valid_moves:
                self.game_over   = True
                self.winner      = "ai"
                self.nao_message = "I win! You have no valid moves."
                nao.celebrate()

    # ── Game intro (runs in background thread) ────────────────────────────────
    def game_intro(self, difficulty_name):
        """NAO announces the difficulty and explains how to play."""
        nao.say_blocking(
            f"Difficulty set to {difficulty_name}. "
            "Welcome to Isolation! Here is how to play. "
            "On your turn, say the column using the NATO alphabet and then the row number. "
            "Columns are alpha, bravo, charlie, delta, and echo. "
            "Rows are one through five. "
            "For example, say alpha three to move to column A, row three. "
            "After moving, say another position to block that cell. "
            "The player who cannot move loses. Good luck!"
        )

    # ── Difficulty selection ──────────────────────────────────────────────────
    def handle_difficulty_selection(self, event):
        if event.type == pygame.KEYDOWN:
            keys = list(self.difficulties.keys())
            idx  = keys.index(self.current_difficulty)
            if event.key == pygame.K_UP:
                self.current_difficulty = keys[(idx - 1) % len(keys)]
                nao.say(self.difficulties[self.current_difficulty]['name'])
            elif event.key == pygame.K_DOWN:
                self.current_difficulty = keys[(idx + 1) % len(keys)]
                nao.say(self.difficulties[self.current_difficulty]['name'])
            elif event.key == pygame.K_RETURN:
                self.game_started = True
                self.reset_game()
                diff_name = self.difficulties[self.current_difficulty]['name']
                print(f"Starting game — difficulty: {diff_name}")
                threading.Thread(target=self.game_intro, args=(diff_name,), daemon=True).start()
            elif event.key == pygame.K_ESCAPE:
                return False
        return True

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        clock   = pygame.time.Clock()
        running = True

        print("Isolation Game — Individual Tiles")
        print("Green tiles = valid moves | Yellow tiles = removable cells")
        print("Red tiles = Offensive strategy (>12 cells) | Blue = Defensive")
        print("Speak using NATO alphabet: alpha, bravo, charlie, delta, echo + one..five")

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if not self.game_started:
                    if not self.handle_difficulty_selection(event):
                        running = False
                else:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r and self.game_over:
                            self.reset_game()
                        elif event.key == pygame.K_d:
                            self.game_started = False
                        elif event.key == pygame.K_ESCAPE:
                            running = False

                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        board_pos = self.screen_to_board(event.pos)
                        if board_pos and self.human_turn and not self.game_over and not self.voice_thinking:
                            self.handle_human_move(board_pos)

            if self.game_started and not self.game_over:
                if self.human_turn:
                    self.update_valid_moves()
                    # Start voice input thread once per human turn
                    if not self.voice_thinking and not self.ai_thinking:
                        threading.Thread(target=self.human_voice_move, daemon=True).start()
                elif not self.ai_thinking:
                    threading.Thread(target=self.ai_move, daemon=True).start()

            self.screen.fill(self.WHITE)
            if not self.game_started:
                self.draw_difficulty_selection()
            else:
                self.draw_board()
                self.draw_game_ui()

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


def main():
    try:
        game = IsolationGameWithDifficulty()
        game.run()
    except Exception as e:
        print(f"Error starting game: {e}")
        print("Make sure pygame is installed: pip install pygame")

if __name__ == "__main__":
    main()
