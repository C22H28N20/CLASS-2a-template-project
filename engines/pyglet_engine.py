from abc import abstractmethod
import random
import pyglet
from pyglet.gl import glClearColor
from pyglet.window import key
from engines.base_engine import BACKGROUND_COLOR, BaseEngine

_BG = tuple(c / 255 for c in BACKGROUND_COLOR) + (1.0,)
AUDIO_FILE = "audio/dead.mp3"


class PygletEngine(BaseEngine):
    def setup(self) -> None:
        self.window = pyglet.window.Window(self.width, self.height, caption=self.title)
        self._should_close = False
        self._bar_name = "Audio Amplitude"
        self._bar_count = 5
        self._bar_width = self.width * 0.08
        self._bar_gap = self.width * 0.02
        total_width = self._bar_count * self._bar_width + (self._bar_count - 1) * self._bar_gap
        self._bar_x = (self.width - total_width) / 2
        self._bar_y = self.height * 0.1
        self._max_bar_height = self.height * 0.55
        self._bar_heights = [0.0] * self._bar_count
        self._bar_scales = (0.6, 0.6, 0.6, 0.6, 0.6)  # Adjusted scales for each bar
        self._bars = [
            pyglet.shapes.Rectangle(
                self._bar_x + index * (self._bar_width + self._bar_gap),
                self._bar_y,
                self._bar_width,
                0,
                color=(80, 190, 255),
            )
            for index in range(self._bar_count)
        ]
        self._bar_label = pyglet.text.Label(
            self._bar_name,
            x=self.width / 2,
            y=self._bar_y + self._max_bar_height + 10,
            anchor_x="center",
            
            color=(255, 255, 255, 255),
        )



        self.audio_player = pyglet.media.Player()
        self.audio_source = pyglet.media.load(AUDIO_FILE, streaming=False)
        self.audio_player.volume = 0.5
        self.audio_player.queue(self.audio_source)
        self.audio_player.play()

        glClearColor(_BG[0], _BG[1], _BG[2], _BG[3])
        

        @self.window.event
        def on_close():
            self._should_close = True
            return pyglet.event.EVENT_HANDLED

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol == key.ESCAPE:
                self._should_close = True
                return pyglet.event.EVENT_HANDLED

    def handle_events(self) -> bool:
        # BaseEngine.run() owns the loop, so events are dispatched manually
        # here each frame rather than handing control to pyglet.app.run().
        self.window.dispatch_events()
        return not self._should_close

   
    def update(self, audio_features: dict) -> None:
        amplitude = float(audio_features.get("peak", 0.0))
        amplitude = min(1.0, max(0.0, amplitude))
        treble = float(audio_features.get("treble", 0.0))
        treble = min(1.0, max(0.0, treble))
        bass = float(audio_features.get("bass", 0.0))
        bass = min(1.0, max(0.0, bass))
        print(audio_features)

        for index, bar in enumerate(self._bars):
            target_height = amplitude * self._bar_scales[index] * self._max_bar_height
            self._bar_heights[index] += (target_height - self._bar_heights[index]) * 0.35
            bar.height = self._bar_heights[index]
            bar.color = (
                int(random.randint(50, 255) * float(bass)),
                int(random.randint(50, 255) * float(bass)),
                int(random.randint(50, 255) * float(bass)),
            )


    def render(self) -> None:
        self.window.clear()
        for bar in self._bars:
            bar.draw()
        self._bar_label.draw()
        self.window.flip()

    def teardown(self) -> None:
        self.window.close()
