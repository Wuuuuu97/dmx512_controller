import time

from PyQt5.QtCore import QThread, pyqtSignal


class ChaserEngine(QThread):
    """Scene chaser — auto-cycles through scenes with optional cross-fade.

    Runs in a background thread. Emits ``values_updated`` at each
    interpolation step so the UI can forward them to the transmitter.

    Usage::

        engine = ChaserEngine()
        engine.set_scenes(scene_list)   # list of {name, channels}
        engine.interval_ms = 3000       # hold time between scenes
        engine.fade_ms = 1000           # cross-fade duration
        engine.values_updated.connect(self._on_chaser_values)
        engine.start()                  # start the thread
        ...
        engine.stop()
    """

    values_updated = pyqtSignal(list)  # 512 ints — intermediate or final frame
    scene_changed = pyqtSignal(int)    # current scene index
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scenes = []         # each item: {"name": str, "channels": list[512]}
        self.interval_ms = 2000  # hold time at each scene (ms)
        self.fade_ms = 500       # cross-fade duration (ms)
        self.loop = True         # restart from beginning when done
        self._running = False

    def set_scenes(self, scenes):
        """Set the scene list. Each scene dict must have 'name' and 'channels'."""
        self.scenes = list(scenes)

    def stop(self):
        self._running = False

    def run(self):
        if not self.scenes:
            self.finished.emit()
            return

        self._running = True
        current = [0] * 512

        while self._running:
            for idx, scene in enumerate(self.scenes):
                if not self._running:
                    break

                target = scene["channels"]
                if len(target) != 512:
                    continue

                # Cross-fade
                if self.fade_ms > 0 and current != target:
                    steps = max(1, int(self.fade_ms / 30))  # ~33 fps steps
                    for step in range(1, steps + 1):
                        if not self._running:
                            break
                        t = step / steps
                        blended = [
                            int(current[i] + (target[i] - current[i]) * t)
                            for i in range(512)
                        ]
                        self.values_updated.emit(blended)
                        self.msleep(30)

                current = list(target)
                self.values_updated.emit(current)
                self.scene_changed.emit(idx)

                if not self._running:
                    break

                # Hold at this scene
                if self.interval_ms > 0:
                    self.msleep(self.interval_ms)

            if not self.loop:
                break

        self.finished.emit()
