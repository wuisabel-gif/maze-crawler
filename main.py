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

    def nearby_open_nodes(origin, limit):
        return [
            cell for cell in KNOWN_MINING_NODES
            if cell not in remembered_mines and manhattan(origin, cell) <= limit
        ]

    def nearby_visible_nodes(origin, limit):
        return [
            cell for cell in visible_nodes
            if cell not in remembered_mines and manhattan(origin, cell) <= limit
        ]

    def nearby_visible_crystals(origin, limit):
        return [
            cell for cell, value in visible_crystal_map.items()
            if value >= 18 and manhattan(origin, cell) <= limit
        ]

    def node_viable_for_miner(origin, node, energy):
        if node is None or node in remembered_mines:
            return False
        distance = manhattan(origin, node)
        if distance > 14:
            return False
        if node[1] - south <= 4:
            return False
        if energy < config.transformCost + 20 and distance > 6:
            return False
        return True

    def best_friendly_mine(origin, max_distance=12, min_energy=150):
        best = None
        best_score = None
        for cell, value in remembered_mines.items():
            if len(value) < 3 or value[2] != obs.player:
                continue
            mine_energy = value[0]
            if mine_energy < min_energy:
                continue
            distance = manhattan(origin, cell)
            if distance > max_distance:
                continue
            score = distance - (mine_energy / 250.0)
            if best is None or score < best_score:
                best = cell
                best_score = score
        return best

    def mine_collectors_available(cell):
        if factory_pos is not None and manhattan(factory_pos, cell) <= 12:
            return True
        for uid in workers + scouts:
            if manhattan((my_robots[uid][1], my_robots[uid][2]), cell) <= 10:
                return True
        return False

    def best_harvestable_mine(origin, max_distance=14, min_energy=180):
        best = None
        best_score = None
        for cell, value in remembered_mines.items():
            if len(value) < 3 or value[2] != obs.player:
                continue
            if cell[1] - south <= 8:
                continue
            mine_energy = value[0]
            if mine_energy < min_energy or not mine_collectors_available(cell):
                continue
            distance = manhattan(origin, cell)
            if distance > max_distance:
                continue
            score = distance - (mine_energy / 220.0)
            if best is None or score < best_score:
                best = cell
                best_score = score
        return best

    def mine_factory_cashout_target():
        if factory_pos is None:
            return None
        return best_harvestable_mine(factory_pos, 12, 220)

    def mine_harvest_viable(node_cell):
        if factory_pos is None:
            return False
        if node_cell[1] - south <= 10:
            return False
        collector_distance = min(
            [manhattan(factory_pos, node_cell)] +
            [manhattan((my_robots[uid][1], my_robots[uid][2]), node_cell) for uid in workers + scouts]
        )
        return collector_distance <= 12

    def can_transfer_to_factory(col, row, energy, threshold):
        if factory_pos is None or energy < threshold:
            return None
        if manhattan((col, row), factory_pos) != 1:
            return None
        for direction in DIRS:
            if next_pos(col, row, direction) == factory_pos and can_move(col, row, direction):
                return f"TRANSFER_{direction}"
        return None

    def best_frontier(origin):
        best = None
        best_score = None
        for row in range(south, north + 1):
            for col in range(width):
                idx = (row - south) * width + col
                if idx >= len(obs.walls) or obs.walls[idx] == -1:
                    score = manhattan(origin, (col, row)) - (row * 0.15)
                    if best is None or score < best_score:
                        best = (col, row)
                        best_score = score
        return best

    