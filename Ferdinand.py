
from tools import  *
from objects import *
from routines import *
from rlbot.utils.structures.quick_chats import QuickChats


#This file is for strategy

class Ferdinand(GoslingAgent):
    def run(agent):
        attack_kickoff = agent.kickoff_flag
        player_boost = agent.me.boost
        player_boost = agent.me.boost
        goal_to_ball = (agent.friend_goal.location - agent.ball.location).magnitude()
        goal_posts = (agent.friend_goal.right_post - agent.friend_goal.left_post).magnitude()
        close = (agent.me.location - agent.ball.location).magnitude() < 3500
        closer = (agent.me.location - agent.ball.location).magnitude() < 1200
        
        goal_to_ball = (agent.ball.location - agent.friend_goal.location).magnitude()
        my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
        ball_close = (agent.ball.location - agent.foe_goal.location).magnitude() > (agent.ball.location - agent.friend_goal.location).magnitude()
        ball_too_close = my_ball_distance < 1500 or (agent.ball.location + agent.ball.velocity - agent.me.location).magnitude() < 2000
        my_goal_to_me = agent.me.location - agent.friend_goal.location
        me_back = my_goal_to_me.magnitude() < my_ball_distance
        me_to_ball = (agent.me.location - agent.ball.location).magnitude()
        in_goal = (agent.friend_goal.location - agent.me.location).magnitude() < 200
        
        


        friends_back = 0
        agent.rotation_index = 0

        for friend in agent.friends:
            friend_to_ball_distance = (friend.location - agent.ball.location).magnitude()

            my_goal_to_friend = friend.location - agent.friend_goal.location
            friend_distance = my_goal_to_ball.dot(my_goal_to_friend)
            friend_back = False
            if friend_distance - 200 < my_ball_distance:
                friends_back += 1
                friend_back = True

        my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
        closest_foe = agent.me
        foes_back = 0

        for foe in agent.foes:
            foe_distance = (foe.location - agent.ball.location).magnitude()
            closest_foe_distance = (closest_foe.location - agent.ball.location).magnitude()

            enemy_goal_to_foe = foe.location - agent.foe_goal.location
            foe_distance_is_back = my_goal_to_ball.dot(enemy_goal_to_foe)
            foe_back = False
            if foe_distance_is_back - 200 < my_ball_distance:
                foe_back = True
                foes_back += 1
            if foe_distance < closest_foe_distance and foe_back:
                closest_foe = foe
        closest_foe_distance = (closest_foe.location - agent.ball.location).magnitude()

        foe_goal_to_ball, foe_ball_distance = (agent.ball.location - agent.foe_goal.location).normalize(True)
        foe_goal_to_foe = closest_foe.location - agent.foe_goal.location
        foe_distance = foe_goal_to_ball.dot(foe_goal_to_foe)


        
        large_boost = [boost for boost in agent.boosts if boost.large and boost.active]
        closest = large_boost[0]
        closest_distance = (large_boost[0].location - agent.me.location).magnitude()  


        for item in large_boost:
            item_distance = (item.location - agent.me.location).magnitude()
            #item_to_goal = (agent.boosts.location - agent.friend_goal.location).magnitude()
            
            if item_distance < closest_distance:
                closest = item
                closest_distance = item_distance 


        ball_in_enemy_corner = not ball_close and abs(agent.ball.location.x) > 3000 and abs(agent.ball.location.y) > 4000 
        ball_in_allie_corner = ball_close and -abs(agent.ball.location.x) > 3000 and -abs(agent.ball.location.y) > 4000 
        kickoff_last_touch = agent.ball.latest_touched_team = 1 if agent.ball.latest_touched_team == 1 else -1 and attack_kickoff == True


        clearing = False
        saving = False
        return_to_goal = False
        Friend_in_our_side = False


        if agent.stack is not None:
            agent.debug_stack()

        if len(agent.stack) < 1:

            if len(agent.friends) < 1:
                if attack_kickoff:
                    agent.push(kickoff())
                        
                if attack_kickoff == False:

                    goal_pos = agent.friend_goal.location
                    ball_pos = agent.ball.location
                    DISTANCE = 100
                    ball_goal_distance = goal_pos.flatten().dist(ball_pos.flatten())
                    x_dir = (goal_pos.x - ball_pos.x) / ball_goal_distance
                    y_dir = (goal_pos.y - ball_pos.y) / ball_goal_distance
                    targeted_x = ball_pos.x - (x_dir * DISTANCE)
                    targeted_y = ball_pos.y - (y_dir * DISTANCE)
                    targeted_car_pos = Vector3(targeted_x , targeted_y , 0)

                    targets = {"goal" : (agent.foe_goal.left_post,agent.foe_goal.right_post), "anywhere_but_my_net":(agent.friend_goal.right_post,agent.friend_goal.left_post)}
                    shots = find_hits(agent,targets)
                    if (len(shots["goal"]) > 0 and me_back) or (not ball_close and not foe_back and len(shots["goal"]) > 0):
                        agent.push((shots["goal"][0]))
                        return
                    elif (len(shots["anywhere_but_my_net"]) > 0 and (clearing and saving) == False and ball_close and me_back and foe_distance > my_ball_distance*2):
                        agent.push((shots["anywhere_but_my_net"][0]))
                        return
                    else:
                        pass
                    
                    if (ball_close and me_back):
                        saving = True
                    elif (ball_close and not me_back):
                        clearing = True
                    elif (not me_back and not ball_close and player_boost > 80):
                        agent.push(demo(closest_foe))
                    elif player_boost < 20 and me_back and not ball_close:
                        if len(agent.stack) < 2:
                            agent.push(goto_boost(closest,agent.ball.location))
                            return
                    else:
                        return_to_goal = True
                   

            if len(agent.friends) >= 1:

                Friend_in_our_side = (friend.location - agent.foe_goal.location).magnitude() < (friend.location - agent.friend_goal.location).magnitude() 

                if attack_kickoff == True:
                    if me_to_ball < friend_to_ball_distance or me_to_ball == friend_to_ball_distance:
                        agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_IGotIt)
                        agent.push(kickoff())
                        return
                    elif me_to_ball > friend_to_ball_distance:
                        agent.push(goto_boost(closest,agent.ball.location))
                        return
                    else:
                        pass
                    
                if attack_kickoff == False:
                    goal_pos = agent.friend_goal.location
                    ball_pos = agent.ball.location
                    DISTANCE = 100
                    ball_goal_distance = goal_pos.flatten().dist(ball_pos.flatten())
                    x_dir = (goal_pos.x - ball_pos.x) / ball_goal_distance
                    y_dir = (goal_pos.y - ball_pos.y) / ball_goal_distance
                    targeted_x = ball_pos.x - (x_dir * DISTANCE)
                    targeted_y = ball_pos.y - (y_dir * DISTANCE)
                    targeted_car_pos = Vector3(targeted_x , targeted_y , 0)

                    targets = {"goal" : (agent.foe_goal.left_post,agent.foe_goal.right_post), "anywhere_but_my_net":(agent.friend_goal.right_post,agent.friend_goal.left_post)}
                    shots = find_hits(agent,targets)

                    if (len(shots["goal"]) > 0 and me_back) or (not ball_close and not foe_back and len(shots["goal"]) > 0):
                        agent.push((shots["goal"][0]))
                        return
                    elif len(shots["anywhere_but_my_net"]) > 0 and (clearing and saving) == False and ball_close and me_back:
                        agent.push((shots["anywhere_but_my_net"][0]))
                        return
                    else:
                        return_to_goal = True


                    if (ball_close and me_back) or (ball_in_allie_corner and in_goal) or (in_goal and ball_close):
                        saving = True
                    elif (ball_close and not me_back and not Friend_in_our_side):
                        clearing = True
                    elif (not me_back and not ball_close and Friend_in_our_side and player_boost > 80):
                        agent.push(demo(closest_foe))
                    elif player_boost < 20 and me_back and not ball_close:
                        if len(agent.stack) < 2:
                            agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_NeedBoost)
                            agent.push(goto_boost(closest,agent.ball.location))
                            return
                    else:
                        return_to_goal = True
                        
        

        if saving:
            if closest_foe_distance < 300 and abs(closest_foe.velocity.magnitude() - agent.ball.velocity.magnitude()) < 600 and agent.ball.location.z < 200:
                agent.push(save())
                return
            else:
                agent.push(find_best_save(agent, closest_foe))
                return

        if clearing:
            if (closest_foe_distance < 300 and abs(closest_foe.velocity.magnitude() - agent.ball.velocity.magnitude()) < 600 and agent.ball.location.z < 200):
                agent.push((save))
                return
            else:
                agent.push(find_best_shot(agent, closest_foe)) 
                return   

        if return_to_goal:
            relative = (agent.friend_goal.location - agent.me.location)
            in_goal = (agent.friend_goal.location - agent.me.location).magnitude() < 500
            needed_speed = 2300 if goal_to_ball < 4500 else 1400
            angles = defaultPD(agent, agent.me.local(relative))
            defaultThrottle(agent, needed_speed)
            agent.controller.handbrake = True if abs(angles[1]) > 1.0 else False
            if in_goal:
                agent.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)
                agent.push(align_in_goal())
        