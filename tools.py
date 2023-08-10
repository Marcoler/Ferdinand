from routines import *

#This file is for strategic tools


def find_hits(agent, targets):
    # training weights removed

    hits = {name: [] for name in targets}
    struct = agent.get_ball_prediction_struct()

    i = 5
    while i < struct.num_slices:
        # Gather some data about the slice
        intercept_time = struct.slices[i].game_seconds
        time_remaining = intercept_time - agent.time
        if time_remaining > 0:
            ball_location = Vector3(struct.slices[i].physics.location)
            ball_velocity = Vector3(struct.slices[i].physics.velocity).magnitude()

            if abs(ball_location[1]) > 5250:
                break  # abandon search if ball is scored at/after this point

            # determine the next slice we will look at, based on ball velocity (slower ball needs fewer slices)
            i += 15 - cap(int(ball_velocity // 150), 0, 13)

            car_to_ball = ball_location - agent.me.location
            # Adding a True to a vector's normalize will have it also return the magnitude of the vector
            direction, distance = car_to_ball.normalize(True)

            # How far the car must turn in order to face the ball, for forward and reverse
            forward_angle = direction.angle(agent.me.forward)
            backward_angle = math.pi - forward_angle

            # Accounting for the average time it takes to turn and face the ball
            # Backward is slightly longer as typically the car is moving forward and takes time to slow down
            forward_time = time_remaining #- (forward_angle * 0.318)
            backward_time = time_remaining #- (backward_angle * 0.418)

            # If the car only had to drive in a straight line, we ensure it has enough time to reach the ball (a few assumptions are made)
            forward_flag = forward_time > 0.0 and (distance / forward_time) < (2299 if agent.me.boost > distance / 100 else max(1410, agent.me.velocity.flatten().magnitude() + (agent.me.boost * 65)))
            backward_flag = distance < 1500 and backward_time > 0.0 and (distance / backward_time) < 1200

            # Provided everything checks out, we begin to look at the target pairs
            if forward_flag or backward_flag:
                for pair in targets:
                    # First we correct the target coordinates to account for the ball's radius
                    # If fits == True, the ball can be scored between the target coordinates
                    left, right, center, fits = post_correction(ball_location, targets[pair][0], targets[pair][1])
                    if fits:
                        # Now we find the easiest direction to hit the ball in order to land it between the target points
                        left_vector = (left - ball_location).normalize()
                        right_vector = (right - ball_location).normalize()
                        best_shot_vector = direction.clamp(left_vector, right_vector)

                        # Check to make sure our approach is inside the field
                        if True:  # in_field(ball_location - (200*best_shot_vector),1):
                            # The slope represents how close the car is to the chosen vector, higher = better
                            # A slope of 1.0 would mean the car is 45 degrees off
                            slope = find_slope(best_shot_vector.flatten(), car_to_ball.flatten())
                            if forward_flag:
                                if (ball_location[2] <= 275 or (not in_field(ball_location, 50) and not in_field(agent.me.location, 100))) and slope > 0.75:
                                    hits[pair].append(jump_shot(ball_location, center, intercept_time, best_shot_vector, slope))
                                if ball_location[2] > 325 and slope > 1.0 and cap(ball_location[2] - 400, 100, 2000) * 0.1 < agent.me.boost:
                                    if abs((car_to_ball / forward_time) - agent.me.velocity).magnitude() - 300 < 400 * forward_time:
                                        hits[pair].append(aerial_shot(ball_location, center, intercept_time, best_shot_vector, slope))
                            elif backward_flag and ball_location[2] <= 250 and slope > 0.25:
                                hits[pair].append(jump_shot(ball_location, center, intercept_time, best_shot_vector, slope, -1))
        else:
            i += 1
    return hits

def find_saves(agent, targets):
    # find_hits takes a dict of (left,right) target pairs and finds routines that could hit the ball between those target pairs
    # find_hits is only meant for routines that require a defined intercept time/place in the future
    # find_hits should not be called more than once in a given tick, as it has the potential to use an entire tick to calculate

    # Example Useage:
    # targets = {"goal":(opponent_left_post,opponent_right_post), "anywhere_but_my_net":(my_right_post,my_left_post)}
    # hits = find_hits(agent,targets)
    # print(hits)
    # >{"goal":[a ton of jump and aerial routines,in order from soonest to latest], "anywhere_but_my_net":[more routines and stuff]}
    hits = {name: [] for name in targets}
    struct = agent.get_ball_prediction_struct()

    # Begin looking at slices 0.25s into the future
    # The number of slices
    i = 15
    while i < struct.num_slices:
        # Gather some data about the slice
        intercept_time = struct.slices[i].game_seconds
        time_remaining = intercept_time - agent.time
        if time_remaining > 0:
            ball_location = Vector3(struct.slices[i].physics.location)
            ball_velocity = Vector3(struct.slices[i].physics.velocity).magnitude()

            if abs(ball_location[1]) > 5250:
                break  # abandon search if ball is scored at/after this point

            # determine the next slice we will look at, based on ball velocity (slower ball needs fewer slices)
            i += 15 - cap(int(ball_velocity // 150), 0, 13)

            car_to_ball = (ball_location - agent.me.location).flatten()
            # Adding a True to a vector's normalize will have it also return the magnitude of the vector
            direction, distance = car_to_ball.normalize(True)

            time_of_arrival,forwards = eta(agent.me, ball_location)

            # Provided everything checks out, we begin to look at the target pairs
            if time_of_arrival < time_remaining:
                for pair in targets:
                    # First we correct the target coordinates to account for the ball's radius
                    # If swapped == True, the shot isn't possible because the ball wouldn't fit between the targets
                    left, right, swapped = post_correction(ball_location, targets[pair][0], targets[pair][1])
                    if not swapped:
                        # Now we find the easiest direction to hit the ball in order to land it between the target points
                        left_vector = (left - ball_location).normalize()
                        right_vector = (right - ball_location).normalize()
                        best_shot_vector = direction.clamp(left_vector, right_vector)

                        # Check to make sure our approach is inside the field
                        if in_field(ball_location - (250 * best_shot_vector), 1):
                            # The slope represents how close the car is to the chosen vector, higher = better
                            # A slope of 1.0 would mean the car is 45 degrees off
                            slope = find_slope(best_shot_vector, car_to_ball)
                            if forwards:
                                if ball_location[2] <= 300 and slope > 0.0:
                                    hits[pair].append(jump_shot(ball_location, intercept_time, best_shot_vector, slope))
                                if 600 > ball_location[2] > 300 and slope > 1.0 and (ball_location[2]-250) * 0.14 > agent.me.boost:
                                    hits[pair].append(aerial_shot(ball_location,intercept_time,best_shot_vector,slope))
                                if ball_location[2] > 600:
                                    aerial_attempt = aerial(ball_location - 120*best_shot_vector, intercept_time, True, target = best_shot_vector)
                                    if aerial_attempt.is_viable(agent, agent.time):
                                        hits[pair].append(aerial_attempt)
                            elif not forwards and ball_location[2] <= 280 and slope > 0.2:
                                hits[pair].append(jump_shot(ball_location, intercept_time, best_shot_vector, slope, -1))
        else:
            i += 1
    return hits

def find_best_shot(agent, closest_foe):
    left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                         0)
    left_mid_field = Vector3(1000 * -side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                             0)
    right_mid_field = Vector3(1000 * side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                              0)
    right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                          0)
    targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post),
               "leftfield": (left_field, left_mid_field), "rightfield": (right_mid_field, right_field),
               "anywhere_but_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}
    shots = find_hits(agent, targets)
    best_score = 0
    best_shot = short_shot(agent.foe_goal.location)
    if len(shots["goal"]) > 0:
        score = 100.3 - shots["goal"][0].intercept_time + agent.time + eta(closest_foe, shots["goal"][0].ball_location)[0] / 3 - eta(agent.me, shots["goal"][0].ball_location)[0] / 3
        if score > best_score:
            best_score = score
            best_shot = shots["goal"][0]
    if len(shots["leftfield"]) > 0:
        score = 100 - shots["leftfield"][0].intercept_time + agent.time + eta(closest_foe, shots["leftfield"][0].ball_location)[0] / 3 - eta(agent.me, shots["leftfield"][0].ball_location)[0] / 3
        if score > best_score:
            best_score = score
            best_shot = shots["leftfield"][0]
    if len(shots["rightfield"]) > 0:
        score = 100 - shots["rightfield"][0].intercept_time + agent.time + eta(closest_foe, shots["rightfield"][0].ball_location)[0] / 3 - eta(agent.me, shots["rightfield"][0].ball_location)[0] / 3
        if score > best_score:
            best_score = score
            best_shot = shots["rightfield"][0]
    return best_shot

def find_best_save(agent, closest_foe):
    left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                         0)
    left_mid_field = Vector3(1000 * -side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                             0)
    right_mid_field = Vector3(1000 * side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                              0)
    right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                          0)
    targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post),
               "leftfield": (left_field, left_mid_field), "rightfield": (right_mid_field, right_field),
               "anywhere_but_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}
    saves = find_saves(agent, targets)
    best_score = 0
    best_shot = save()
    if len(saves["goal"]) > 0:
        score = 100 - saves["goal"][0].intercept_time + agent.time + eta(closest_foe, saves["goal"][0].ball_location)[0] / 2 - 1 + distance_to_wall(saves["goal"][0].ball_location) / 1000
        if score > best_score:
            best_score = score
            best_shot = saves["goal"][0]
    if len(saves["leftfield"]) > 0:
        score = 100 - saves["leftfield"][0].intercept_time + agent.time
        if score > best_score:
            best_score = score
            best_shot = saves["leftfield"][0]
    if len(saves["rightfield"]) > 0:
        score = 100 - saves["rightfield"][0].intercept_time + agent.time
        if score > best_score:
            best_score = score
            best_shot = saves["rightfield"][0]
    if len(saves["anywhere_but_my_net"]) > 0:
        score = 100 - saves["anywhere_but_my_net"][0].intercept_time + agent.time
        if score > best_score:
            best_shot = saves["anywhere_but_my_net"][0]
    return best_shot