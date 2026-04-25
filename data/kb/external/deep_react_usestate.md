# React useState Hook

## Reference

### `useState(initialState)`

Call `useState` at the top level of your component to declare a state variable.

```javascript
import { useState } from 'react';

function MyComponent() {
  const [age, setAge] = useState(28);
  const [name, setName] = useState('Taylor');
  const [todos, setTodos] = useState(() => createTodos());
  // ...
}
```

The convention is to name state variables like `[something, setSomething]` using array destructuring.

#### Parameters

- `initialState`: The value you want the state to be initially. It can be a value of any type, but there is a special behavior for functions. This argument is ignored after the initial render.
- If you pass a function as `initialState`, it will be treated as an initializer function. It should be pure, should take no arguments, and should return a value of any type. React will call your initializer function when initializing the component, and store its return value as the initial state.

#### Returns

`useState` returns an array with exactly two values:
1. The current state. During the first render, it will match the `initialState` you have passed.
2. The `set` function that lets you update the state to a different value and trigger a re-render.

#### Caveats

- `useState` is a Hook, so you can only call it at the top level of your component or your own Hooks. You can’t call it inside loops or conditions.
- In Strict Mode, React will call your initializer function twice in order to help you find accidental impurities. The result from one of the calls will be ignored.

---

### `set` functions (e.g. `setSomething(nextState)`)

The `set` function returned by `useState` lets you update the state to a different value and trigger a re-render. You can pass the next state directly, or a function that calculates it from the previous state:

```javascript
const [name, setName] = useState('Edward');
function handleClick() {
  setName('Taylor');
  setAge(a => a + 1);
}
```

#### Parameters

- `nextState`: The value that you want the state to be.
- If you pass a function as `nextState`, it will be treated as an updater function. It must be pure, should take the pending state as its only argument, and should return the next state. React will queue this updater function.

#### Returns

`set` functions do not have a return value.

#### Caveats

- The `set` function only updates the state variable for the next render. If you read the state variable right after calling the `set` function, you will still get the old value.
- If the new value is identical to the current state (based on `Object.is`), React will skip re-rendering the component and its children.
- React batches state updates. It updates the screen after all the event handlers have run. Use `flushSync` to force early updates if required.
- Calling the `set` function during rendering is only allowed from within the currently rendering component.

## Usage Guide

### Updating objects and arrays in state

You can put objects and arrays into state. In React, state is considered read-only, so you should replace it rather than mutate your existing objects.

```javascript
// 🚩 Don't mutate an object in state like this:
form.firstName = 'Taylor';

// ✅ Replace state with a new object
setForm({
  ...form,
  firstName: 'Taylor'
});
```

### Updating state based on the previous state

If you need to update state based on the previous state multiple times in one event handler, passing the literal next state value can cause issues due to state snapshot behaviour.

```javascript
function handleClick() {
  // If age is 42, each setAge(age + 1) evaluates to setAge(43).
  setAge(age + 1);
  setAge(age + 1);
  setAge(age + 1);
}
```

To solve this problem, you may pass an updater function:

```javascript
function handleClick() {
  // setAge(42 => 43), setAge(43 => 44), etc.
  setAge(a => a + 1);
  setAge(a => a + 1);
  setAge(a => a + 1);
}
```