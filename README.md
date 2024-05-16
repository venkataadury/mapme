# MapMe
Find (the shortest) path between countries. Inspired by https://travle.earth/

## About
Guess how to connect two countries. Some borders may be unintuitive/missing. Updates to the adjacency matrix will keep happening

## Requirements
The default mode is `LOW_MEM` (low memory) mode, that dynamically loads only sections of the map that are requried. But given that the map is very high resolution, it might eventually fill upto 4 GB RAM.<br/>
Disabling `LOW_MEM` takes a lot more RAM (4-5 GB) during the loading phase, but there is no increase in memory use after.

### Python Packages
The following python packages are required to run this program. The default install script uses `micromamba` (See: https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html), but you can satisfy these requirements through other means (such as anaconda/pip)
- numpy (Preferred >= 1.26.3)
- matplotlib (Mostly any version compatible with other requirements works)
- pillow (Preferred >= 10.2.0)
- pygame (Preferred >= 2.5.2)
- pygame_widgets (>=1.1.5)

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
