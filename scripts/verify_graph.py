import argparse
import json
import os
import sys

graph_path = "graph"
raw_path = "raw"

class Conditions:

    def __init__(self):
        self.items = []
        self.tasks = []

    def extend(self, items, tasks):
        self.items.extend(items)
        self.tasks.extend(tasks)

    def can_fulfill(self, task_key):
        task_is_complted = task_key in self.tasks
        if task_is_complted:
            return True
        
        task = raw_data["tasks"][task_key]
        task_can_be_completed = ((task["task_obstacle"] is None or task["task_obstacle"] in self.tasks) and all([item in self.items for item in task["items_needed"]]))
        
        return task_can_be_completed


def check_edge_lengths(graph_data, raw_data, warning_prefix):
    all_good = True

    edges = graph_data["edges"]
    vertices = graph_data["vertices"]
    
    for edge in edges:
        from_vertex_key = edge["from"]
        to_vertex_key = edge["to"]
        
        from_vertex = vertices[str(from_vertex_key)]
        to_vertex = vertices[str(to_vertex_key)]
        
        from_scene = from_vertex["furthest_scene"]
        to_scene = to_vertex["furthest_scene"]

        expected_length = edge["length"]

        conditions = Conditions()
        for condition_vertex in edge["conditions"]:
            vertex = vertices[str(condition_vertex)]
            conditions.extend(vertex["items"], vertex["tasks"])

        alternative_conditions = Conditions()
        for alternative_edge in edges:
            if alternative_edge["from"] == to_vertex_key and alternative_edge["to"] == from_vertex_key:
                for condition_vertex in alternative_edge["conditions"]:
                    vertex = vertices[str(condition_vertex)]
                    alternative_conditions.extend(vertex["items"], vertex["tasks"])

        post_scene = None
        for task in from_vertex["tasks"]:
            if raw_data["tasks"][task]["post_scene"] is not None:
                post_scene = raw_data["tasks"][task]["post_scene"]

        start_scene = from_scene
        additional_length = 0
        if post_scene is not None:
            start_scene = post_scene
            additional_length = 1
            
        actual_length = calculate_minimum_distance(raw_data, start_scene, to_scene, [], conditions)

        if actual_length is None:
            actual_length = calculate_minimum_distance(raw_data, start_scene, to_scene, [], alternative_conditions)
            
        
        if actual_length is not None:
            actual_length += additional_length

        if expected_length != actual_length:
            all_good = False
            print(warning_prefix + "Exptected length for edge from vertex", edge["from"], "(scene \"" + str(from_scene) + "\") to vertex", edge["to"], "(scene \"" + str(to_scene) + "\")",
                  "to be", expected_length, "but actual length is calculated to be", actual_length)

    return all_good


def calculate_minimum_distance(raw_data, from_scene, to_scene, visited_scenes, conditions):
    if from_scene == to_scene:
        return 0

    minimum_distance_for_next_scenes = None

    for next_scene_key in raw_data["scenes"][from_scene]["connected_scenes"]:
        if next_scene_key in visited_scenes:
            continue

        next_scene = raw_data["scenes"][next_scene_key]

        task_obstacle_key = next_scene["task_obstacle"]
        if task_obstacle_key is not None:
            if not conditions.can_fulfill(task_obstacle_key):
                continue
                
        next_visited_scenes = visited_scenes.copy()
        next_visited_scenes.append(next_scene_key)

        distance = calculate_minimum_distance(raw_data, next_scene_key, to_scene, next_visited_scenes, conditions)
        if distance is None:
            continue

        if minimum_distance_for_next_scenes is None or distance < minimum_distance_for_next_scenes:
            minimum_distance_for_next_scenes = distance

    if minimum_distance_for_next_scenes is None:
        return None

    return minimum_distance_for_next_scenes + 1
               

def check_graph_routes(graph_data, raw_data, warning_prefix):
    all_good = True

    for from_vertex_key in graph_data["vertices"]:
        for to_vertex_key in graph_data["vertices"]:
            if from_vertex_key == to_vertex_key:
                continue

            last_edges = []
            for edge in graph_data["edges"]:
                if edge["to"] == to_vertex_key:
                    last_edges.append(edge)

            if len(last_edges) == 0:
                continue

            from_vertex = graph_data["vertices"][from_vertex_key]
            to_vertex = graph_data["vertices"][to_vertex_key]

            start_scene = from_vertex["furthest_scene"]
            additional_length = 0
            for task_key in from_vertex["tasks"]:
                post_scene = raw_data["tasks"][task_key]["post_scene"]
                if post_scene is not None:
                    start_scene = post_scene
                    additional_length = 1
            
            raw_routes = calculate_shortest_routes(raw_data, start_scene, to_vertex["furthest_scene"], [from_vertex["furthest_scene"]])

            for calculated_length, task_obstacles in raw_routes:
                expected_length = calculated_length + additional_length

                allowed_condition_vertices = find_allowed_condition_vertices(graph_data["vertices"], raw_routes, last_edges, task_obstacles)

                if allowed_condition_vertices is None:
                    continue

                max_length = expected_length + 1
                result = calculate_shortest_graph_route(graph_data, from_vertex_key, to_vertex_key, allowed_condition_vertices, [from_vertex_key], 0, max_length)

                if result is None:
                    all_good = False
                    print(warning_prefix + "Could not find a route from", from_vertex_key, "to", to_vertex_key, "(with expected task obstacles", task_obstacles, "and allowed conditions", str(allowed_condition_vertices) + ") either because there wasn't a route or the graph one was longer than the path (raw path length was", str(expected_length) + ")")
                    continue

                actual_length, raw_path = result
                if(expected_length != actual_length):
                    all_good = False
                    print(warning_prefix + "Routes are not matching from", from_vertex_key, "to", str(to_vertex_key) + ". Raw path length was", expected_length, "and graph length was", str(actual_length) + ". Allowed task obstacles was " + str(task_obstacles) + " and allowed condition vertices was " + str(allowed_condition_vertices))

    return all_good


def calculate_shortest_routes(raw_data, from_scene_key, to_scene_key, visited_scenes):
    if from_scene_key == to_scene_key:
        return [[0, []]]

    from_scene = raw_data["scenes"][from_scene_key]

    routes = []

    for next_scene_key in from_scene["connected_scenes"]:
        if next_scene_key in visited_scenes:
            continue

        task_obstacle = raw_data["scenes"][next_scene_key]["task_obstacle"]
        
        new_visited_scenes = visited_scenes.copy()
        new_visited_scenes.append(next_scene_key)
        for length, task_obstacles in calculate_shortest_routes(raw_data, next_scene_key, to_scene_key, new_visited_scenes):
            if task_obstacle is not None:
                task_obstacles.append(task_obstacle)

            routes.append([length + 1, task_obstacles])

    highest_task_obstacles_count = 0
    shortest_routes_map = {}
    for length, task_obstacles in routes:
        if str(task_obstacles) not in shortest_routes_map or shortest_routes_map[str(task_obstacles)][0] > length:
               shortest_routes_map[str(task_obstacles)] = [length, task_obstacles]

        if len(task_obstacles) > highest_task_obstacles_count:
            highest_task_obstacles_count = len(task_obstacles)

    shortest_routes = []

    for task_obstacles_count in range(highest_task_obstacles_count + 1):
        for length, task_obstacles in shortest_routes_map.values():
            if len(task_obstacles) != task_obstacles_count:
                continue

            has_better_alternative = False
            for alternative_length, alternative_task_obstacles in shortest_routes:
                if alternative_length <= length and all([alternative_task_obstacle in task_obstacles for alternative_task_obstacle in alternative_task_obstacles]):
                    has_better_alternative = True
                    break

            if has_better_alternative:
                continue
            
            shortest_routes.append([length, task_obstacles])

    return shortest_routes


def calculate_shortest_graph_route(graph_data, from_vertex_key, to_vertex_key, allowed_condition_vertices, visited_vertices, previous_length, max_length):
    if from_vertex_key == to_vertex_key:
        return [0, [to_vertex_key]]

    if previous_length >= max_length:
        return None

    best_result = None

    for edge in graph_data["edges"]:
        if edge["from"] != from_vertex_key or edge["to"] in visited_vertices:
            continue

        allowed_condition = True
        for vertex_condition_key in edge["conditions"]:            
            if vertex_condition_key not in allowed_condition_vertices:
                allowed_condition = False

        if not allowed_condition:
            continue

        new_visited_vertices = visited_vertices.copy()
        new_visited_vertices.append(edge["to"])

        result = calculate_shortest_graph_route(graph_data, edge["to"], to_vertex_key, allowed_condition_vertices, new_visited_vertices, previous_length + edge["length"], max_length)

        if result is None:
            continue

        result[0] += edge["length"]
        result[1].insert(0, edge["from"])

        if best_result is None or result[0] < best_result[0]:
            best_result = result

    return best_result 


def find_allowed_condition_vertices(vertices, all_raw_routes, last_edges, allowed_task_obstacles):
    allowed_condition_vertices = []
    for vertex_key, vertex in vertices.items():
        conditons = Conditions()
        conditons.extend(vertex["items"],vertex["tasks"])

        for task in allowed_task_obstacles:
            if conditons.can_fulfill(task):
                allowed_condition_vertices.append(vertex_key)
                break

    enter_condition_sets = []
    for edge in last_edges:
        new_enter_conditions = edge["conditions"]
                    
        if len(new_enter_conditions) > 0:
            new_enter_conditions.sort()

            if new_enter_conditions not in enter_condition_sets:
                enter_condition_sets.append(new_enter_conditions)
        else:
            # There's one without conditions, that should always be picked
            enter_condition_sets = []
            break

    if len(enter_condition_sets) > 0:
        mininmum_condition_set = min(enter_condition_sets, key=len)

        # Handle case where there is more than one entry.  If there is more
        # with conditions, but the simplest one matches in all conditions we
        # assume that's the condition that's actually needed in order to
        # enter/solve the "end scene".  The remaining are just in another scene
        # for some of the routes
        for condition_set in enter_condition_sets:
            for condition in mininmum_condition_set:
                if condition not in condition_set:
                    raise Exception("Cannot handle edges with mixed issue vertices: " + str(enter_condition_sets))                                           

        for vertex in mininmum_condition_set:
            if vertex not in allowed_condition_vertices:
                allowed_condition_vertices.append(vertex)

    # In case we at this point figure out that in order to complete the graph
    # path we've allowed some condition that potentially could've changed the
    # raw path (as there would have been more items/tasks available) we simply
    # skip this route as it doesn't make sense - and there will be another path
    # with the "correct" conditions instead.  This can for instance be the case
    # if the last scene has a task that cannot be completed unless you've been
    # in a scene with a specific task obstacle.  For example in the 1st game,
    # you cannot help the ant queen unless you've let down the snake (so it
    # won't sense to look for paths that doesn't allow going via the snake)
    for _, other_task_obstacles in all_raw_routes:
        if allowed_task_obstacles != other_task_obstacles:
            task_obstacles_difference = [task for task in other_task_obstacles if task not in allowed_task_obstacles]

            for vertex_key in allowed_condition_vertices:
                vertex = graph_data["vertices"][vertex_key]

                conditons = Conditions()
                conditons.extend(vertex["items"],vertex["tasks"])

                for task in task_obstacles_difference:
                    if conditons.can_fulfill(task):
                        return None
    
    return allowed_condition_vertices


def fetch_graph_ids():
    graph_ids = []
    for file in os.listdir(graph_path):
        if os.path.isfile(os.path.join(graph_path, file)):
            graph_ids.append(file.split("_")[1])

    return graph_ids

parser = argparse.ArgumentParser(description='Verify graph data up against raw data')
parser.add_argument('--warning-prefix', dest='warning_prefix', default=" - ",
                    help='Prefix printed before warning messages')

args = parser.parse_args()
warning_prefix = args.warning_prefix

exit_code = 0
for game_version in fetch_graph_ids():
    print("Check graphs for game version " + game_version + ":")
    with open(os.path.join(graph_path, "ss_" + game_version + "_graph.json")) as graph_file:
        graph_data = json.load(graph_file)
    
    with open(os.path.join(raw_path, "ss_" + game_version + "_raw.json")) as graph_file:
        raw_data = json.load(graph_file)

    # Checks all edges up against raw path data.  This is the simple check
    if check_edge_lengths(graph_data, raw_data, warning_prefix):
        print(" - Current edge lenghts: OK")
    else:
        exit_code = 1

    # Checks all possible vertex-connection combinations (via one or more
    # edges) up against raw path data.  This is the more complex check
    if check_graph_routes(graph_data, raw_data, warning_prefix):
        print(" - Missing edges check: OK")
    else:
        exit_code = 1

sys.exit(exit_code)
