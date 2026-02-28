# Juego Isolation con Fichas Individuales

Este repositorio contiene la implementación del juego Isolation con inteligencia artificial usando algoritmo Alpha-Beta pruning y selección de dificultad.

## Juego de Isolation con Fichas Individuales
**Archivo:** `Isolation_Game_Individual_Tiles.py`

Implementación avanzada del juego Isolation con fichas individuales para cada jugador y múltiples niveles de dificultad.

**Características:**
- Tablero de 5x5 con fichas individuales
- Algoritmo Minimax con poda Alpha-Beta
- 4 niveles de dificultad (Fácil, Medio, Difícil, Experto)
- Heurística adaptativa con 3 componentes principales
- Interfaz gráfica mejorada con pygame
- Sistema de selección de dificultad al inicio

## Componentes de la Heurística de IA

La inteligencia artificial utiliza una heurística avanzada con **3 componentes principales**:

### 1. **Detección de Estados Terminales**
- Identifica automáticamente finales de juego (victoria, derrota, empate)
- Asigna valores absolutos (±200) para garantizar decisiones correctas
- Prioridad máxima sobre otros factores

### 2. **Estrategia Adaptativa (Ofensiva/Defensiva)**
- **Estrategia Ofensiva** (>12 casillas disponibles): Maximiza movilidad propia
- **Estrategia Defensiva** (≤12 casillas disponibles): Restringe movilidad del oponente
- Transición automática según el progreso del juego

### 3. **Control del Centro**
- Favorece posiciones centrales en el tablero
- Usa distancia Manhattan al centro (posición 2,2)
- Componente secundario que complementa la estrategia principal

## Instalación

1. Clona o descarga este repositorio
2. Instala las dependencias:

```bash
pip install pygame numpy
```

## Uso

### Ejecutar el Juego
Ejecuta directamente el archivo Python:

```bash
python Isolation_Game_Individual_Tiles.py
```

Al iniciar, podrás seleccionar entre 4 niveles de dificultad:
- **Fácil** (Profundidad 1): IA básica para principiantes
- **Medio** (Profundidad 2): IA intermedia con mejor planificación
- **Difícil** (Profundidad 3): IA avanzada con análisis profundo
- **Experto** (Profundidad 4): IA máxima con estrategia superior

## Reglas del Juego

El Isolation es un juego de estrategia para dos jugadores:

1. **Objetivo:** Ser el último jugador que pueda moverse
2. **Tablero:** 5x5 casillas con fichas individuales
3. **Movimientos:** Tipo rey (8 direcciones)
4. **Turno completo:** Mover ficha + eliminar una casilla del tablero
5. **Victoria:** El oponente no puede moverse

## Algoritmo Alpha-Beta

### Características Técnicas
- **Búsqueda:** Minimax con poda alpha-beta eficiente
- **Heurística:** 3 componentes (terminales, estrategia adaptativa, control del centro)
- **Profundidad:** Variable según dificultad (1-4 niveles)
- **Optimización:** Prevención de superposición y estados inválidos

### Análisis de Rendimiento por Dificultad
- **Fácil (Depth 1):** ~20-50 nodos explorados (instantáneo)
- **Medio (Depth 2):** ~500-1000 nodos explorados (rápido)
- **Difícil (Depth 3):** ~5000-15000 nodos explorados (tiempo razonable)
- **Experto (Depth 4):** >50000 nodos explorados (fuerte pero más lento)

## Dependencias

- **pygame**: Interfaz gráfica del juego
- **numpy**: Operaciones numéricas y matrices

## Autor

Proyecto desarrollado para el curso de Inteligencia Artificial
