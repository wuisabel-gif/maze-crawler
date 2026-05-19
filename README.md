# Maze Crawler Agent

This project is an ongoing attempt to build a competitive agent for Kaggle's Maze Crawler challenge. The core problem is not just moving units through a maze, but making good decisions under fog of war, limited energy, scrolling pressure, and a high penalty for small tactical mistakes. The agent has been built incrementally, starting from simple rule-based movement and growing toward a more structured decision system with search, memory, and role-based coordination.

![Maze Crawler match example](assets/competition_example.gif)

## Project Goal

The goal of the agent is to survive while still building a meaningful energy economy. In practice, that means balancing several competing objectives at once:

- keep the factory from falling behind the scroll
- explore enough of the maze to find crystals and mining nodes
- turn miners into long-term energy sources when good opportunities appear
- avoid self-destructive friendly collisions
- move units intelligently through partially known terrain

Rather than jumping straight into machine learning, this project focuses on building a strong algorithmic baseline first. That makes the behavior easier to reason about, easier to debug, and much more useful as a foundation for later learning-based improvements.

## Design Approach

The development process has followed a staged strategy.

At the beginning, the agent used simple greedy movement rules: move north when possible, collect nearby resources, and react locally to walls. That was enough to get a legal bot running, but it exposed the main weaknesses of naive policies very quickly. Units looped in corridors, miners got stuck taking locally good but globally bad routes, and scouts often wasted turns because they had no memory of where they had just been.

The next step was to add persistent per-unit memory. Scouts and miners now keep short movement histories so they are less likely to oscillate between the same few cells. This added a lightweight tabu-style behavior without requiring a full global planner for every situation. The reasoning here was simple: in a maze with partial visibility, even a small amount of memory can dramatically improve movement quality.

After that, the agent was upgraded from one-step greedy movement to actual pathfinding on known terrain. Once enough of the maze has been discovered, units can use A* search to route around walls instead of repeatedly making short-sighted choices. This was an important shift in the project: movement stopped being purely reactive and became more plan-driven.

## Current Agent Logic

The current bot uses a role-based control system.

- The factory acts as the strategic anchor. It decides when to move north for survival, when to jump, and when to spend energy on scouts, workers, or miners.
- Scouts are used for fast exploration and crystal gathering. When they accumulate enough energy, they prioritize returning to the factory so that value is not stranded in fragile units.
- Workers are utility units. Their main job is to reduce movement bottlenecks, especially when the factory is blocked by a wall and needs help progressing.
- Miners are the long-term economy play. They try to reach mining nodes efficiently and convert into mines when the position is worth committing to.

This division of labor keeps the policy understandable while still allowing different unit types to serve different strategic purposes.

## Algorithms and Heuristics

The current implementation is built around a few practical algorithmic ideas:

- A* pathfinding for routing through discovered sections of the maze
- greedy target selection for choosing nearby crystals, frontier cells, and mining nodes
- tabu-style recent-cell memory to reduce loops when the map is incomplete
- collision avoidance heuristics to reduce friendly fire and wasted turns
- role-based action policies so each robot type contributes differently to the overall plan

This combination was chosen because the environment mixes long-term planning with incomplete information. Pure graph search is not enough when the world is only partially visible, and pure greedy movement is not enough once the maze becomes more complex. The current design tries to use search where it is reliable and heuristics where the information is still uncertain.

## Thought Process Behind the Build

The main philosophy behind this project has been to solve the most damaging failure modes first.

First, the agent needed to become safe: legal movement, no walking off the board, and better handling of scroll pressure. Next, it needed to become less wasteful: fewer friendly collisions, fewer oscillations, and better use of unit roles. Only after that did it make sense to invest in better routing with search.

That order matters. There is not much value in adding sophisticated pathfinding to a bot that still loses games because it accidentally trades away energy, gets trapped in short loops, or fails basic survival checks. Each layer of improvement has been added to make the next layer more useful.

## Why This Project Matters

This project is a good example of applied algorithmic decision-making under uncertainty. It combines elements of pathfinding, multi-agent coordination, resource management, and partial-observability reasoning in a way that is concrete and testable. It also creates a strong baseline for future extensions such as:

- broader map memory and exploration policies
- better assignment of scouts across multiple resource targets
- deeper search for tactical engagements
- simulation-based planning
- reinforcement learning or imitation learning on top of the current heuristic framework

## USC Coursework Connection

This project also reflects ideas from USC's `CSCI 103` and `CSCI 104`. The implementation relies on the programming discipline, modular design, and debugging practices emphasized in `CSCI 103`, while many of the agent's decision-making systems were directly inspired by concepts from `CSCI 104`.

One especially direct connection is the A* pathfinding work from the `CSCI 104` [Rush Hour homework](https://bytes.usc.edu/cs104/homework/hw3/#problem-5---rush-hour-40). Building the bot became a practical way to apply data structures and algorithms in a dynamic environment rather than only through isolated homework problems. Concepts such as graph traversal, `DFS`, shortest-path search, heuristic-driven decision making, recursion, state management, and algorithmic tradeoffs became much more tangible once they directly affected how units behaved inside the maze.

For example:

- `DFS`-style exploration ideas influenced how scouts reason about partially discovered terrain and frontier expansion
- A* search inspired the pathfinding layer used once enough map information is available
- heuristic evaluation helps balance exploration, survival, and resource collection under uncertainty
- persistent unit memory functions similarly to lightweight tabu-search behavior by discouraging repetitive movement loops
- role-based coordination mirrors the kind of systems-level decomposition emphasized in algorithmic design

Working on the project also reinforced an important lesson from `CSCI 104`: an algorithm is not just about correctness, but also about tradeoffs between efficiency, flexibility, memory, and behavior under imperfect conditions. In that sense, the bot became more than a Kaggle competition entry. It became a larger systems-style application of core computer science concepts to real-time decision making under uncertainty.

## Current Status

The agent is functional and has moved beyond the starter-policy stage. It now includes persistent unit memory, safer movement rules, A*-based path planning on discovered terrain, and differentiated behavior across scouts, workers, miners, and the factory. The project is still in progress, with the next major focus being stronger local evaluation through simulation and more robust strategic tuning.
