from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class ModalLayer:
    name: str
    consume_input: bool = True
    on_close: Callable[[], None] | None = None

class ModalStack:
    """Simple LIFO modal stack.

    Integration points:
    - push(name): adds a modal layer (optionally record overlay sprite group creation externally).
    - pop(name): removes the top if matching.
    - top(): returns current top name.
    - active(): bool whether any modal present.
    
    Future extension: store per-modal metadata (e.g., fade timers, input routing hooks).
    """
    def __init__(self):
        self._stack: list[ModalLayer] = []

    def push(self, layer: ModalLayer):
        self._stack.append(layer)

    def pop(self, name: str | None = None):
        if not self._stack:
            return
        top = self._stack[-1]
        if name and top.name != name:
            return
        popped = self._stack.pop()
        if popped.on_close:
            try:
                popped.on_close()
            except Exception:
                pass

    def clear(self):
        while self._stack:
            self.pop()

    def top(self) -> ModalLayer | None:
        return self._stack[-1] if self._stack else None

    def active(self) -> bool:
        return bool(self._stack)

__all__ = ["ModalStack", "ModalLayer"]
