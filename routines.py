from utils import *
from objects import *

#This file holds all of the mechanical tasks, called "routines", that the bot can do

class atba():
    #An example routine that just drives towards the ball at max speed
    def run(self, agent):
        relative_target = agent.ball.location - agent.me.location
        local_target = agent.me.local(relative_target)
        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)


class aerial_shot():
    # Very similar to jump_shot(), but instead designed to hit targets above 300uu
    # ***This routine is a WIP*** It does not currently hit the ball very hard, nor does it like to be accurate above 600uu or so
    def __init__(self, ball_location, center_location, intercept_time, shot_vector, ratio):
        self.ball_location = ball_location
        self.center_location = center_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # The point we hit the ball at
        self.intercept = self.ball_location - (self.shot_vector * 110)
        # dictates when (how late) we jump, much later than in jump_shot because we can take advantage of a double jump
        self.jump_threshold = 600
        # what time we began our jump at
        self.jump_time = 0
        # If we need a second jump we have to let go of the jump button for 3 frames, this counts how many frames we have let go for
        self.counter = 0

    def run(self, agent):
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.01, 10.0)

        car_to_ball = self.ball_location - agent.me.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0, 0, 1)).dot(car_to_ball))

        car_to_intercept = self.intercept - agent.me.location
        car_to_intercept_perp = car_to_intercept.cross((0, 0, side_of_shot))  # perpendicular
        flat_distance_remaining = car_to_intercept.flatten().magnitude()

        speed_required = flat_distance_remaining / time_remaining
        # When still on the ground we pretend gravity doesn't exist, for better or worse
        acceleration_required = backsolve(self.intercept, agent.me, time_remaining, 325)
        local_acceleration_required = agent.me.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_intercept.angle(self.shot_vector) * flat_distance_remaining / 1.57  # size of adjustment
        adjustment *= (cap(self.jump_threshold - (acceleration_required[2]), 0.0,
                           self.jump_threshold) / self.jump_threshold)  # factoring in how close to jump we are
        # we don't adjust the final target if we are already jumping
        final_target = self.intercept + ((car_to_intercept_perp.normalize() * adjustment) if self.jump_time == 0 else 0)

        # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5150: final_target[0] = cap(final_target[0], -750, 750)

        local_final_target = agent.me.local(final_target - agent.me.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location, self.intercept)
        agent.line(self.intercept - Vector3(0, 0, 100), self.intercept + Vector3(0, 0, 100), [255, 0, 0])
        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [0, 255, 0])

        angles = defaultPD(agent, local_final_target)

        if self.jump_time == 0:
            defaultThrottle(agent, speed_required)
            agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost == True
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake 

            velocity_required = car_to_intercept / time_remaining
            good_slope = velocity_required[2] / cap(abs(velocity_required[0]) + abs(velocity_required[1]), 1,
                                                    10000) > 0.15
            if good_slope and (
            local_acceleration_required[2]) > self.jump_threshold and agent.me.velocity.flatten().normalize().dot(
                    acceleration_required.flatten().normalize()) > 0.8:
                # Switch into the jump when the upward acceleration required reaches our threshold, hopefully we have aligned already...
                self.jump_time = agent.time
        else:
            time_since_jump = agent.time - self.jump_time

            # While airborne we boost if we're within 30 degrees of our local acceleration requirement
            if agent.me.airborne and local_acceleration_required.magnitude() * time_remaining > 90:
                angles = defaultPD(agent, local_acceleration_required)
                if abs(angles[0]) + abs(angles[1]) < 0.45:
                    agent.controller.boost = True
            elif agent.me.airborne and self.counter < 3:
                final_target -= Vector3(0, 0, 45)
                local_final_target = agent.me.local(final_target - agent.me.location)
                angles = defaultPD(agent, local_final_target)

            if self.counter == 0 and (time_since_jump <= 0.2 and local_acceleration_required[2] > 0):
                # hold the jump button up to 0.2 seconds to get the most acceleration from the first jump
                agent.controller.jump = True
            elif time_since_jump > 0.2 and self.counter < 3:
                # Release the jump button for 3 ticks
                agent.controller.jump = False
                agent.controller.pitch = agent.controller.yaw = agent.controller.roll = 0
                self.counter += 1
            elif local_acceleration_required[2] > 300 and self.counter == 3:
                # the acceleration from the second jump is instant, so we only do it for 1 frame
                agent.controller.jump = True
                agent.controller.pitch = agent.controller.yaw = agent.controller.roll = 0
                self.counter += 1
            elif self.counter < 5:
                self.counter += 1
                agent.controller.pitch = agent.controller.yaw = agent.controller.roll = 0

        if raw_time_remaining < -0.25:
            agent.pop()
            agent.push(recovery())
        if not shot_valid(agent, self, 90):
            agent.pop()

class flip():
    #Flip takes a vector in local coordinates and flips/dodges in that direction
    #cancel causes the flip to cancel halfway through, which can be used to half-flip
    def __init__(self,vector,cancel = False):
        self.vector = vector.normalize()
        self.pitch = abs(self.vector[0])* -sign(self.vector[0])
        self.yaw = abs(self.vector[1]) * sign(self.vector[1])
        self.cancel = cancel
        #the time the jump began
        self.time = -1
        #keeps track of the frames the jump button has been released
        self.counter = 0
    def run(self,agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < 0.15:
            agent.controller.jump = True
        elif elapsed >=0.15 and self.counter < 3:
            agent.controller.jump = False
            self.counter += 1
        elif elapsed < 0.3 or (not self.cancel and elapsed < 0.9):
            agent.controller.jump = True
            agent.controller.pitch = self.pitch
            agent.controller.yaw = self.yaw
        else:
            agent.pop()
            agent.push(recovery())
            
class goto():
    #Drives towards a designated (stationary) target
    #Optional vector controls where the car should be pointing upon reaching the target
    #TODO - slow down if target is inside our turn radius
    def __init__(self, target, vector=None, direction = 1):
        self.target = target
        self.vector = vector
        self.direction = direction
    def run(self,agent):
        car_to_target = self.target - agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(self.target - Vector3(0,0,500),self.target + Vector3(0,0,500),[255,0,255])
        
        if self.vector != None:
            #See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0,0,1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1] > 5150): final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target, self.direction)
        defaultThrottle(agent, 2300, self.direction)
        
        agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if distance_remaining < 350:
            agent.pop()
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0:
            agent.push(flip(local_target))
        elif abs(angles[1]) > 2.8 and velocity < 200:
            agent.push(flip(local_target,True))
        elif agent.me.airborne:
            agent.push(recovery(self.target))

class goto_boost():
    #very similar to goto() but designed for grabbing boost
    #if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self,boost,target=None):
        self.boost = boost
        self.target = target
    def run(self,agent):
        car_to_boost = self.boost.location - agent.me.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector3(0,0,500),self.boost.location+ Vector3(0,0,500),[0,255,0])

        if self.target != None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0,0,1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0,0,side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            car_to_target = (self.target - agent.me.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location.copy()

        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1] > 5150): final_target[0] = cap(final_target[0],-750,750)

        local_target = agent.me.local(final_target - agent.me.location)
        
        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)
        
        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1+agent.me.velocity.magnitude()
        if self.boost.active == False or agent.me.boost >= 99.0 or distance_remaining < 350:
            agent.pop()
        elif agent.me.airborne:
            agent.push(recovery(self.target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and (distance_remaining / velocity > 2.0 or (adjustment < 90 and car_to_target/velocity > 2.0)):
            agent.push(flip(local_target))        
               
class jump_shot():
    #Hits a target point at a target time towards a target direction
    #Target must be no higher than 300uu unless you're feeling lucky
    #TODO - speed
    def __init__(self, ball_location, center_location, intercept_time, shot_vector, ratio, direction=1, speed=2300):
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        #The direction we intend to hit the ball in
        self.shot_vector = shot_vector

        center_vector = (center_location - ball_location).normalize()
        center_perp = center_vector.cross((0, 0, 1))
        center_side = sign(center_perp.dot(shot_vector)) # left is positive
        center_error = 0# cap((1 - cap(center_vector.dot(shot_vector), 0, 1)) * 200, 0, 100)

        #The point we dodge at
        #177 is the 93uu ball radius + a bit more to account for the car's hitbox
        self.dodge_point = self.ball_location - (self.shot_vector * 185) + (center_perp * center_error * center_side)
        #Ratio is how aligned the car is. Low ratios (<0.5) aren't likely to be hit properly 
        self.ratio = ratio
        #whether the car should attempt this backwards
        self.direction = direction
        #Intercept speed not implemented
        self.speed_desired = speed
        #controls how soon car will jump based on acceleration required. max 584
        #bigger = later, which allows more time to align with shot vector
        #smaller = sooner
        self.jump_threshold = 400
        #Flags for what part of the routine we are in
        self.jumping = False
        self.dodging = False
        self.counter = 0
    def run(self,agent):
        raw_time_remaining = self.intercept_time - agent.time
        #Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining,0.001,10.0)
        car_to_ball = self.ball_location - agent.me.location

        #whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0,0,1)).dot(car_to_ball))
        
        car_to_dodge_point = self.dodge_point - agent.me.location
        car_to_dodge_perp = car_to_dodge_point.cross((0,0,side_of_shot)) #perpendicular
        distance_remaining = car_to_dodge_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.dodge_point,agent.me,time_remaining,0 if not self.jumping else 650)
        local_acceleration_required = agent.me.local(acceleration_required)

        #The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        #The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_dodge_point.angle(self.shot_vector) * distance_remaining / 2 #size of adjustment
        adjustment *= (cap(self.jump_threshold-(acceleration_required[2]),0.0,self.jump_threshold) / self.jump_threshold) #factoring in how close to jump we are
        #we don't adjust the final target if we are already jumping
        final_target = self.dodge_point + ((car_to_dodge_perp.normalize() * adjustment) if not self.jumping else 0) + Vector3(0,0,50)
        #Ensuring our target isn't too close to the sides of the field, where our car would get messed up by the radius of the curves
        
        #Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1] > 5150): final_target[0] = cap(final_target[0],-750,750)

        local_final_target = agent.me.local(final_target - agent.me.location)

        #drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(agent.me.location,self.dodge_point)
        agent.line(self.dodge_point-Vector3(0,0,100), self.dodge_point+Vector3(0,0,100),[255,0,0])
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[0,255,0])

        #Calling our drive utils to get us going towards the final target
        angles = defaultPD(agent,local_final_target,self.direction)
        defaultThrottle(agent, speed_required,self.direction)

        agent.line(agent.me.location, agent.me.location + (self.shot_vector*200), [255,255,255])

        agent.controller.boost = False if abs(angles[1]) > 0.3 or agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 and self.direction == 1 else agent.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 60 or not shot_valid(agent,self, 45):
                #If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                agent.pop()
                if agent.me.airborne:
                    agent.push(recovery())
            elif local_acceleration_required[2] > self.jump_threshold and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude():
                #Switch into the jump when the upward acceleration required reaches our threshold, and our lateral acceleration is negligible
                self.jumping = True 
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent,self,150)) or raw_time_remaining <= -0.9 or (not agent.me.airborne and self.counter > 0):
                agent.pop()
                agent.push(recovery())
            elif self.counter == 0 and local_acceleration_required[2] > 0.0 and raw_time_remaining > 0.083:
                #Initial jump to get airborne + we hold the jump button for extra power as required
                agent.controller.jump = True
            elif self.counter < 3:
                #make sure we aren't jumping for at least 3 frames
                agent.controller.jump = False
                self.counter += 1
            elif raw_time_remaining <= 0.1 and raw_time_remaining > -1.2:
                if distance_remaining < 500:
                    #dodge in the direction of the shot_vector
                    agent.controller.jump = True
                    if not self.dodging:
                        vector = agent.me.local(self.shot_vector).normalize() * self.direction
                        self.p = -vector[0] * self.direction
                        self.y = vector[1]
                        self.dodging = True
                    #simulating a deadzone so that the dodge is more natural
                    agent.controller.pitch = self.p if abs(self.p) > 0.2 else 0
                    agent.controller.yaw = self.y if abs(self.y) > 0.3 else 0
                else:
                    agent.pop()
                    agent.push(recovery())

class kickoff():
    #A simple 1v1 kickoff that just drives up behind the ball and dodges
    #misses the boost on the slight-offcenter kickoffs haha
    def run(self,agent):
        kickoff_last_touch = agent.ball.latest_touched_team = 1 if agent.ball.latest_touched_team == 1 else -1 and agent.kickoff_flag == True
        target = agent.ball.location + Vector3(0,200*side(agent.team),0)
        local_target = agent.me.local(target - agent.me.location)
        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)
        if local_target.magnitude() < 650:
            agent.pop()
            #flip towards opponent goal
            agent.push(flip(agent.me.local(agent.foe_goal.location - agent.me.location)))
            if kickoff_last_touch:
                pass
        
               

class recovery():
    #Point towards our velocity vector and land upright, unless we aren't moving very fast
    #A vector can be provided to control where the car points when it lands
    def __init__(self,target=None):
        self.target = target
    def run(self, agent):
        if self.target != None:
            local_target = agent.me.local((self.target-agent.me.location).flatten())
        else:
            local_target = agent.me.local(agent.me.velocity.flatten())

        defaultPD(agent,local_target)
        agent.controller.throttle = 1
        if not agent.me.airborne:
            agent.pop()

class short_shot():
    #This routine drives towards the ball and attempts to hit it towards a given target
    #It does not require ball prediction and kinda guesses at where the ball will be on its own
    def __init__(self,target):
        self.target = target
    def run(self,agent):
        car_to_ball,distance = (agent.ball.location - agent.me.location).normalize(True)
        ball_to_target = (self.target - agent.ball.location).normalize()

        relative_velocity = car_to_ball.dot(agent.me.velocity-agent.ball.velocity)
        if relative_velocity != 0.0:
            eta = cap(distance / cap(relative_velocity,400,2300),0.0, 1.5)
        else:
            eta = 1.5

        #If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross((0,0,1))
        right_vector = car_to_ball.cross((0,0,-1))
        target_vector = -ball_to_target.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector*(distance/2))

        #Some adjustment to the final target to ensure we don't try to drive through any goalposts to reach it
        if abs(agent.me.location[1] > 5150): final_target[0] = cap(final_target[0],-750,750)
        
        agent.line(final_target-Vector3(0,0,100),final_target+Vector3(0,0,100),[255,255,255])
        
        angles = defaultPD(agent, agent.me.local(final_target-agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300-cap(1600*abs(angles[1]),0,2050))
        agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (eta < 0.45 or distance < 150):
            agent.pop()
            agent.push(flip(agent.me.local(car_to_ball)))

class dribble():
    # this routine simply hits the ball away from our goal
    def __init__(self, target):
        self.target = target
        self.jumping = False
        self.step = 0
        self.eta = 0
    def run(self, agent):
        me_to_goal = (agent.me.location - self.target).normalize()
        balance_spot = agent.me.location + me_to_goal * 20

        ball_to_spot = agent.ball.location - balance_spot
        local_ball_offset = agent.me.local(ball_to_spot)
        distance = ball_to_spot.flatten().magnitude()

        ball_speed = agent.ball.velocity.flatten().magnitude()

        defaultPD(agent, local_ball_offset)
        if self.step == 0:
            car_to_ball = (agent.ball.location - agent.me.location).normalize()

            ball_to_our_goal = (agent.ball.location - agent.friend_goal.location).normalize()

            relative_velocity = car_to_ball.dot(agent.me.velocity - agent.ball.velocity)
            if relative_velocity != 0.0:
                self.eta = cap(distance / cap(relative_velocity, 400, 2300), 0.0, 1.5)
            else:
                self.eta = 1.5

            # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
            left_vector = car_to_ball.cross((0, 0, 1))
            right_vector = car_to_ball.cross((0, 0, -1))
            target_vector = -ball_to_our_goal.clamp(left_vector, right_vector)
            final_target = agent.ball.location + (target_vector * (distance / 2))

            # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
            if abs(agent.me.location[1]) > 5000:
                if abs(final_target[0]) < 800:
                    final_target[0] = cap(final_target[0], -800, 800)
                else:
                    final_target[1] = cap(final_target[1], -5100, 5100)

            angles = defaultPD(agent, agent.me.local(final_target - agent.me.location))
            defaultThrottle(agent, cap(ball_speed + distance + 800, 0, 2300))
            agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
            agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
            if agent.ball.location.z > 100 and distance < 500:
                self.step = 1
        if self.step == 1:
            defaultThrottle(agent, 2300)
            if distance < 50 and agent.ball.location.z > 80:
                self.step = 2
            elif agent.ball.location.z < 100:
                agent.pop()
        if self.step > 1:
            agent.controller.steer = cap(local_ball_offset[1] / 50, -1, 1)
            defaultThrottle(agent, cap(local_ball_offset[0] * 2 + ball_speed, 0, 2300))
            if agent.ball.location.z < 50 or distance > 200:
                agent.pop()
        if agent.me.airborne or agent.me.location.z > 500 or agent.rotation_index != 0:
            agent.pop()

class save():
    # this routine simply hits the ball away from our goal
    def __init__(self):
        self.eta = 0
    def run(self, agent):
        car_to_ball, distance = (agent.ball.location - agent.me.location).normalize(True)

        ball_to_our_goal = (agent.ball.location - agent.friend_goal.location).normalize()

        relative_velocity = car_to_ball.dot(agent.me.velocity - agent.ball.velocity)
        if relative_velocity != 0.0:
            self.eta = cap(distance / cap(relative_velocity, 400, 2300), 0.0, 1.5)
        else:
            self.eta = 1.5

        # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross((0, 0, 1))
        right_vector = car_to_ball.cross((0, 0, -1))
        target_vector = -ball_to_our_goal.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector * (distance / 2))

        # Some extra adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1]) > 5000:
            if abs(final_target[0]) < 800:
                final_target[0] = cap(final_target[0],-800,800)
            else:
                final_target[1] = cap(final_target[1],-5100,5100)

        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [255, 255, 255])

        angles = defaultPD(agent, agent.me.local(final_target - agent.me.location))
        defaultThrottle(agent, 2300 if distance > 1600 else 2300 - cap(1600 * abs(angles[1]), 0, 2050))
        agent.controller.boost = False if agent.me.airborne or abs(angles[1]) > 0.3 else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        if abs(angles[1]) < 0.05 and (self.eta < 0.45 or distance < 150):
            agent.pop()
            agent.push(flip(agent.me.local(car_to_ball)))
        if self.eta > 1 or agent.rotation_index != 0:
            agent.pop()

class demo():
    # this routine simply hits the ball away from our goal
    def __init__(self, target):
        self.target = target
    def run(self, agent):
        distance = (self.target.location - agent.me.location).magnitude()
        car_to_target = self.target.location + self.target.velocity * (distance / 2000) - agent.me.location

        angles = defaultPD(agent, agent.me.local(car_to_target))
        defaultThrottle(agent, 2300 if distance < 500 else 2300 - cap(1600 * abs(angles[1]), 0, 2050))
        agent.controller.boost = False if agent.me.airborne else agent.controller.boost
        agent.controller.handbrake = True if abs(angles[1]) > 2.0 else agent.controller.handbrake

        if self.target.location.z > 100 and distance < 1000 and abs(self.target.location.x) < 4000 and abs(self.target.location.y) < 5000:
            agent.pop()
            agent.controller.jump = True
        elif self.target.demolished or not agent.me.supersonic:
            agent.pop()
            
class align_in_goal():
    # this routine simply hits the ball away from our goal
    def __init__(self):
        self.backwards = False

    def run(self, agent):
        my_ball_distance = (agent.friend_goal.location - agent.ball.location).magnitude()
        ball_too_close = my_ball_distance < 1500 or (agent.ball.location + agent.ball.velocity - agent.me.location).magnitude() < 2000

        friend_goal_to_ball = (agent.friend_goal.location - agent.ball.location).flatten().normalize()
        ideal_position = (agent.friend_goal.location - friend_goal_to_ball * 700).flatten()
        ideal_position_to_me = ideal_position - agent.me.location
        ideal_distance = ideal_position_to_me.magnitude()

        me_to_goal = (agent.friend_goal.location - agent.me.location).flatten()

        relative_target = agent.ball.location - agent.me.location
        distance = me_to_goal.magnitude()

        ball_distance = (agent.friend_goal.location - agent.ball.location).magnitude()

        agent.line(ideal_position - Vector3(0, 0, 100), ideal_position + Vector3(0, 0, 100), [0, 0, 0])

        if distance < 700 and not self.backwards:
            defaultPD(agent, agent.me.local(relative_target))
            agent.controller.throttle = 1
            self.backwards = False
        else:
            self.backwards = True
        if distance > 400 and self.backwards:
            defaultPD(agent, agent.me.local(me_to_goal), -1)
            agent.controller.throttle = -1
            self.backwards = True

        if self.backwards and distance < 400:
            agent.pop()

        if ideal_distance < 50 or distance > 900 or ball_too_close:
            agent.pop()