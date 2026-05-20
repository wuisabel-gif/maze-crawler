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

## Progress Update

### 1. Search and Stability

One of the most encouraging milestones so far was seeing the bot improve from roughly the `400+` range to the `670+` range on the competition ladder. While that jump does not prove the agent is "solved," it does suggest that the recent architectural changes made the policy substantially more stable and less wasteful.

The improvement seems to come from a few specific changes working together:

- replacing mostly local greedy movement with more deliberate search-based planning
- improving factory survival through better northward routing and jump-aware navigation
- reducing friendly interference through destination reservation and cleaner unit coordination
- using maze symmetry to make better movement decisions before the full map is visible
- preserving economically useful information such as mining-node locations instead of repeatedly rediscovering them

In practical terms, the newer versions appear to lose fewer games to avoidable mistakes. Earlier versions often wasted turns in loops, took weaker local routes, or failed to convert partial map knowledge into better movement decisions. The updated versions behave more consistently, which likely matters a lot in a ladder setting where avoiding bad losses can be just as important as finding flashy wins.

This update also reinforced a useful lesson for the project as a whole: performance gains did not come from one isolated trick, but from tightening the system end to end. Better search, better state management, and better coordination each contributed a little, and together they produced a noticeably stronger bot.

### 2. Factory Danger Mode

Another important improvement came from replay-driven debugging rather than from adding a brand-new algorithm. After analyzing a losing episode, it became clear that the bot was still making the wrong choices under heavy scroll pressure: the factory could continue spending energy on support behavior, drift sideways or backward, and even spawn units when survival should have been the only priority.

To address that, the agent was updated with a more explicit factory danger mode. When the factory gets too close to the southern boundary, normal convoy logic is temporarily overridden. In that state, the bot stops feeding workers, stops spawning new units, and switches into a survival-only routing mode focused on moving `NORTH`, `EAST`, or `WEST` without allowing low-value detours. Jump logic also remains available as an emergency escape tool.

This change matters because the previous losses were not always caused by weak pathfinding in the abstract. Sometimes the bot already knew enough to survive, but its policy priorities were wrong. The factory was still behaving like a coordinator when it needed to behave like a fleeing VIP. The May 20 update made that distinction much sharper.

More broadly, this was a useful reminder that strong competition bots are often improved less by adding complexity and more by removing bad behavior in the highest-risk states. In this case, the replay showed that late-game survival logic needed to be stricter, and tightening that rule set was likely more valuable than adding another economic or exploration feature.

### 3. Energy Reserve Fix

Another replay exposed a different type of failure: the factory was not dying because it got trapped too low on the board, but because it slowly bankrupted itself. In that episode, the factory remained alive and reasonably well-positioned for a long time, but by roughly turn `191` it had reached `0` energy. From that point onward, it was effectively a dead object sitting on the board until the scroll finally removed it much later.

This loss showed that the problem was not mainly pathfinding. It was an economic collapse caused by overspending on workers and then transferring too much energy into them. The factory was behaving like an unlimited battery for its support units even when preserving its own energy reserve should have been the higher priority.

To address that, the agent was updated with stricter factory energy reserve rules. Worker, scout, and miner production now require larger minimum energy buffers, and factory-to-worker transfers are only allowed when the factory is both safe and meaningfully rich. In other words, the bot now treats factory energy as a protected survival resource rather than something that can always be spent on support behavior.

This update also coincided with another meaningful ladder improvement, with the bot moving from roughly the `670+` range into the `730+` range. As with the earlier score jump, that increase should not be read as proof that the agent is finished, but it does suggest that protecting factory energy made the policy more stable over long games and reduced another major source of avoidable losses.

This change reinforced another important lesson from the project: a bot can still lose even when it survives physically if it stops functioning economically. The replay made it clear that long-term survival depends not just on staying ahead of the scroll, but also on protecting enough factory energy to remain an active decision-maker deep into the game.

### 4. Early Mine Economy Response

![Battle against AI TOOK MY JOB AND YOUR JOB!](assets/battle_may_19.gif)

Another important lesson came from losing to a bot named `AI TOOK MY JOB AND YOUR JOB!`. That replay showed a different strategic weakness: even when the convoy logic was relatively stable, the agent could still lose badly to an opponent that established an early mine economy and then snowballed factory energy from it.

In that match, the opponent transformed a miner into a mine very early and used that long-term income source to outscale the convoy-based strategy. Their factory energy kept compounding while the bot continued investing mostly in workers and survival structure. The result was not a sudden tactical collapse, but a slower strategic defeat caused by being economically outclassed.

To address that, the miner policy was updated to respond more aggressively when known mining nodes are nearby and realistically reachable. The bot still treats factory survival as the top priority, but it is now more willing to open an early miner line when the opportunity is strong enough to matter. The goal of this change was not to abandon the safer convoy architecture, but to prevent obviously favorable mine opportunities from being ignored while an opponent scales uncontested.

This update reinforced a broader systems insight: a stable bot can still be strategically incomplete if it survives well but never develops a meaningful answer to compounding income. In other words, safety and economy are not competing ideas in this environment; a competitive agent eventually needs both.

## Current Status

The agent is functional and has moved beyond the starter-policy stage. It now includes persistent unit memory, safer movement rules, A*-based path planning on discovered terrain, and differentiated behavior across scouts, workers, miners, and the factory. The project is still in progress, with the next major focus being stronger local evaluation through simulation and more robust strategic tuning.
