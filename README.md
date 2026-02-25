# Juego Isolation con Algoritmo Alpha-Beta

Este repositorio contiene la implementación del juego Isolation con inteligencia artificial usando algoritmo Alpha-Beta pruning, desarrollado para el curso de Ciberdefensa, Semestre 9.

## Contenido del Proyecto

### Juego de Aislamiento con Algoritmo Alpha-Beta
**Archivo:** `Isolation_alpha_betav2.ipynb`

Implementación del juego Isolation con inteligencia artificial usando algoritmo Alpha-Beta pruning.

**Características:**
- Tablero de 5x5
- Algoritmo Minimax con poda Alpha-Beta
- Heurística adaptativa (ofensiva-defensiva)
- Interfaz gráfica con pygame
- Contador de nodos explorados en versión consola

**Estrategias de IA:**
- **Estrategia Ofensiva:** Maximiza la movilidad propia (>12 casillas disponibles)
- **Estrategia Defensiva:** Minimiza la movilidad del oponente (≤12 casillas disponibles)

**Modos de juego disponibles:**
1. `play_isolation_gui_optimized()` - Interfaz gráfica con imágenes personalizadas
2. `play_isolation()` - Versión por consola con contador de nodos explorados

### Recursos Gráficos
**Directorio:** `game_assets/`

Contiene las imágenes personalizadas para el juego Isolation:
- `tableroRojo.png` - Tablero para estrategia ofensiva
- `tableroAzul.png` - Tablero para estrategia defensiva
- `jugador.png` - Ficha del jugador humano
- `IA.png` - Ficha de la inteligencia artificial

## Instalación

1. Clona o descarga este repositorio
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Uso

### Juego de Aislamiento
Abre el notebook `Isolation_alpha_betav2.ipynb` y ejecuta las celdas. Para iniciar el juego, usa una de las funciones disponibles:

```python
# Juego con gráficos personalizados (recomendado)
play_isolation_gui_optimized()

# Juego por consola con contador de nodos
play_isolation()
```

## Dependencias Principales

- **numpy**: Operaciones numéricas y arrays
- **pandas**: Manipulación de datos
- **matplotlib**: Visualización básica
- **plotly**: Gráficos interactivos
- **pygame**: Interfaz gráfica del juego
- **pydot**: Visualización de árboles (opcional)
- **jupyter**: Entorno de notebooks

## Algoritmos Implementados

### Alpha-Beta Pruning
- **Búsqueda:** Minimax con poda alpha-beta
- **Heurística:** Evaluación de movilidad con control del centro
- **Profundidad:** Configurable (depth 2-3 recomendado)
- **Métricas:** Contador de nodos explorados para análisis de rendimiento

## Reglas del Juego

El Isolation es un juego de estrategia para dos jugadores:

1. **Objetivo:** Ser el último jugador que pueda moverse
2. **Tablero:** 5x5 casillas
3. **Movimientos:** Tipo rey (8 direcciones)
4. **Turno completo:** Mover ficha + eliminar una casilla
5. **Victoria:** El oponente no puede moverse

## Características Técnicas

- **Evita superposición:** Las fichas no pueden ocupar la misma casilla
- **Cambio de estrategia:** La IA adapta su estrategia según casillas disponibles
- **Interfaz visual:** Tablero cambia de color según la estrategia (rojo/azul)
- **Análisis de rendimiento:** Muestra nodos explorados en versión consola

## Autor

Proyecto desarrollado para el curso de Inteligencia Artificial
Ciberdefensa - Semestre 9

## Notas Técnicas

- Los notebooks están optimizados para Google Colab pero funcionan en cualquier entorno Jupyter
- El juego Isolation incluye validaciones para evitar superposición de fichas
- La IA cambia automáticamente de estrategia según el estado del juego
- Las imágenes del juego son opcionales; si no se encuentran, se usan gráficos de respaldo
- El contador de nodos ayuda a analizar la eficiencia del algoritmo Alpha-Beta