import gymnasium as gym
from envs import DaddyLongLegsEnv

# Initialize environment
env = DaddyLongLegsEnv(auto_init_client=True)

# Standard Gymnasium reset & step loop
obs, info = env.reset()
for step in range(1000):
    action = env.action_space.sample()  # or policy.predict(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    print(f"Step {step}: Reward={reward:.2f}, Distance={info['distance']}")
    if terminated or truncated:
        obs, info = env.reset()

env.close()
