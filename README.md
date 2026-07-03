# PID-TempController
Lab project to control the temperature of water using an Arduino and a PID algorithm

## Proportional-Integral-Derivative Algorithms
A Proportional-Integral-Derivative Algorithm can be used in controllers to minimize the difference betweent the output and the desired state of the system. A PID is a classic closed-loop feedback system, meaning it takes an input and then systematically compares current state to its input over time. The image below shows a simple version of a closed loop system. The PID is simple and easy to implement, making it an attractive choice for many automated processes.

<img width="397" height="214" alt="image" src="https://github.com/user-attachments/assets/d91bf206-2f75-4440-b236-87e77090f019" />

There are many applications for the PID controller, but it's used most often in regulation. For example, the current goal for my PID is to simply regulate water temperature using a probe and heating rod.

### Walking 100 meters; example
So imagine you need to walk forward 100 meters for a sobriety test (**that is one demanding cop!**). Of course, you're sober, but the cop is having a bad night so he demands you walk exactly 100 meters. You only pass if you stop within 0.1 meters of the goal. If you think about it, this is a clever test, because drunk people do not understand control systems! Another rule: **you cannot stop until you're done, reverse, or speed up after slowing down!** This'll come into play in a second.

So, how do you proceed? Well, the cop gives you a watch that tells you your position every second, and you have a brain that sets your velocity with devastating accuracy. Thats easy! Just stop when the watch says 99.9. But wait, theres a caveat: the watch only updates every second. One miss-step near the goal and you fail, and the watch won't update fast enough to  So what you do first is select your **gain**. The gain is very simple: select your gain, multipy it by your distance, and then thats the new velocity you will walk. Since a fast human walking pace is 2.5 meters per second, you select a gain of 0.025, as 100 meters * 0.025 $$s^{-1}$$ is 2.5 m/s. Your distance to time graph will look something like this.
<img width="1281" height="993" alt="image" src="https://github.com/user-attachments/assets/554364f9-1cc3-4ed2-a72d-d934708d6473" />
Your position will approach the goal asymptotically until you get within 0.1 meters. The cop is stunned, but daps you up for your incredible math abilities. Thankfully for you, you simple cannot walk fast enough to blow past your target. However, if it *were* possible to select a gain of, say, 1.9, your graph would look like 
<img width="1281" height="993" alt="image" src="https://github.com/user-attachments/assets/c936f86c-3ab7-478c-8687-eae24ce65864" />
So lets talk a little bit more of P, I, and D.

## Proportional Gain, K<sub>p</sub>
Propotional gain was exemplified just before this in the walking example. Its a good way to correct your behavior as you approach the target. However, there are many ways for this to go wrong. Imagine that instead of walking, you're climbing, and gain * error sets the force you climb with. Obviously, you will stop dead in your tracks if the force you move up with ever equals the force of gravity, or your weight. This is called steady state error, and it will result in you never making it to the target. Also, think about it for a heating apparatus: if a certain amount of applied voltage corresponds to a certain amount of heat loss per minute, if the rate of heat emmission by the heated system ever becomes equal, you'll be screwed. Whoops!

