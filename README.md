# Skipper and Skeeto Data
The purpose of this project is to gather resources that potentially could be used for various projects dealing with 
Skipper and Skeeto. The project started because the data was needed in order to find shortest paths for speedrunning, 
but there is no limit for the usage - feel more than free to suggest/add more data.

## Structures
The current data set is structured as JSON and are split up into different types. Within each type there is various 
games, each identified with an ID (see the games section below). In the data, all keys are (aimed at being) snake_case. 

### Raw
The raw data (found in the `raw` folder) describes the "raw" data of the game in the sense that it lists all scenes, 
items and tasks and their connections. The elements are roughly defined as:
* __Item__: An element you can have in your inventory after for instance having picked it up or getting it from solving 
a task.
  * Items are usually used for a solving tasks, but it might not always be the case.
  * Items can be locked until some task has been solved (`task_obstacle`).
* __Task__: Something in the game you complete/solve in order to e.g. be able to enter a scene, pick up locked items or
solve other tasks. 
  * Tasks might not always lead to anything new and can for instance just be a requirement in order to complete the 
game.
  * Tasks can be "locked" until some other task has been solved (`task_obstacle`) and/or some items has been collected
(`items_needed`). 
  * Tasks can never be added to the inventory but they might unlock an item that can be added.
  * Some tasks automatically move the player into another scene after being solved (see `post_scene`). This is done 
right after the task has been solved, so be careful about the order of solving taks within a scene. It can be debated if
this move should be counted as a move between scenes, so be aware of this when comparing path lengths.
* __Scene__: A place in the game (for instance a room or specific location) you can enter and usually also exit. You 
move between scenes in the game and you as a player always see exactly one scene at a time.
  * Each scene can contain one/more items that can be picked up and/or tasks that can be solved.
  * Scenes can be "locked" until some task has been solved (`task_obstacle`). Note that this task might be inside the 
scene, meaning it should be solved as the first thing when entering the scene. This could for instance be a boss the 
user needs to beat. 
  * Currently the distance between connected scenes (see `connected_scenes`) are weighted equally. 

As a collective term, picking up items, solving tasks and moving to a scene can be defined as _actions_.

### Graph
The graph data (found in the `graph` folder) describes data that can be used when finding the fastest route with graph
theory. This potentially means that the data is a lot harder to get a complete overview of (compared to raw data), but 
is a lot more optimized for finding the best path(s). 

The data mainly consists of vertices and edges, but does also contain other info like an initial distance (see 
`start_length`) that is important since the first vertex (see `start_vertex`) might not have its furthest scene in the 
first scene of the game. Vertices and edges are roughly defined as:

* __Vertex__: A set of items and/or tasks that always makes sense to collect/complete at the same time. 
  * The items/tasks might be spread across several scenes, but there will always be a single scene that represents the 
scene that's furthest away from the connected verticies (this is represented by `furthest_scene`). In practice the 
vertex can only be spread across several scenes for scenes that are "dead ends" or part of a "one-way" path - so in most
cases the furthest scene also represents the scene where all the items/tasks are located in.
  * Some vertices should only be visited once (as defined by `one_time`), for instance because it's not possible in the 
game or the vertex has a task with a post scene which only can be used once. In the case of a post scene, this could
potentially be a shortcut and thus the algorithms might pick that vertex more than once if nothing was specified. Note 
however that most vertices should be allowed for more than one visit as they could be used as a part of the path more 
than once (the actions within it is just not performed the succeeding visits). 
  * In the vertex data, the items and tasks it represents are also specified (see `items` and `tasks`), but usually 
aren't directly necessary for finding a route. They are good for debugging/understanding the data and for instance 
verifying that they vertices are correct. And again, note that the items/tasks might not all be located in the same 
scene as a vertex can span across several scenes.
* __Edge__: The directional connection between two vertices (see `from` and `to`).
  * The length of an edge (see `length`) represents the distance between the two vertices the edge connects. This is 
usually the number of moves between their two furthest scenes, but might not always be the direct route, for instance if
there's a post scene involved. The length can be zero if the two vertices are located in the same scene.
  * Edges can be "locked" by some conditions until certain vertices has been visited (see `conditions`).
  * Several edges from a vertex might partly follow the same "route" as it's important an vertex isn't limited by edges 
with conditions if that wouldn't be the case in the game.
    * For instance there could be three vertices, A, B and C, each having a furthest sceen by the same name. In this 
example scenario scene A is then connected to scene B and scene B is connected to scene C. Vertex B furthermore 
represents a task that requires some items to be solved and vertex C represents an item that can be picked up right 
away. From vertex A there needs to be an edge to both vertex B and C, as edge A to B would have an condition 
(representing the obstacles of the task in vertex B) and edge A to C wouldn't have any conditions (as the "route" of the 
edge is just passing by scene B not performing any actions within it).

## Games
Currently only the games listed below is part of the data set and not all games of the Skipper and Skeeto series might 
make sense to add either.

### 1st game: Tales From Paradise Park
In this game, Skipper and Skeeto are in the park they live in and help all the animals living there. The goal is to help
them all, so they can help getting the fairy's wand back from the witch. The scenes are roughly laid out in a grid, 
which means there's a lot of possible ways to walk around in the park.

The game has two editions with different tasks/items and therefore two data sets.

#### 1st edition _(ID 1-1)_
Has a bit less tasks that is required to complete compared to the second edition, but does instead have some musical 
notes you optionally can pick up and play.

#### 2nd edition _(ID 1-2)_ 
The most known edition as it's been released the most times. It's a bit more complex than the first edition as it does 
have more required tasks/items and there's only a few actions that's not required in order to complete the game. A small
detail with the second game is that you as a player actually have to hand over the wand to the fairy. This is however 
not part of the data (for now) as it's a mandatory part of the ending.

### 2nd game: The Great Treasure Hunt _(ID 2)_
In this game, Skipper and Skeeto are inside the castle looking for a treasure that can make sure the castle isn't taken 
over by Mr. Shade. On their adventure they for instance have to get rid of some ghosts. 

The scenes are connected as a tree structure with its root in the main hall. Therefore the possibilities are a lot 
more limited compared to the first game. This is also why there for now only has been added raw data - the complexity of
the routes are so simple that raw data should be sufficient to find the fastest route with basic algorithms.

There exist two editions of the game, one with a maze and one without. We do however not distinguish for now, as the 
data does not include the maze at all. This is due to the fact that the maze is in the end of the game and a completly 
seperate part of the game.

## Scripts and test
There is a few scripts/test in the project (located in the `scripts`) folder. They for instance verify if the data is 
valid and are executed automatically when pushing new data to the project. It is however also possible to run them 
locally to test the data before pushing them to the project.

## Contributions
Contributions and new ideas to the dataset/structure are more than welcome. Feel free to make a pull request, open an
issue or contact us about ideas. The current structure is fairly generic, but might not cover all needed aspects for all
games, so suggestions to changes/additions are more than welcome. There might also be flaws in the data set and those we 
really want to eliminate.

The structure or the documentation behind it (within this document) might also be unclear/confusing in some cases. Any 
constructive feedback is more than welcome, so feel free to let us know.  
