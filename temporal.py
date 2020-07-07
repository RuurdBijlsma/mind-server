# Temporal module on the basis of the pace-maker accumulator model
import random
import math


# Generates logistic noise with M = 0, SD = s
def noise(s):
    rand = random.uniform(0.001, 0.999)
    return s * math.log((1 - rand) / rand)


# Takes time in seconds and returns pulses
def time_to_pulses(time, t_0=0.011, a=1.1, b=0.015, add_noise=True):
    pulses = 0
    pulse_duration = t_0

    while time >= pulse_duration:
        time = time - pulse_duration
        pulses = pulses + 1
        pulse_duration = a * pulse_duration + add_noise * noise(b * a * pulse_duration)

    return pulses


# Takes pulses and returns time in seconds
def pulses_to_time(pulses, t_0=0.011, a=1.1, b=0.015, add_noise=True):
    time = 0
    pulse_duration = t_0

    while pulses > 0:
        time = time + pulse_duration
        pulses = pulses - 1
        pulse_duration = a * pulse_duration + add_noise * noise(b * a * pulse_duration)

    return time
