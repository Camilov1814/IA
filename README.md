# Proyecto de Inteligencia Artificial

Este repositorio contiene implementaciones de algoritmos de inteligencia artificial desarrollados para el curso de Ciberdefensa, Semestre 9.



### Juego de Aislamiento con Algoritmo Alpha-Beta
**Archivo:** `Isolation_alpha_betav2.ipynb`

Implementación del juego Isolation con inteligencia artificial usando algoritmo Alpha-Beta pruning.

**Características:**
- Tablero de 5x5
- Algoritmo Minimax con poda Alpha-Beta
- Heurística adaptativa (ofensiva-defensiva)
- Interfaz gráfica con pygame
- Optimizaciones de memoria para mayor profundidad de búsqueda

**Estrategias de IA:**
- **Estrategia Ofensiva:** Maximiza la movilidad propia (>12 casillas disponibles)
- **Estrategia Defensiva:** Minimiza la movilidad del oponente (≤12 casillas disponibles)

**Modos de juego disponibles:**
1. `play_isolation_gui_optimized()` - Interfaz gráfica con imágenes personalizadas
2. `play_isolation_gui()` - Interfaz gráfica estándar
3. `play_isolation_optimized()` - Consola optimizada (depth 4)
4. `play_isolation()` - Versión original por consola

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

# Juego por consola optimizado
play_isolation_optimized()
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

### Algoritmo Genético
- **Selección:** Método de la ruleta
- **Cruce:** Un punto (one-point crossover)
- **Mutación:** Flip de un bit
- **Función objetivo:** Maximización del valor total respetando la capacidad

### Alpha-Beta Pruning
- **Búsqueda:** Minimax con poda alpha-beta
- **Heurística:** Evaluación de movilidad con control del centro
- **Optimizaciones:** Tabla de transposición y gestión de memoria
- **Profundidad:** Configurable (depth 3-4 recomendado)

## Autor

Proyecto desarrollado para el curso de Inteligencia Artificial


## Notas Técnicas

- Los notebooks están optimizados para Google Colab pero funcionan en cualquier entorno Jupyter
- El juego Isolation incluye validaciones para evitar superposición de fichas
- La IA cambia automáticamente de estrategia según el estado del juego
- Las imágenes del juego son opcionales; si no se encuentran, se usan gráficos de respaldo
