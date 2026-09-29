# Missing Game Methods & Reverse Engineering Keywords Guide

This document details missing internal game methods, class names, field offsets, and keywords to search for within your internal game code to enhance Frida RPC integration and accelerate Reinforcement Learning (RL) training for **Daddy Long Legs**.

---

## 1. Speeding Up RL Training (Unity Time Scale)

### Concept
By default, Unity simulates physics at real-time (1.0x timeScale, 30/60 FPS). Accelerating Unity's internal physics clock allows your RL agent to collect thousands of environment steps in a fraction of the time.

### Class & Method to Search
- **Assembly**: `UnityEngine.CoreModule` (or `UnityEngine`)
- **Class**: `UnityEngine.Time`
- **Method**: `set_timeScale(float value)`

### Frida TypeScript Implementation
Add this method inside `frida_rpc_conn.ts` to control training speed dynamically:

```typescript
setTimeScale(scale: number) {
  const Time = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image.class("UnityEngine.Time");
  Time.method("set_timeScale").invoke(scale);
}
```
Expose via RPC:
```typescript
rpc.exports = {
  ...
  setTimeScale: (scale: number) => env.setTimeScale(scale),
};
```

---

## 2. Instant Episode Reset (Fast Respawn / Animation Skip)

### Concept
`RequestRestart()` currently triggers UI restart buttons and death animations, introducing a 1-2 second delay per episode reset. Locating or building an instant reset method bypasses animations and teleports the character back to the starting point instantly.

### Classes & Keywords to Search
- **Classes**: `Character`, `Daddy`, `GameController`, `SpawnManager`, `Ragdoll`
- **Keywords / Method Names**:
  - `Reset()`
  - `Respawn()`
  - `Init()`
  - `ResetState()`
  - `OnRestart()`
  - `startPosition` / `_initialPos`
- **Field Mutators**: Resetting rigidbodies directly:
  ```csharp
  _cachedBodyRigid.velocity = Vector2.zero;
  _cachedBodyRigid.angularVelocity = 0f;
  ```

---

## 3. Ground Contact & Leg Foot Detection (Enhanced State Space)

### Concept
Knowing if the left or right foot is currently in contact with the ground (`isGrounded`) provides a critical feature for gait control and stepping policy learning.

### Classes & Keywords to Search
- **Classes**: `Character`, `Leg`, `Foot`, `GroundCheck`, `CollisionSensor`
- **Keywords / Field Names**:
  - `isGrounded` / `_isGrounded`
  - `leftGrounded` / `rightGrounded`
  - `onGround` / `isTouchingGround`
  - `OnCollisionEnter2D` / `OnCollisionExit2D`
- **Physics Contact Check**:
  Checking if velocity along Y is zero or if contact count > 0.

---

## 4. Distance & Score Management

### Concept
Currently `GetCurrDistance()` is exported. Verifying score resets and distance tracking ensures accurate step-by-step reward calculations.

### Classes & Keywords to Search
- **Class**: `Score` (Assembly-CSharp)
- **Methods**:
  - `GetCurrDistance()`
  - `GetHighscore()`
  - `Reset()` / `ResetScore()`
  - `UpdateDistance()`
- **Fields**:
  - `m_Distance`
  - `_currentDistance`
  - `_highScore`

---

## 5. Direct Physics & Joint Torque Control (Advanced Action Space)

### Concept
Currently the action space is `Discrete(2)` (`OnGameTap`). If you want continuous RL control (e.g. continuous leg torques), search for internal joint force methods.

### Classes & Keywords to Search
- **Class**: `Character`
- **Keywords / Methods**:
  - `OnGameTap()`
  - `ApplyLegTorque(float)`
  - `SwitchLeg()`
  - `legCode` (tracks which leg is active/ready to swing)
  - `_legLeft1`, `_legRight1`, `_legLeft2`, `_legRight2` HingeJoint2D or SpringJoint2D components.

---

## Summary Table of Recommended Frida RPC Hooks

| Feature | Target Class | Target Method / Field | Key Benefit |
| :--- | :--- | :--- | :--- |
| **Physics Speedup** | `UnityEngine.Time` | `set_timeScale(float)` | 3x-5x faster RL simulation |
| **Ground Contact** | `Character` / `Foot` | `isGrounded` (bool) | Better step policy state |
| **Instant Reset** | `Character` / `GameController` | `Reset()` / `Respawn()` | Eliminates reset animation delay |
| **Distance Traveled** | `Score` / `Character` | `GetCurrDistance()` | Precise reward calculation |
| **Active Leg Code** | `Character` | `legCode` | Leg state for timing taps |
