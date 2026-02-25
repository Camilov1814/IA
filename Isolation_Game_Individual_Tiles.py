import pygame
import sys
import threading
import time
import os
import copy

# Import the AI classes from the notebook (we'll need to copy them here)
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
            else None for i, op in enumerate(self.operators)
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
        other = pos2 if is_max else pos1

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
        other = pos2 if is_max else pos1
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


class IsolationGameWithDifficulty:
    def __init__(self, width=600, height=700):
        pygame.init()

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Isolation Game - Individual Tiles")

        # Board configuration
        self.board_size = 5
        self.cell_size = 80
        self.board_offset_x = (width - self.board_size * self.cell_size) // 2
        self.board_offset_y = 150

        # Load individual tile images
        self.load_tile_images()

        # Fonts
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 20)

        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GREEN = (0, 255, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.LIGHT_GRAY = (200, 200, 200)
        self.YELLOW = (255, 255, 0)
        self.DARK_GRAY = (100, 100, 100)

        # Difficulty settings
        self.difficulties = {
            "Fácil": {"depth": 1, "name": "FÁCIL"},
            "Medio": {"depth": 2, "name": "MEDIO"},
            "Difícil": {"depth": 3, "name": "DIFÍCIL"},
            "Imposible": {"depth": 4, "name": "IMPOSIBLE"}
        }

        self.current_difficulty = "Medio"  # Default
        self.game_started = False

        # Game state
        self.reset_game()

        # UI state
        self.selected_pos = None
        self.valid_moves = []
        self.game_phase = "move"
        self.removable_cells = []
        self.ai_thinking = False
        self.last_nodes_explored = 0
        self.last_processing_time = 0.0

    def load_tile_images(self):
        """Load individual tile images (blueTile.png and redTile.png)"""
        print("Loading individual tile images...")

        assets_dir = "game_assets"

        try:
            # Load blue and red tiles
            blue_tile_path = os.path.join(assets_dir, "blueTile.png")
            red_tile_path = os.path.join(assets_dir, "redTile.png")

            if os.path.exists(blue_tile_path):
                blue_original = pygame.image.load(blue_tile_path)
                self.blue_tile = pygame.transform.scale(blue_original, (self.cell_size, self.cell_size))
                print("Blue tile loaded successfully")
            else:
                print(f"Blue tile not found: {blue_tile_path}")
                self.create_fallback_blue_tile()

            if os.path.exists(red_tile_path):
                red_original = pygame.image.load(red_tile_path)
                self.red_tile = pygame.transform.scale(red_original, (self.cell_size, self.cell_size))
                print("Red tile loaded successfully")
            else:
                print(f"Red tile not found: {red_tile_path}")
                self.create_fallback_red_tile()

            # Load player pieces
            jugador_path = os.path.join(assets_dir, "jugador.png")
            ia_path = os.path.join(assets_dir, "IA.png")

            if os.path.exists(jugador_path):
                player_original = pygame.image.load(jugador_path)
                self.player1_piece = pygame.transform.scale(player_original, (self.cell_size, self.cell_size))
                print("Player piece loaded successfully")
            else:
                self.create_fallback_player1_piece()

            if os.path.exists(ia_path):
                ia_original = pygame.image.load(ia_path)
                self.player2_piece = pygame.transform.scale(ia_original, (self.cell_size, self.cell_size))
                print("AI piece loaded successfully")
            else:
                self.create_fallback_player2_piece()

            # Create blocked cell (black)
            self.blocked_cell = pygame.Surface((self.cell_size, self.cell_size))
            self.blocked_cell.fill((20, 20, 20))

            # Create overlays
            self.valid_move_overlay = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.valid_move_overlay.fill((0, 255, 0, 100))  # Green transparent

            self.removable_overlay = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.removable_overlay.fill((255, 255, 0, 100))  # Yellow transparent

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
        center = self.cell_size // 2
        pygame.draw.circle(self.player1_piece, (200, 100, 255), (center, center), 30)

    def create_fallback_player2_piece(self):
        self.player2_piece = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        center = self.cell_size // 2
        pygame.draw.circle(self.player2_piece, (255, 150, 50), (center, center), 30)

    def create_fallback_graphics(self):
        print("Creating fallback graphics...")
        self.create_fallback_blue_tile()
        self.create_fallback_red_tile()
        self.create_fallback_player1_piece()
        self.create_fallback_player2_piece()

    def reset_game(self):
        """Reset game state"""
        self.game_state = {
            'board': [[1]*5 for _ in range(5)],
            'pos1': (0, 2),  # Player (X)
            'pos2': (4, 2),  # AI (O)
            'max_turn': True  # Player's turn
        }
        self.game_over = False
        self.winner = None
        self.human_turn = True
        self.selected_pos = None
        self.game_phase = "move"
        self.last_nodes_explored = 0
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

    def screen_to_board(self, screen_pos):
        x, y = screen_pos
        board_x = (x - self.board_offset_x) // self.cell_size
        board_y = (y - self.board_offset_y) // self.cell_size

        if 0 <= board_x < 5 and 0 <= board_y < 5:
            return (board_y, board_x)
        return None

    def board_to_screen(self, board_pos):
        r, c = board_pos
        x = self.board_offset_x + c * self.cell_size
        y = self.board_offset_y + r * self.cell_size
        return (x, y)

    def draw_difficulty_selection(self):
        """Draw difficulty selection screen"""
        self.screen.fill(self.WHITE)

        # Title
        title = self.font.render("ISOLATION - Selecciona Dificultad", True, self.BLACK)
        title_rect = title.get_rect(center=(self.width//2, 100))
        self.screen.blit(title, title_rect)

        # Difficulty options
        y_start = 200
        for i, (diff_key, diff_info) in enumerate(self.difficulties.items()):
            y_pos = y_start + i * 60

            # Highlight current selection
            if diff_key == self.current_difficulty:
                highlight_rect = pygame.Rect(self.width//2 - 150, y_pos - 20, 300, 50)
                pygame.draw.rect(self.screen, self.LIGHT_GRAY, highlight_rect)
                pygame.draw.rect(self.screen, self.BLACK, highlight_rect, 2)

            # Difficulty text
            diff_text = f"{diff_info['name']} (Depth {diff_info['depth']})"
            text_surface = self.small_font.render(diff_text, True, self.BLACK)
            text_rect = text_surface.get_rect(center=(self.width//2, y_pos))
            self.screen.blit(text_surface, text_rect)

        # Instructions
        instructions = [
            "Use las flechas ARRIBA/ABAJO para seleccionar",
            "Presiona ENTER para comenzar el juego",
            "Presiona ESC para salir"
        ]

        for i, instruction in enumerate(instructions):
            y_pos = 450 + i * 30
            text = self.tiny_font.render(instruction, True, self.DARK_GRAY)
            text_rect = text.get_rect(center=(self.width//2, y_pos))
            self.screen.blit(text, text_rect)

    def draw_board(self):
        """Draw the game board using individual tile images"""
        board = self.game_state['board']
        pos1 = self.game_state['pos1']
        pos2 = self.game_state['pos2']

        # Choose tile color based on available cells (strategy indicator)
        current_cells = sum(sum(row) for row in board)
        tile_image = self.red_tile if current_cells > 12 else self.blue_tile

        for r in range(5):
            for c in range(5):
                x, y = self.board_to_screen((r, c))

                if board[r][c] == 0:  # Blocked cell
                    self.screen.blit(self.blocked_cell, (x, y))
                else:
                    # Draw tile
                    self.screen.blit(tile_image, (x, y))

                    # Overlays
                    if (r, c) in self.valid_moves:
                        self.screen.blit(self.valid_move_overlay, (x, y))
                    elif (r, c) in self.removable_cells:
                        self.screen.blit(self.removable_overlay, (x, y))

                # Draw pieces
                if (r, c) == pos1:
                    self.screen.blit(self.player1_piece, (x, y))
                elif (r, c) == pos2:
                    self.screen.blit(self.player2_piece, (x, y))

    def draw_game_ui(self):
        """Draw game UI"""
        # Title
        title = f"ISOLATION - {self.difficulties[self.current_difficulty]['name']}"
        title_text = self.font.render(title, True, self.BLACK)
        title_rect = title_text.get_rect(center=(self.width//2, 30))
        self.screen.blit(title_text, title_rect)

        # Game status
        if self.game_over:
            if self.winner == "human":
                status = "¡GANASTE! 🎉"
                color = self.GREEN
            elif self.winner == "ai":
                status = "IA GANÓ 🤖"
                color = self.RED
            else:
                status = "EMPATE"
                color = self.BLACK
        elif self.ai_thinking:
            depth = self.difficulties[self.current_difficulty]['depth']
            status = f"IA pensando... (Depth {depth})"
            color = self.RED
        elif self.human_turn:
            if self.game_phase == "move":
                status = "Tu turno - Selecciona movimiento"
            else:
                status = "Tu turno - Elimina una celda"
            color = self.BLUE
        else:
            status = "Turno de la IA"
            color = self.RED

        status_text = self.small_font.render(status, True, color)
        status_rect = status_text.get_rect(center=(self.width//2, 60))
        self.screen.blit(status_text, status_rect)

        # Strategy indicator
        if not self.game_over:
            current_cells = sum(sum(row) for row in self.game_state['board'])
            strategy = "OFENSIVA" if current_cells > 12 else "DEFENSIVA"
            tile_color = "ROJO" if current_cells > 12 else "AZUL"

            strategy_text = self.small_font.render(
                f"IA: {current_cells} casillas → {strategy} | Tiles {tile_color}",
                True, self.BLACK
            )
            strategy_rect = strategy_text.get_rect(center=(self.width//2, 85))
            self.screen.blit(strategy_text, strategy_rect)

        # Performance metrics
        if self.last_nodes_explored > 0:
            metrics_text = self.tiny_font.render(
                f"📊 Último movimiento IA: {self.last_nodes_explored} nodos | {self.last_processing_time:.3f}s",
                True, self.DARK_GRAY
            )
            metrics_rect = metrics_text.get_rect(center=(self.width//2, self.height - 50))
            self.screen.blit(metrics_text, metrics_rect)

        # Instructions
        if self.game_over:
            instructions = ["Presiona R para reiniciar", "Presiona D para cambiar dificultad", "Presiona ESC para salir"]
        else:
            instructions = ["Haz clic para mover/eliminar", "Presiona D para cambiar dificultad"]

        y_offset = self.board_offset_y + 5 * self.cell_size + 30
        for i, instruction in enumerate(instructions):
            inst_text = self.small_font.render(instruction, True, self.BLACK)
            inst_rect = inst_text.get_rect(center=(self.width//2, y_offset + i * 25))
            self.screen.blit(inst_text, inst_rect)

    def handle_human_move(self, board_pos):
        """Handle human player move"""
        if self.game_phase == "move":
            if board_pos in self.valid_moves:
                self.game_state['pos1'] = board_pos

                self.removable_cells = self.get_removable_cells(
                    self.game_state['board'],
                    self.game_state['pos1'],
                    self.game_state['pos2']
                )

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
        self.human_turn = False
        self.game_phase = "move"
        self.valid_moves = []
        self.removable_cells = []

    def ai_move(self):
        """Execute AI move with selected difficulty"""
        self.ai_thinking = True

        pos2 = self.game_state['pos2']
        pos1 = self.game_state['pos1']
        board = self.game_state['board']
        valid_moves_ai = self.get_valid_moves(pos2, board, pos1)

        if not valid_moves_ai:
            self.game_over = True
            self.winner = "human"
            self.ai_thinking = False
            return

        # Use selected difficulty depth
        depth = self.difficulties[self.current_difficulty]['depth']

        ia_state = copy.deepcopy(self.game_state)
        ia_state['max_turn'] = False

        root = NodeIsolation(
            state=ia_state,
            value='root',
            operators=['mover+eliminar'],
            player=False,
        )

        start_time = time.time()
        tree = Tree(root=root, operators=['mover+eliminar'])
        best_child = tree.alphaBeta(depth=depth)
        end_time = time.time()

        self.last_nodes_explored = tree.nodes_explored
        self.last_processing_time = end_time - start_time

        if best_child:
            new_state = copy.deepcopy(best_child.state)
            self.game_state = {
                'board': new_state['board'],
                'pos1': new_state['pos1'],
                'pos2': new_state['pos2'],
                'max_turn': True
            }

        self.human_turn = True
        self.ai_thinking = False

        # Check if human has valid moves
        pos1_new = self.game_state['pos1']
        pos2_new = self.game_state['pos2']
        valid_moves_human = self.get_valid_moves(pos1_new, self.game_state['board'], pos2_new)

        if not valid_moves_human:
            self.game_over = True
            self.winner = "ai"

    def update_valid_moves(self):
        if self.human_turn and self.game_phase == "move" and not self.game_over:
            pos1 = self.game_state['pos1']
            pos2 = self.game_state['pos2']
            self.valid_moves = self.get_valid_moves(pos1, self.game_state['board'], pos2)
            if not self.valid_moves:
                self.game_over = True
                self.winner = "ai"

    def handle_difficulty_selection(self, event):
        """Handle difficulty selection input"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                difficulty_list = list(self.difficulties.keys())
                current_index = difficulty_list.index(self.current_difficulty)
                new_index = (current_index - 1) % len(difficulty_list)
                self.current_difficulty = difficulty_list[new_index]

            elif event.key == pygame.K_DOWN:
                difficulty_list = list(self.difficulties.keys())
                current_index = difficulty_list.index(self.current_difficulty)
                new_index = (current_index + 1) % len(difficulty_list)
                self.current_difficulty = difficulty_list[new_index]

            elif event.key == pygame.K_RETURN:
                self.game_started = True
                self.reset_game()
                print(f"Iniciando juego con dificultad: {self.difficulties[self.current_difficulty]['name']}")
                print(f"Depth de IA: {self.difficulties[self.current_difficulty]['depth']}")

            elif event.key == pygame.K_ESCAPE:
                return False

        return True

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True

        print("Isolation Game con Individual Tiles y Seleccion de Dificultad")
        print("Tiles verdes indican movimientos validos")
        print("Tiles amarillos indican celdas eliminables")
        print("Tiles rojos = Estrategia ofensiva (>12 casillas)")
        print("Tiles azules = Estrategia defensiva (<=12 casillas)")

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if not self.game_started:
                    # Handle difficulty selection
                    if not self.handle_difficulty_selection(event):
                        running = False
                else:
                    # Handle game events
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r and self.game_over:
                            self.reset_game()
                        elif event.key == pygame.K_d:
                            self.game_started = False  # Return to difficulty selection
                        elif event.key == pygame.K_ESCAPE:
                            running = False

                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            board_pos = self.screen_to_board(event.pos)
                            if board_pos and self.human_turn and not self.game_over:
                                self.handle_human_move(board_pos)

            # Update game state
            if self.game_started and not self.game_over:
                if self.human_turn:
                    self.update_valid_moves()
                elif not self.ai_thinking:
                    threading.Thread(target=self.ai_move, daemon=True).start()

            # Draw everything
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
    """Start the game with individual tiles and difficulty selection"""
    try:
        game = IsolationGameWithDifficulty()
        game.run()
    except Exception as e:
        print(f"Error executing game: {e}")
        print("Make sure pygame is installed correctly")

if __name__ == "__main__":
    main()