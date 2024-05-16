# MapMe
Find (the shortest) path between countries. Inspired by https://travle.earth/

## About
Guess how to connect two countries. Some borders may be unintuitive/missing. Updates to the adjacency matrix will keep happening

## Rules
You are given two countries (a start and a finish) that you need to join by supplying intermediate countries.<br/>
Countries guessed will be highlighted in 3 colors based on the following:
- Yellow: Start/End (Given by the program)
- Red: Wrong (i.e. there is no optimal path that passes through that country)
- Green: Correct (i.e. there *exists* an optimal path that passes through that country
Note that there may be more than one optimal path (multiple paths can have the same length).<br/>
The (ideal) goal is to complete the connection in exactly 'k' guesses, where 'k' is the length of the optimal path.

## Known bugs
In some systems, the combobox in the game can randomly fail to work, forcing a full restart.

## Acknowledgements
- Inspired by https://travle.earth/
- World map images extracted from https://www.mapchart.net/world.html
- Adjacency matrix mined from: https://github.com/DataOmbudsman/country-graph
