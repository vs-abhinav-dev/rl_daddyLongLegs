// fix findExportByName function cannot find relevent modules
const _findExportByName = Module.prototype.findExportByName;
Module.prototype.findExportByName = function (name: string) {
  const fast = _findExportByName.call(this, name);
  if (fast !== null) return fast;

  for (const exp of this.enumerateExports()) {
    if (exp.name === name) return exp.address;
  }
  return null;
};

// Common read functions
function readLegAngle(transform: Il2Cpp.Object) {
  const euler = transform
    .method<Il2Cpp.ValueType>("get_eulerAngles", 0)
    .invoke();
  return euler.field<number>("z").value;
}

// Common Interfaces
interface State {
  frame: number;
  hasDied: boolean;
  vx: number;
  vy: number;
  legLeft1: number;
  legRight1: number;
  legLeft2: number;
  legRight2: number;
  headRotation: number;
  legCode: number;
  distance: number;
}

class DaddyEnv {
  private readonly Character = Il2Cpp.domain
    .assembly("Assembly-CSharp")
    .image.class("Character");

  // private readonly Daddy = Il2Cpp.domain
  // .assembly("Assembly-CSharp")
  // .image.class("Daddy");

  private readonly ClassScore = Il2Cpp.domain
    .assembly("Assembly-CSharp")
    .image.class("Score");

  private readonly scriptField = this.Character.field<Il2Cpp.Object>("script");

  private get character(): Il2Cpp.Object | null {
    const c = this.scriptField.value;
    return c.isNull() ? null : c;
  }

  private get score(): Il2Cpp.Object | null {
    const s = this.ClassScore.method<Il2Cpp.Object>("get_script").invoke();
    return s.isNull() ? null : s;
  }

  private frame = 0;

  incFrame() {
    this.frame++;
  }

  readState(): Partial<State> {
    const character = this.character;
    if (!character) return {};

    const rb = character.field<Il2Cpp.Object>("_cachedBodyRigid").value;
    const vel = rb.method<Il2Cpp.ValueType>("get_velocity", 0).invoke();
    const vx = vel.field<number>("x").value;
    const vy = vel.field<number>("y").value;
    const hasDied = character.method<boolean>("get_hasDied", 0).invoke();
    const head = character.field<Il2Cpp.Object>("_head").value;
    const headRotation = head
      .method<Il2Cpp.ValueType>("get_eulerAngles", 0)
      .invoke();

    const hz = headRotation.field<number>("z").value;

    const legLeft2 = character.field<Il2Cpp.Object>("_legLeft2").value;
    const legRight2 = character.field<Il2Cpp.Object>("_legRight2").value;

    const legLeft1 = character.field<Il2Cpp.Object>("_legLeft1").value;
    const legRight1 = character.field<Il2Cpp.Object>("_legRight1").value;

    const legCode = character.field<number>("legCode").value;
    let distance = 0;
    try {
      distance = character.method<number>("GetCurrDistance", 0).invoke();
    } catch (e) {
      distance = 0;
    }

    return {
      frame: this.frame,
      hasDied,
      vx,
      vy,
      legLeft1: readLegAngle(legLeft1),
      legRight1: readLegAngle(legRight1),
      legLeft2: readLegAngle(legLeft2),
      legRight2: readLegAngle(legRight2),
      legCode,
      headRotation: hz,
      distance: distance,
    };
  }

  tap() {
    const character = this.character;
    if (!character) return;

    character.method("OnGameTap").invoke();
  }

  restart() {
    const character = this.character;
    if (!character) return;

    character.method("RequestRestart").invoke();
  }

  getCurrDistance() {
    const character = this.character;
    if (!character) return 0;

    try {
      const distance = character.method<number>("GetCurrDistance", 0).invoke();
      return distance;
    } catch (e) {
      return 0;
    }
  }

  getHighscore() {
    const scoreValue = this.score;
    if (!scoreValue) return 0;

    try {
      const highscore = scoreValue.method<number>("GetHighscore", 0).invoke();
      return highscore;
    } catch (e) {
      return 0;
    }
  }

  get fixedUpdateMethod() {
    return this.Character.method("FixedUpdate");
  }
}

// main function
//
//

import "frida-il2cpp-bridge";
Il2Cpp.perform(() => {
  // init the state object
  let stateObj: Partial<State> = {};

  // attach interceptor
  //
  //
  const env = new DaddyEnv();

  Interceptor.attach(env.fixedUpdateMethod.virtualAddress, {
    onLeave() {
      env.incFrame();
      stateObj = env.readState();
    },
  });

  rpc.exports = {
    getState: () => stateObj,
    tap: () => env.tap(),
    restart: () => env.restart(),
    getCurrDistance: () => env.getCurrDistance(),
    getHighscore: () => env.getHighscore(),
  };
});
