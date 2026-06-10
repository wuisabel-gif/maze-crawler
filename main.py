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

    my_robots = {uid: data for uid, data in obs.robots.items() if data[4] == obs.player}
    enemy_robots = {
        uid: data for uid, data in obs.robots.items() if data[4] != obs.player
    }
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
        parse_coord(key): value for key, value in obs.crystals.items() if value > 0
    }
    visible_nodes = {parse_coord(key) for key in obs.miningNodes}
    remembered_mines = {parse_coord(key): value for key, value in obs.mines.items()}
    friendly_mines = {
        cell
        for cell, value in remembered_mines.items()
        if len(value) >= 3 and value[2] == obs.player
    }
    friendly_mine_energy = sum(
        value[0]
        for value in remembered_mines.values()
        if len(value) >= 3 and value[2] == obs.player
    )

    KNOWN_MINING_NODES.update(visible_nodes)
    KNOWN_MINING_NODES.difference_update(
        {
            cell
            for cell in KNOWN_MINING_NODES
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
        if (
            0 <= mirrored_col < width
            and 0 <= mirrored_idx < len(obs.walls)
            and obs.walls[mirrored_idx] != -1
        ):
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
            cell
            for cell in KNOWN_MINING_NODES
            if cell not in remembered_mines and manhattan(origin, cell) <= limit
        ]

    def nearby_visible_nodes(origin, limit):
        return [
            cell
            for cell in visible_nodes
            if cell not in remembered_mines and manhattan(origin, cell) <= limit
        ]

    def nearby_visible_crystals(origin, limit):
        return [
            cell
            for cell, value in visible_crystal_map.items()
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
            [manhattan(factory_pos, node_cell)]
            + [
                manhattan((my_robots[uid][1], my_robots[uid][2]), node_cell)
                for uid in workers + scouts
            ]
        )
        return collector_distance <= 12

    def can_transfer_to_factory(col, row, energy, threshold):
        if factory_pos is None or energy < threshold:
            return None
        if manhattan((col, row), factory_pos) != 1:
            return None
        for direction in DIRS:
            if next_pos(col, row, direction) == factory_pos and can_move(
                col, row, direction
            ):
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

    def bfs_first_action(start, goals, avoid, depth, init_jump_cd):
        """Search both movement and optional factory jumps."""
        if not goals:
            return None
        goal_set = set(goals)
        queue = deque([(start[0], start[1], 0, None, init_jump_cd)])
        visited = {(start[0], start[1], init_jump_cd)}

        while queue:
            col, row, dist, first_action, jump_cd = queue.popleft()
            if (col, row) in goal_set and dist > 0:
                return first_action
            if dist >= depth:
                continue

            for direction in DIRS:
                if not can_move(col, row, direction):
                    continue
                next_col, next_row = next_pos(col, row, direction)
                if (next_col, next_row) in avoid:
                    continue
                next_jump_cd = max(0, jump_cd - 1)
                state = (next_col, next_row, next_jump_cd)
                if state in visited:
                    continue
                visited.add(state)
                queue.append(
                    (
                        next_col,
                        next_row,
                        dist + 1,
                        first_action or direction,
                        next_jump_cd,
                    )
                )

            if jump_cd == 0:
                for direction in DIRS:
                    if not can_jump(col, row, direction):
                        continue
                    dc, dr = OFFSETS[direction]
                    next_col = col + 2 * dc
                    next_row = row + 2 * dr
                    if (next_col, next_row) in avoid:
                        continue
                    state = (next_col, next_row, config.factoryJumpCooldown)
                    if state in visited:
                        continue
                    visited.add(state)
                    queue.append(
                        (
                            next_col,
                            next_row,
                            dist + 1,
                            first_action or f"JUMP_{direction}",
                            config.factoryJumpCooldown,
                        )
                    )
        return None

    def bfs_move_only(start, goals, avoid, depth):
        if not goals:
            return None
        goal_set = set(goals)
        queue = deque([(start, None, 0)])
        visited = {start}

        while queue:
            pos, first_action, dist = queue.popleft()
            if pos in goal_set and dist > 0:
                return first_action
            if dist >= depth:
                continue

            for direction in ("NORTH", "EAST", "WEST"):
                if not can_move(pos[0], pos[1], direction):
                    continue
                nxt = next_pos(pos[0], pos[1], direction)
                if nxt in avoid or nxt in visited:
                    continue
                visited.add(nxt)
                queue.append((nxt, first_action or direction, dist + 1))

        return None

    def bfs_factory_safe(start, goals, avoid, depth, init_jump_cd, allow_south):
        if not goals:
            return None
        goal_set = set(goals)
        directions = DIRS if allow_south else ("NORTH", "EAST", "WEST")
        queue = deque([(start[0], start[1], 0, None, init_jump_cd)])
        visited = {(start[0], start[1], init_jump_cd)}

        while queue:
            col, row, dist, first_action, jump_cd = queue.popleft()
            if (col, row) in goal_set and dist > 0:
                return first_action
            if dist >= depth:
                continue

            for direction in directions:
                if not can_move(col, row, direction):
                    continue
                next_col, next_row = next_pos(col, row, direction)
                if (next_col, next_row) in avoid:
                    continue
                next_jump_cd = max(0, jump_cd - 1)
                state = (next_col, next_row, next_jump_cd)
                if state in visited:
                    continue
                visited.add(state)
                queue.append(
                    (
                        next_col,
                        next_row,
                        dist + 1,
                        first_action or direction,
                        next_jump_cd,
                    )
                )

            if jump_cd == 0:
                for direction in DIRS:
                    if not can_jump(col, row, direction):
                        continue
                    dc, dr = OFFSETS[direction]
                    next_col = col + 2 * dc
                    next_row = row + 2 * dr
                    if (next_col, next_row) in avoid:
                        continue
                    state = (next_col, next_row, config.factoryJumpCooldown)
                    if state in visited:
                        continue
                    visited.add(state)
                    queue.append(
                        (
                            next_col,
                            next_row,
                            dist + 1,
                            first_action or f"JUMP_{direction}",
                            config.factoryJumpCooldown,
                        )
                    )

        return None

    def reserve_action(col, row, action):
        if action in DIRS:
            reserved.add(next_pos(col, row, action))
        elif action and action.startswith("JUMP_"):
            direction = action.split("_", 1)[1]
            dc, dr = OFFSETS[direction]
            reserved.add((col + 2 * dc, row + 2 * dr))
        else:
            reserved.add((col, row))

    def action_destination(col, row, action):
        if action in DIRS:
            return next_pos(col, row, action)
        if action and action.startswith("JUMP_"):
            direction = action.split("_", 1)[1]
            dc, dr = OFFSETS[direction]
            return col + 2 * dc, row + 2 * dr
        return col, row

    def enemy_factory_reach(factory_data):
        if factory_data is None:
            return set()
        col, row = factory_data[1], factory_data[2]
        reachable = {(col, row)}
        move_cd = move_cooldown(factory_data)
        jump_cd = jump_cooldown(factory_data)
        if move_cd <= 1:
            for direction in DIRS:
                if can_move(col, row, direction):
                    reachable.add(next_pos(col, row, direction))
        if jump_cd == 0:
            for direction in DIRS:
                if can_jump(col, row, direction):
                    dc, dr = OFFSETS[direction]
                    reachable.add((col + 2 * dc, row + 2 * dr))
        return reachable

    def move_cooldown(data):
        return data[5] if len(data) > 5 else 0

    def jump_cooldown(data):
        return data[6] if len(data) > 6 else 0

    def build_cooldown(data):
        return data[7] if len(data) > 7 else 0

    def out_of_time():
        return time.time() - started > 2.6

    units = sorted(my_robots.items(), key=lambda item: (item[1][0], item[0]))
    factory_item = next(
        ((uid, data) for uid, data in units if data[0] == FACTORY), (None, None)
    )
    factory_uid, factory_data = factory_item
    workers = [uid for uid, data in units if data[0] == WORKER]
    scouts = [uid for uid, data in units if data[0] == SCOUT]
    miners = [uid for uid, data in units if data[0] == MINER]
    total_workers = len(workers)
    total_scouts = len(scouts)
    total_miners = len(miners)
    active_miners = [
        uid for uid in miners if my_robots[uid][3] > 0 and my_robots[uid][2] >= south
    ]
    active_workers = [
        uid for uid in workers if my_robots[uid][3] > 0 and my_robots[uid][2] >= south
    ]
    active_scouts = [
        uid for uid in scouts if my_robots[uid][3] > 0 and my_robots[uid][2] >= south
    ]
    stranded_workers = [
        uid for uid in workers if my_robots[uid][3] == 0 and my_robots[uid][2] >= south
    ]
    stranded_scouts = [
        uid for uid in scouts if my_robots[uid][3] == 0 and my_robots[uid][2] >= south
    ]
    stranded_supports = len(stranded_workers) + len(stranded_scouts)
    late_phase = south >= 35
    harvestable_mine_energy = sum(
        value[0]
        for cell, value in remembered_mines.items()
        if len(value) >= 3
        and value[2] == obs.player
        and cell[1] - south > 8
        and mine_collectors_available(cell)
    )
    enemy_factory_data = next(
        (data for data in enemy_robots.values() if data[0] == FACTORY), None
    )
    if enemy_factory_data is not None:
        ENEMY_FACTORY_MEMORY[enemy_player] = (
            enemy_factory_data[1],
            enemy_factory_data[2],
        )
    remembered_enemy_factory_pos = ENEMY_FACTORY_MEMORY.get(enemy_player)
    enemy_factory_cells = enemy_factory_reach(enemy_factory_data)
    if not enemy_factory_cells and remembered_enemy_factory_pos is not None:
        enemy_factory_cells = {
            remembered_enemy_factory_pos,
            (remembered_enemy_factory_pos[0] + 1, remembered_enemy_factory_pos[1]),
            (remembered_enemy_factory_pos[0] - 1, remembered_enemy_factory_pos[1]),
            (remembered_enemy_factory_pos[0], remembered_enemy_factory_pos[1] + 1),
            (remembered_enemy_factory_pos[0], remembered_enemy_factory_pos[1] - 1),
        }
    friendly_support_positions = {
        (my_robots[uid][1], my_robots[uid][2])
        for uid in workers + scouts + miners
        if my_robots[uid][2] >= south
    }
    our_support_count = sum(
        1 for uid in workers + scouts + miners if my_robots[uid][2] >= south
    )
    our_support_energy = sum(
        my_robots[uid][3]
        for uid in workers + scouts + miners
        if my_robots[uid][2] >= south
    )
    enemy_support_count = sum(
        1 for data in enemy_robots.values() if data[0] != FACTORY and data[2] >= south
    )
    enemy_support_energy = sum(
        data[3]
        for data in enemy_robots.values()
        if data[0] != FACTORY and data[2] >= south
    )

    factory_pos = None

    if factory_uid is not None:
        fc, fr, fe = factory_data[1], factory_data[2], factory_data[3]
        factory_pos = (fc, fr)
        factory_action = None
        factory_move_cd = move_cooldown(factory_data)
        factory_jump_cd = jump_cooldown(factory_data)
        factory_build_cd = build_cooldown(factory_data)
        spawn_cell = (fc, fr + 1)
        danger_gap = fr - south
        in_danger = south > 0 and danger_gap <= 4
        forbid_south = danger_gap <= 6
        allow_worker_feed = not in_danger and factory_build_cd > 0 and fe >= 650

        if allow_worker_feed:
            for worker_uid in workers:
                worker = my_robots[worker_uid]
                if manhattan(factory_pos, (worker[1], worker[2])) != 1:
                    continue
                if worker[3] >= 120:
                    continue
                if fe - worker[3] < worker_reserve:
                    continue
                for direction in DIRS:
                    if next_pos(fc, fr, direction) == (
                        worker[1],
                        worker[2],
                    ) and can_move(fc, fr, direction):
                        factory_action = f"TRANSFER_{direction}"
                        break
                if factory_action:
                    break

        if (
            factory_action is None
            and danger_gap <= 3
            and south > 0
            and factory_jump_cd == 0
            and can_jump(fc, fr, "NORTH")
        ):
            factory_action = "JUMP_NORTH"

        if factory_action is None and in_danger and factory_move_cd <= 1:
            urgent_goals = [(col, min(north, fr + 8)) for col in range(width)]
            urgent_avoid = enemy_positions | reserved
            step = bfs_move_only(factory_pos, urgent_goals, urgent_avoid, 20)
            if step is None:
                step = bfs_factory_safe(
                    factory_pos,
                    urgent_goals,
                    enemy_positions,
                    20,
                    factory_jump_cd,
                    False,
                )
            if step is not None:
                factory_action = step

        if (
            factory_action is None
            and factory_move_cd <= 1
            and harvestable_mine_energy >= 350
            and fe <= 500
        ):
            cashout_target = mine_factory_cashout_target()
            if cashout_target is not None:
                step = bfs_factory_safe(
                    factory_pos,
                    [cashout_target],
                    enemy_positions | reserved,
                    20,
                    factory_jump_cd,
                    not forbid_south,
                )
                if step is not None:
                    factory_action = step

        if factory_action is None and factory_move_cd <= 1:
            long_goals = [(col, min(north, fr + 25)) for col in range(width)]
            polite_avoid = enemy_positions | {
                (my_robots[uid][1], my_robots[uid][2])
                for uid in workers + scouts + miners
            }
            step = bfs_factory_safe(
                factory_pos,
                long_goals,
                polite_avoid,
                40,
                factory_jump_cd,
                not forbid_south,
            )
            if step is None:
                step = bfs_factory_safe(
                    factory_pos,
                    long_goals,
                    enemy_positions,
                    40,
                    factory_jump_cd,
                    not forbid_south,
                )
            if step is not None:
                factory_action = step

        if (
            factory_action is None
            and not in_danger
            and factory_build_cd == 0
            and not (get_walls(fc, fr) & WALL_BITS["NORTH"])
        ):
            open_nodes = [
                cell for cell in KNOWN_MINING_NODES if cell not in remembered_mines
            ]
            close_nodes = nearby_open_nodes(factory_pos, 12)
            urgent_visible_nodes = nearby_visible_nodes(factory_pos, 5)
            close_crystals = nearby_visible_crystals(factory_pos, 4)
            no_mine_plan = not open_nodes
            mine_mode = bool(friendly_mines or active_miners)
            cashout_mode = harvestable_mine_energy >= 250
            opening_phase = south <= 3 and fr <= 10
            opening_worker_job = bool(
                close_crystals or (get_walls(fc, fr) & WALL_BITS["NORTH"])
            )
            worker_build_ok = (
                opening_worker_job
                or bool(friendly_mines)
                or harvestable_mine_energy >= 250
            )
            allow_second_worker = (
                worker_build_ok
                and not no_mine_plan
                and not friendly_mines
                and not stranded_supports
                and not late_phase
                and not cashout_mode
                and fe >= 1000
            )
            max_workers = 2 if allow_second_worker else 1
            prospect_scout_ok = (
                (no_mine_plan or opening_phase)
                and total_scouts == 0
                and not active_workers
                and not miners
                and stranded_supports == 0
                and not late_phase
                and fe
                >= max(
                    700 if opening_phase else 900,
                    scout_reserve + (200 if opening_phase else 350),
                )
                and (south == 0 or danger_gap >= 8)
            )
            followup_scout_ok = (
                opening_phase
                and total_scouts == 0
                and not miners
                and len(active_workers) <= 1
                and stranded_supports == 0
                and not urgent_visible_nodes
                and fe >= max(650, scout_reserve + 120)
            )
            scout_floor = scout_reserve + (250 if no_mine_plan else 150)
            scout_room_ok = (
                stranded_supports == 0 and danger_gap >= 10 and fe >= scout_floor
            )
            mine_room_ok = (south == 0 or danger_gap >= 8) and fe >= max(
                460, config.minerCost + 160
            )
            late_miner_ok = (
                south < 22 or (fe >= 850 and danger_gap >= 16) or danger_gap >= 22
            )
            build_pressure_ok = (
                stranded_supports == 0
                and (not friendly_mines or fe >= 1200)
                and (not mine_mode or fe >= 700)
                and (not late_phase or fe >= 950)
                and (not cashout_mode or fe >= 1050)
            )
            scout_mine_followup_ok = (
                build_pressure_ok
                and close_nodes
                and not friendly_mines
                and not cashout_mode
                and total_miners < 1
                and (len(active_workers) + len(active_scouts)) >= 1
                and fe >= max(500, config.minerCost + 180)
                and (opening_phase or danger_gap >= 10)
                and late_miner_ok
            )
            spawn_blocked = spawn_cell in occupied_now
            if not spawn_blocked:
                if (
                    build_pressure_ok
                    and urgent_visible_nodes
                    and not friendly_mines
                    and not cashout_mode
                    and total_miners < 1
                    and mine_room_ok
                    and late_miner_ok
                ):
                    factory_action = "BUILD_MINER"
                elif prospect_scout_ok:
                    factory_action = "BUILD_SCOUT"
                elif followup_scout_ok:
                    factory_action = "BUILD_SCOUT"
                elif (
                    build_pressure_ok
                    and len(active_workers) < max_workers
                    and total_workers < (2 if allow_second_worker else 1)
                    and not cashout_mode
                    and worker_build_ok
                    and (
                        not opening_phase
                        or opening_worker_job
                        or len(active_workers) > 0
                        or len(active_miners) > 0
                    )
                    and (
                        not friendly_mines or (len(active_workers) == 0 and fe >= 1300)
                    )
                    and fe >= worker_reserve
                ):
                    factory_action = "BUILD_WORKER"
                elif scout_mine_followup_ok:
                    factory_action = "BUILD_MINER"
                elif (
                    build_pressure_ok
                    and not friendly_mines
                    and not no_mine_plan
                    and not cashout_mode
                    and total_scouts < 1
                    and len(active_workers) <= 1
                    and scout_room_ok
                ):
                    factory_action = "BUILD_SCOUT"
                elif (
                    build_pressure_ok
                    and not friendly_mines
                    and not no_mine_plan
                    and not cashout_mode
                    and total_scouts < 1
                    and len(active_workers) >= 1
                    and scout_room_ok
                    and fe >= scout_reserve + 250
                ):
                    factory_action = "BUILD_SCOUT"

        if factory_action is not None and not factory_action.startswith("BUILD_"):
            destination = action_destination(fc, fr, factory_action)
            if destination in friendly_support_positions:
                safer_action = None
                if in_danger and factory_move_cd <= 1:
                    urgent_goals = [(col, min(north, fr + 8)) for col in range(width)]
                    safer_action = bfs_move_only(
                        factory_pos,
                        urgent_goals,
                        enemy_positions | reserved | friendly_support_positions,
                        20,
                    )
                    if safer_action is None:
                        safer_action = bfs_factory_safe(
                            factory_pos,
                            urgent_goals,
                            enemy_positions | friendly_support_positions,
                            20,
                            factory_jump_cd,
                            False,
                        )
                elif factory_move_cd <= 1:
                    long_goals = [(col, min(north, fr + 25)) for col in range(width)]
                    safer_action = bfs_factory_safe(
                        factory_pos,
                        long_goals,
                        enemy_positions | friendly_support_positions,
                        40,
                        factory_jump_cd,
                        not forbid_south,
                    )
                if (
                    safer_action is not None
                    and action_destination(fc, fr, safer_action)
                    not in friendly_support_positions
                ):
                    factory_action = safer_action
                else:
                    factory_action = "IDLE"

        if (
            factory_action is not None
            and enemy_factory_data is not None
            and (
                enemy_support_count > our_support_count
                or (
                    enemy_support_count == our_support_count
                    and enemy_support_energy > our_support_energy
                )
            )
            and manhattan(factory_pos, (enemy_factory_data[1], enemy_factory_data[2]))
            <= 4
        ):
            destination = action_destination(fc, fr, factory_action)
            if destination in enemy_factory_cells:
                safer_action = None
                if in_danger and factory_move_cd <= 1:
                    urgent_goals = [(col, min(north, fr + 8)) for col in range(width)]
                    safer_action = bfs_move_only(
                        factory_pos,
                        urgent_goals,
                        enemy_positions | reserved | enemy_factory_cells,
                        20,
                    )
                    if safer_action is None:
                        safer_action = bfs_factory_safe(
                            factory_pos,
                            urgent_goals,
                            enemy_positions | enemy_factory_cells,
                            20,
                            factory_jump_cd,
                            False,
                        )
                elif factory_move_cd <= 1:
                    long_goals = [(col, min(north, fr + 25)) for col in range(width)]
                    safer_avoid = (
                        enemy_positions
                        | enemy_factory_cells
                        | {
                            (my_robots[uid][1], my_robots[uid][2])
                            for uid in workers + scouts + miners
                        }
                    )
                    safer_action = bfs_factory_safe(
                        factory_pos,
                        long_goals,
                        safer_avoid,
                        40,
                        factory_jump_cd,
                        not forbid_south,
                    )
                if (
                    safer_action is not None
                    and action_destination(fc, fr, safer_action)
                    not in enemy_factory_cells
                ):
                    factory_action = safer_action
                elif factory_action.startswith("BUILD_") or destination != factory_pos:
                    factory_action = "IDLE"

        actions[factory_uid] = factory_action or "IDLE"
        reserve_action(fc, fr, actions[factory_uid])

    for worker_uid in workers:
        if out_of_time():
            actions[worker_uid] = "IDLE"
            reserve_action(my_robots[worker_uid][1], my_robots[worker_uid][2], "IDLE")
            continue
        worker = my_robots[worker_uid]
        wc, wr, we = worker[1], worker[2], worker[3]
        worker_action = None
        gap = wr - south

        transfer_action = can_transfer_to_factory(wc, wr, we, 120)
        mine_target = best_harvestable_mine((wc, wr), 12, 140)
        if transfer_action is not None:
            worker_action = transfer_action
        elif mine_target is not None and we <= 180 and move_cooldown(worker) <= 1:
            step = bfs_first_action(
                (wc, wr), [mine_target], reserved | enemy_positions, 18, 999
            )
            if step is not None:
                worker_action = step
        elif (get_walls(wc, wr) & WALL_BITS["NORTH"]) and we >= config.wallRemoveCost:
            worker_action = "REMOVE_NORTH"

        if worker_action is None and move_cooldown(worker) <= 1:
            if factory_pos is not None and gap <= 4:
                target = (factory_pos[0], min(north, factory_pos[1] + 5))
                goals = [target]
            else:
                crystal_target = best_crystal((wc, wr))
                if (
                    crystal_target is not None
                    and manhattan((wc, wr), crystal_target) <= 10
                ):
                    claimed_targets.add(crystal_target)
                    goals = [crystal_target]
                elif factory_pos is not None:
                    goals = [(factory_pos[0], min(north, factory_pos[1] + 5))]
                else:
                    goals = [(wc, min(north, wr + 5))]

            step = bfs_first_action(
                (wc, wr), goals, reserved | enemy_positions, 25, 999
            )
            if step is None:
                frontier = best_frontier((wc, wr))
                if frontier is not None:
                    step = bfs_first_action(
                        (wc, wr), [frontier], reserved | enemy_positions, 20, 999
                    )
            if step is not None:
                worker_action = step

        actions[worker_uid] = worker_action or "IDLE"
        reserve_action(wc, wr, actions[worker_uid])

    for miner_uid in miners:
        if out_of_time():
            actions[miner_uid] = "IDLE"
            reserve_action(my_robots[miner_uid][1], my_robots[miner_uid][2], "IDLE")
            continue
        miner = my_robots[miner_uid]
        mc, mr, me = miner[1], miner[2], miner[3]
        miner_pos = (mc, mr)
        miner_action = None
        memory = MINER_MEMORY.get(miner_uid, {"pos": miner_pos, "stale": 0})
        stale_turns = memory["stale"] + 1 if memory["pos"] == miner_pos else 0
        MINER_MEMORY[miner_uid] = {"pos": miner_pos, "stale": stale_turns}
        node_target = best_node(miner_pos)
        viable_node = node_viable_for_miner(miner_pos, node_target, me)
        miner_stale = stale_turns >= 4
        opening_stall = (
            mr <= south + 10
            and stale_turns >= 2
            and not nearby_visible_nodes(miner_pos, 4)
        )
        opening_no_signal = (
            factory_pos is not None
            and mr <= south + 12
            and manhattan(miner_pos, factory_pos) <= 10
            and stale_turns >= 1
            and not nearby_visible_nodes(miner_pos, 6)
        )
        miner_abort = (
            not viable_node
            or miner_stale
            or opening_stall
            or opening_no_signal
            or mr - south <= 6
            or (
                factory_pos is not None
                and my_robots[factory_uid][3] <= 260
                and me >= 120
            )
            or (friendly_mines and not nearby_visible_nodes(miner_pos, 6))
            or (
                harvestable_mine_energy >= 400
                and factory_pos is not None
                and my_robots[factory_uid][3] <= 500
            )
        )

        if (
            miner_pos in KNOWN_MINING_NODES
            and me >= config.transformCost + 40
            and mine_harvest_viable(miner_pos)
            and (friendly_mine_energy < 850 or factory_data[3] >= 850)
        ):
            miner_action = "TRANSFORM"
            MINER_MEMORY.pop(miner_uid, None)
        elif (
            move_cooldown(miner) <= 1
            and factory_pos is not None
            and manhattan(miner_pos, factory_pos) == 1
            and miner_abort
            and me >= 40
        ):
            for direction in DIRS:
                if next_pos(mc, mr, direction) == factory_pos and can_move(
                    mc, mr, direction
                ):
                    miner_action = f"TRANSFER_{direction}"
                    break
        elif move_cooldown(miner) <= 1 and factory_pos is not None and mr - south > 4:
            if viable_node:
                claimed_targets.add(node_target)
                miner_action = bfs_first_action(
                    miner_pos, [node_target], reserved | enemy_positions, 30, 999
                )
            elif miner_abort and manhattan(miner_pos, factory_pos) <= 24:
                miner_action = bfs_first_action(
                    miner_pos, [factory_pos], reserved | enemy_positions, 24, 999
                )
            if miner_action is None:
                fallback = (factory_pos[0], min(north, factory_pos[1] + 6))
                miner_action = bfs_first_action(
                    miner_pos, [fallback], reserved | enemy_positions, 16, 999
                )

        actions[miner_uid] = miner_action or "IDLE"
        reserve_action(mc, mr, actions[miner_uid])

    for scout_uid in scouts:
        if out_of_time():
            actions[scout_uid] = "IDLE"
            reserve_action(my_robots[scout_uid][1], my_robots[scout_uid][2], "IDLE")
            continue
        scout = my_robots[scout_uid]
        sc, sr, se = scout[1], scout[2], scout[3]
        scout_pos = (sc, sr)
        scout_action = None

        if (
            factory_pos is not None
            and manhattan(scout_pos, factory_pos) == 1
            and se >= 50
        ):
            for direction in DIRS:
                if next_pos(sc, sr, direction) == factory_pos and can_move(
                    sc, sr, direction
                ):
                    scout_action = f"TRANSFER_{direction}"
                    break

        if scout_action is None and move_cooldown(scout) <= 0:
            goals = None
            mine_target = best_harvestable_mine(scout_pos, 14, 140)
            if mine_target is not None and se <= 70:
                goals = [mine_target]
            elif se > 80 and factory_pos is not None:
                goals = [factory_pos]
            else:
                crystal_target = best_crystal(scout_pos)
                if (
                    crystal_target is not None
                    and manhattan(scout_pos, crystal_target) <= 10
                ):
                    claimed_targets.add(crystal_target)
                    goals = [crystal_target]
                else:
                    frontier = best_frontier(scout_pos)
                    if frontier is not None:
                        goals = [(col, min(north, sr + 12)) for col in range(width)]

            if goals:
                scout_action = bfs_first_action(
                    scout_pos, goals, reserved | enemy_positions, 30, 999
                )

        actions[scout_uid] = scout_action or "IDLE"
        reserve_action(sc, sr, actions[scout_uid])

    return actions


def act(obs, config):
    """Fail closed so the submission does not error out on Kaggle."""
    try:
        return agent(obs, config)
    except Exception:
        return {}
