import os
import sys
import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces

# Ensure parent directory is in sys.path when running scripts standalone
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from managers.gameClient import GameClient


class DaddyLongLegsEnv(gym.Env):
    """
    Custom Gymnasium Environment for Daddy Long Legs running in Waydroid via Frida RPC.

    Action Space:
        Discrete(2):
            0 -> Do nothing / wait for next physics frame
            1 -> Tap (triggers OnGameTap in Unity)

    Observation Space:
        Box(9,):
            [0] vx: Horizontal velocity
            [1] vy: Vertical velocity
            [2] legLeft1: Left upper leg angle (degrees)
            [3] legRight1: Right upper leg angle (degrees)
            [4] legLeft2: Left lower leg angle (degrees)
            [5] legRight2: Right lower leg angle (degrees)
            [6] headRotation: Head Z-rotation angle (degrees)
            [7] legCode: Current active leg state
            [8] distance: Current total distance traveled
    """
    metadata = {"render_modes": ["human"], "render_fps": 30}

    def __init__(
        self,
        game_client: GameClient = None,
        max_episode_steps: int = 1000,
        survival_reward: float = 0.05,
        fall_penalty: float = 10.0,
        dist_scale: float = 1.0,
        vel_scale: float = 0.01,
        auto_init_client: bool = True,
    ):
        super().__init__()

        self.max_episode_steps = max_episode_steps
        self.survival_reward = survival_reward
        self.fall_penalty = fall_penalty
        self.dist_scale = dist_scale
        self.vel_scale = vel_scale
        self.auto_init_client = auto_init_client

        # Discrete Action Space: 0 = Wait, 1 = Tap
        self.action_space = spaces.Discrete(2)

        # Observation Space: 9 float features
        high = np.array([np.inf] * 9, dtype=np.float32)
        low = np.array([-np.inf] * 9, dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

        self.game_client = game_client
        self.current_step = 0
        self.prev_distance = 0.0
        self.last_frame = -1

    def _ensure_client(self):
        """Lazily initialize GameClient if not supplied."""
        if self.game_client is None and self.auto_init_client:
            print("[ENV] Initializing GameClient connection...")
            self.game_client = GameClient()
            print("[ENV] GameClient connected successfully.")

    def _extract_obs(self, state_dict: dict) -> np.ndarray:
        """Convert Frida state dictionary into numpy observation array."""
        if not state_dict:
            return np.zeros(9, dtype=np.float32)

        vx = float(state_dict.get("vx", 0.0) or 0.0)
        vy = float(state_dict.get("vy", 0.0) or 0.0)
        ll1 = float(state_dict.get("legLeft1", 0.0) or 0.0)
        lr1 = float(state_dict.get("legRight1", 0.0) or 0.0)
        ll2 = float(state_dict.get("legLeft2", 0.0) or 0.0)
        lr2 = float(state_dict.get("legRight2", 0.0) or 0.0)
        head_z = float(state_dict.get("headRotation", 0.0) or 0.0)
        leg_code = float(state_dict.get("legCode", 0.0) or 0.0)
        dist = float(state_dict.get("distance", 0.0) or 0.0)

        obs = np.array([vx, vy, ll1, lr1, ll2, lr2, head_z, leg_code, dist], dtype=np.float32)
        return obs

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._ensure_client()

        assert self.game_client is not None, "GameClient is not initialized"

        print("[ENV] Resetting environment...")
        self.game_client.reset()

        # Wait until game resets and character is alive
        start_time = time.time()
        timeout = 5.0
        state = {}

        while time.time() - start_time < timeout:
            state = self.game_client.step_frame(action=0, timeout=1.0)
            if state and not state.get("hasDied", True):
                break
            time.sleep(0.05)

        self.current_step = 0
        dist = float(state.get("distance", 0.0) or 0.0) if state else 0.0
        self.prev_distance = dist

        obs = self._extract_obs(state)
        info = {"frame": state.get("frame", 0) if state else 0, "reset_success": not state.get("hasDied", False)}

        return obs, info

    def step(self, action: int):
        self._ensure_client()
        assert self.game_client is not None, "GameClient is not initialized"

        self.current_step += 1

        # Execute action & wait for physics update frame
        state = self.game_client.step_frame(action=int(action), timeout=1.0)
        obs = self._extract_obs(state)

        has_died = bool(state.get("hasDied", False)) if state else True
        vx = float(state.get("vx", 0.0) or 0.0) if state else 0.0
        curr_dist = float(state.get("distance", 0.0) or 0.0) if state else self.prev_distance
        head_z = float(state.get("headRotation", 0.0) or 0.0) if state else 0.0

        # Reward computation
        dist_progress = max(0.0, curr_dist - self.prev_distance)
        self.prev_distance = curr_dist

        forward_reward = max(0.0, vx) * self.vel_scale
        step_dist_reward = dist_progress * self.dist_scale

        if has_died:
            reward = -self.fall_penalty
            terminated = True
        else:
            # Penalize extreme head angles (tilt/imbalance)
            head_tilt = abs(((head_z + 180) % 360) - 180)
            balance_penalty = 0.001 * (head_tilt ** 2)

            reward = step_dist_reward + forward_reward + self.survival_reward - balance_penalty
            terminated = False

        truncated = self.current_step >= self.max_episode_steps

        info = {
            "step": self.current_step,
            "frame": state.get("frame", -1) if state else -1,
            "distance": curr_dist,
            "has_died": has_died,
            "vx": vx,
        }

        return obs, float(reward), terminated, truncated, info

    def render(self):
        """Waydroid displays UI directly on host screen."""
        pass

    def close(self):
        if self.game_client is not None:
            print("[ENV] Closing GameClient connection...")
            try:
                self.game_client.close()
            except Exception as e:
                print(f"[ENV] Exception during close: {e}")
            self.game_client = None
