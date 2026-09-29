import os
import sys
import numpy as np
import gymnasium as gym

from envs.daddy_long_legs_env import DaddyLongLegsEnv


class MockGameClient:
    """Mock GameClient for offline environment API verification."""
    def __init__(self):
        self.frame = 0
        self.died = False
        self.distance = 0.0

    def reset(self):
        self.frame = 1
        self.died = False
        self.distance = 0.0

    def step_frame(self, action=0, timeout=1.0):
        self.frame += 1
        if action == 1:
            self.distance += 0.5
        else:
            self.distance += 0.1

        # Simulate random fall
        if self.frame > 20 and np.random.rand() < 0.1:
            self.died = True

        return {
            "frame": self.frame,
            "hasDied": self.died,
            "vx": 1.2 if action == 1 else 0.5,
            "vy": 0.0,
            "legLeft1": 15.0,
            "legRight1": -12.0,
            "legLeft2": 5.0,
            "legRight2": -8.0,
            "headRotation": 2.5,
            "legCode": 1.0,
            "distance": self.distance,
        }

    def close(self):
        pass


def test_mock_env():
    print("[VERIFY] Testing DaddyLongLegsEnv with Mock GameClient...")
    mock_client = MockGameClient()
    env = DaddyLongLegsEnv(game_client=mock_client, auto_init_client=False)

    # Test reset
    obs, info = env.reset()
    print(f"[VERIFY] reset() returned obs shape: {obs.shape}, dtype: {obs.dtype}")
    assert obs.shape == (9,), f"Expected obs shape (9,), got {obs.shape}"
    assert env.observation_space.contains(obs), "Observation outside observation_space bounds"

    # Test step loop
    total_reward = 0.0
    steps = 0
    for _ in range(50):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
        assert env.observation_space.contains(obs), "Obs invalid"
        if terminated or truncated:
            print(f"[VERIFY] Episode finished after {steps} steps. Total reward: {total_reward:.2f}")
            break

    print("[VERIFY] Mock environment verification PASSED!")


def main():
    if "--live" in sys.argv:
        print("[VERIFY] Running live environment test against Waydroid GameClient...")
        env = DaddyLongLegsEnv(auto_init_client=True)
        obs, info = env.reset()
        print(f"[VERIFY] Live env reset obs: {obs}")
        for _ in range(10):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            print(f"Step {_}: reward={reward:.2f}, terminated={terminated}, dist={info.get('distance')}")
            if terminated:
                break
        env.close()
    else:
        test_mock_env()


if __name__ == "__main__":
    main()
