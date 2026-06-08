"""Factory-centric convoy bot with symmetry-aware BFS planning."""

from collections import deque
import time


FACTORY = 0
SCOUT = 1
WORKER = 2
MINER = 3

DIRS = ("NORTH", "EAST", "WEST", "SOUTH")
OFFSETS = {
    "NORTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
    "SOUTH": (0, -1),
}
WALL_BITS = {"NORTH": 1, "EAST": 2, "SOUTH": 4, "WEST": 8}

KNOWN_MINING_NODES = set()
MINER_MEMORY = {}
ENEMY_FACTORY_MEMORY = {}


def parse_coord(text):
    col, row = text.split(",")
    return int(col), int(row)


def agent(obs, config):
    started = time.time()
    actions = {}
    width = config.width
    south = obs.southBound
    north = obs.northBound
    scout_reserve = max(200, config.scoutCost + 150)
    worker_reserve = max(400, config.workerCost + 200)
    miner_reserve = max(550, config.minerCost + 250)

    my_robots = {uid: data for uid, data in obs.robots.items() if data[4] == obs.player}
    enemy_robots = {uid: data for uid, data in obs.robots.items() if data[4] != obs.player}
    enemy_player = 1 - obs.player
    MINER_MEMORY_KEYS = set(my_robots)
    for stale_uid in list(MINER_MEMORY):
        if stale_uid not in MINER_MEMORY_KEYS:
            del MINER_MEMORY[stale_uid]
    enemy_positions = {(data[1], data[2]) for data in enemy_robots.values()}
    occupied_now = {(data[1], data[2]) for data in obs.robots.values()}
    reserved = set()
    claimed_targets = set()

    visible_crystal_map = {
        parse_coord(key): value
        for key, value in obs.crystals.items()
        if value > 0
    }
    visible_nodes = {parse_coord(key) for key in obs.miningNodes}
    remembered_mines = {parse_coord(key): value for key, value in obs.mines.items()}
    friendly_mines = {
        cell for cell, value in remembered_mines.items()
        if len(value) >= 3 and value[2] == obs.player
    }
    friendly_mine_energy = sum(
        value[0] for value in remembered_mines.values()
        if len(value) >= 3 and value[2] == obs.player
    )

    KNOWN_MINING_NODES.update(visible_nodes)
    KNOWN_MINING_NODES.difference_update(
        {
            cell for cell in KNOWN_MINING_NODES
            if cell[1] < south or cell[1] > north or cell in remembered_mines
        }
    )

    def get_walls(col, row):
        """Return wall bitmask, using east-west symmetry when unseen."""
        idx = (row - south) * width + col
        if 0 <= col < width and 0 <= idx < len(obs.walls) and obs.walls[idx] != -1:
            return obs.walls[idx]

        mirrored_col = width - 1 - col
        mirrored_idx = (row - south) * width + mirrored_col
        if 0 <= mirrored_col < width and 0 <= mirrored_idx < len(obs.walls) and obs.walls[mirrored_idx] != -1:
            value = obs.walls[mirrored_idx]
            mirrored = value & 5
            if value & 2:
                mirrored |= 8
            if value & 8:
                mirrored |= 2
            return mirrored
        return 0

    def can_move(col, row, direction):
        dc, dr = OFFSETS[direction]
        next_col = col + dc
        next_row = row + dr
        if not (0 <= next_col < width and south <= next_row <= north):
            return False
        return not (get_walls(col, row) & WALL_BITS[direction])

    def can_jump(col, row, direction):
        dc, dr = OFFSETS[direction]
        next_col = col + 2 * dc
        next_row = row + 2 * dr
        if not (0 <= next_col < width and south <= next_row <= north):
            return False
        return get_walls(next_col, next_row) != 15

    def next_pos(col, row, direction):
        dc, dr = OFFSETS[direction]
        return col + dc, row + dr

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def best_crystal(origin):
        best = None
        best_score = None
        for cell, value in visible_crystal_map.items():
            score = manhattan(origin, cell) - (value / 18.0)
            if cell in claimed_targets:
                score += 4
            if best is None or score < best_score:
                best = cell
                best_score = score
        return best

    def best_node(origin):
        best = None
        best_score = None
        for cell in KNOWN_MINING_NODES:
            score = manhattan(origin, cell)
            if cell in claimed_targets:
                score += 6
            if best is None or score < best_score:
                best = cell
                best_score = score
        return best
