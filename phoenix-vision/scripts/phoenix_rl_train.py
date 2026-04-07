"""
phoenix_rl_train.py - RL training scaffold (optional)

What this contains:
 - A minimal Gym environment wrapper skeleton (FlightGearEnv) that will interface
   with FlightGear via telnet. It implements reset() and step() placeholders.
 - A training scaffold that tries to import stable-baselines3 and train PPO if available.
 - NOTE: Training RL with a real simulator is advanced: you will likely want a
   deterministic (fast) simulator wrapper or an FDM (no GUI) instance of FlightGear.

Usage:
 - Implement observation_space, action_space and step/reset according to your design.
 - Install stable-baselines3 to run the example:
     pip install stable-baselines3[extra] gym==0.21.0
"""

import time, math, os
try:
    import gymnasium as gym
    from gymnasium import spaces

except Exception:
    gym = None

# Optional RL library
try:
    from stable_baselines3 import PPO
    import numpy as np
    SB3_AVAILABLE = True
except Exception:
    SB3_AVAILABLE = False

class FlightGearEnv(gym.Env):
    """
    Minimal skeleton for a Gym environment that interacts with FlightGear.
    You MUST implement actual telemetry reads and actions (autopilot commands).
    """
    def __init__(self, host="localhost", port=5400):
        if gym is None:
            raise ImportError("gym not available. install gym to use RL scaffold.")
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -90.0, -90.0], dtype=np.float32),
            high=np.array([10000.0, 200.0, 90.0, 90.0], dtype=np.float32),
            dtype=np.float32
        )

        # Define action space (heading delta, pitch delta, throttle)
        self.action_space = spaces.Box(
            low=np.array([-30.0, -5.0, 0.0], dtype=np.float32),
            high=np.array([30.0, 5.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )

        print("RL scaffold. Running a small test (no FG connection).")

        # TODO: add telnet connection to FlightGear, or start FG in headless mode
        self.host = host
        self.port = port
        self.state = None
        self.step_count = 0

    def reset(self):
        # Reset simulator to safe state (you must implement FG commands)
        self.step_count = 0
        # Example initial observation (alt,airspeed,heading,pitch,roll,vsi)
        self.state = [3000.0, 85.0, 0.0, 0.0, 0.0, 0.0]
        return self._get_obs()

    def step(self, action):
        # Action is applied to the simulator (you must implement)
        # For now, simulate simple dynamics.
        heading_delta, pitch_delta, throttle = action
        # fake dynamics
        alt, ias, hdg, pitch, roll, vsi = self.state
        hdg = (hdg + heading_delta) % 360
        alt = max(0.0, alt - max(10.0, abs(pitch_delta)*10.0))
        ias = max(30.0, ias + (throttle - 0.5)*5.0)
        vsi = - (alt * 0.001)
        self.state = [alt, ias, hdg, pitch + pitch_delta, roll, vsi]
        self.step_count += 1

        # Reward: encourage descending safely (this is a placeholder)
        reward = -abs(alt - 500) * 0.001  # closer to 500ft is better (toy)
        done = (alt <= 0) or (self.step_count > 500)
        info = {}
        return self._get_obs(), reward, done, info

    def _get_obs(self):
        return [float(x) for x in self.state]

    def render(self, mode="human"):
        print("Step", self.step_count, "state:", self.state)

# Training scaffold
def train_small_test(total_timesteps=10000):
    if not SB3_AVAILABLE:
        print("stable-baselines3 not installed. To train, run:")
        print("  pip install stable-baselines3[extra] gym==0.21.0")
        return

    env = FlightGearEnv()
    # Wrap with DummyVecEnv etc if needed by SB3
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=total_timesteps)
    model.save("ppo_phoenix_demo")
    print("Saved policy: ppo_phoenix_demo.zip")

if __name__ == "__main__":
    print("RL scaffold. Running a small test (no FG connection).")
    env = FlightGearEnv()
    obs = env.reset()
    for _ in range(5):
        a = env.action_space.sample()
        obs, r, d, info = env.step(a)
        env.render()
    print("To train, call train_small_test() with stable-baselines3 installed.")
