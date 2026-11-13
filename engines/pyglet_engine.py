from abc import abstractmethod
import math
import pyglet
from pyglet.gl import glClearColor
from pyglet.window import key, mouse
from engines.base_engine import BACKGROUND_COLOR, BaseEngine

_BG = tuple(c / 255 for c in BACKGROUND_COLOR) + (1.0,)
AUDIO_FILE = "audio/smith.mp3"
CALM_DARK = (8, 28, 70)
CALM_LIGHT = (35, 120, 185)
ENERGETIC_DARK = (5, 125, 145)
ENERGETIC_LIGHT = (190, 255, 235)
TREBLE_HIGHLIGHT = (255, 245, 180)
WAVE_POINTS = 96
BAND_CENTERS = (0.17, 0.5, 0.83)
BAND_SMOOTHING = 0.2
SLIDER_MIN_GAIN = 0.0
SLIDER_MAX_GAIN = 2.0


class PygletEngine(BaseEngine):
    def setup(self) -> None:
        self.window = pyglet.window.Window(self.width, self.height, caption=self.title)
        self._should_close = False
        self._bar_count = 5
        self._bar_width = self.width * 0.08
        self._bar_gap = self.width * 0.02
        self._ocean_width = self.width
        self._bar_x = 0.0
        self._bar_y = 0.0
        self._max_bar_height = self.height
        self._wave_phase = 0.0
        self._wave_heights = [0.0] * WAVE_POINTS
        self._previous_bass = 0.0
        self._previous_amplitude = 0.0
        self._kick_strength = 0.0
        self._colour_drive = 0.0
        self._treble_pulse = 0.0
        self._frequency_gain = 1.0
        self._slider_colour_drive = 0.5
        self._slider_dragging = False
        self._wave_batch = pyglet.graphics.Batch()
        self._ui_batch = pyglet.graphics.Batch()
        self._slider_left = self.width * 0.25
        self._slider_width = self.width * 0.5
        self._slider_y = self.height - 36
        self._slider_track = pyglet.shapes.Rectangle(
            self._slider_left,
            self._slider_y,
            self._slider_width,
            6,
            color=(75, 110, 135),
            batch=self._ui_batch,
        )
        self._slider_knob = pyglet.shapes.Circle(
            self._slider_left + self._slider_width / 2,
            self._slider_y + 3,
            12,
            color=(190, 255, 235),
            batch=self._ui_batch,
        )
        self._slider_label = pyglet.text.Label(
            "Frequency boost: 1.00x",
            x=self.width / 2,
            y=self._slider_y + 22,
            anchor_x="center",
            color=(220, 240, 245, 255),
            batch=self._ui_batch,
        )
        self._wave_triangles = [
            (
                pyglet.shapes.Triangle(0, 0, 0, 0, 0, 0, batch=self._wave_batch),
                pyglet.shapes.Triangle(0, 0, 0, 0, 0, 0, batch=self._wave_batch),
            )
            for _ in range(WAVE_POINTS - 1)
        ]

        self.audio_player = pyglet.media.Player()
        self.audio_source = pyglet.media.load(AUDIO_FILE, streaming=False)
        self.audio_player.volume = 0.5
        self.audio_player.queue(self.audio_source)

        def on_audio_end() -> None:
            self._should_close = True

        self.audio_player.push_handlers(on_eos=on_audio_end)
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

        @self.window.event
        def on_mouse_press(x, y, button, modifiers):
            if button == mouse.LEFT and self._slider_y - 16 <= y <= self._slider_y + 22:
                self._slider_dragging = True
                self._set_frequency_gain(x)

        @self.window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            if self._slider_dragging and buttons & mouse.LEFT:
                self._set_frequency_gain(x)

        @self.window.event
        def on_mouse_release(x, y, button, modifiers):
            if button == mouse.LEFT:
                self._slider_dragging = False

    def _set_frequency_gain(self, x: float) -> None:
        position = (x - self._slider_left) / self._slider_width
        position = min(1.0, max(0.0, position))
        self._frequency_gain = (
            SLIDER_MIN_GAIN
            + position * (SLIDER_MAX_GAIN - SLIDER_MIN_GAIN)
        )
        self._slider_colour_drive = position
        self.audio_player.volume = min(1.0, self._frequency_gain * 0.5)
        self._slider_knob.x = self._slider_left + position * self._slider_width
        self._slider_label.text = (
            f"Frequency boost: {self._frequency_gain:.2f}x | "
            f"Volume: {self.audio_player.volume:.0%}"
        )

    def handle_events(self) -> bool:
        # BaseEngine.run() owns the loop, so events are dispatched manually
        # here each frame rather than handing control to pyglet.app.run().
        self.window.dispatch_events()
        return not self._should_close

    def update(self, audio_features: dict) -> None:
        amplitude = float(audio_features.get("peak", 0.0)) * self._frequency_gain
        amplitude = min(1.0, max(0.0, amplitude))
        band_levels = {
            band: min(
                1.0,
                max(0.0, float(audio_features.get(band, 0.0)) * self._frequency_gain),
            )
            for band in ("bass", "mid", "treble")
        }
        audio_drive = min(1.0, math.sqrt(amplitude) * 1.25)
        colour_target = audio_drive * 0.7 + self._slider_colour_drive * 0.3
        self._colour_drive += (colour_target - self._colour_drive) * 0.12
        self._treble_pulse += (
            band_levels["treble"] - self._treble_pulse
        ) * 0.7
        dark_colour = tuple(
            round(calm + (energetic - calm) * self._colour_drive)
            for calm, energetic in zip(CALM_DARK, ENERGETIC_DARK)
        )
        light_colour = tuple(
            round(calm + (energetic - calm) * self._colour_drive)
            for calm, energetic in zip(CALM_LIGHT, ENERGETIC_LIGHT)
        )
        bass_rise = max(0.0, band_levels["bass"] - self._previous_bass)
        amplitude_rise = max(0.0, amplitude - self._previous_amplitude)
        kick = min(1.0, bass_rise * 3.5 + amplitude_rise * 2.0)
        self._kick_strength = max(kick, self._kick_strength * 0.65)
        self._previous_bass = band_levels["bass"]
        self._previous_amplitude = amplitude
        self._wave_phase += 0.075

        wave_points = []
        for index in range(WAVE_POINTS):
            position = index / (WAVE_POINTS - 1)
            x = self._bar_x + position * self._ocean_width
            band_weights = [
                math.exp(
                    -((position - center) / BAND_SMOOTHING) ** 2
                )
                for center in BAND_CENTERS
            ]
            weight_total = sum(band_weights)
            band_level = sum(
                weight * level
                for weight, level in zip(
                    band_weights,
                    (band_levels["bass"], band_levels["mid"], band_levels["treble"]),
                )
            ) / weight_total

            wave = (
                math.sin(self._wave_phase + position * math.tau * 1.5) * 0.55
                + math.sin(self._wave_phase * 0.7 + position * math.tau * 3) * 0.3
                + 0.75
            )
            wave = max(0.0, min(1.0, wave))
            band_drive = min(1.0, math.sqrt(band_level) * 1.15)
            kick_position = math.exp(
                -((position - 0.17) / 0.09) ** 2
            )
            kick_spike = self._kick_strength * kick_position
            target_height = (
                audio_drive
                * band_drive
                * (0.15 + wave * 0.8 + kick_spike * 1.5)
                * self._max_bar_height
            )
            target_height = min(target_height, self._max_bar_height)
            response_rate = 0.32 if target_height > self._wave_heights[index] else 0.18
            self._wave_heights[index] += (
                target_height - self._wave_heights[index]
            ) * response_rate
            height = self._wave_heights[index]
            base_color = tuple(
                round(dark + (light - dark) * wave)
                for dark, light in zip(dark_colour, light_colour)
            )
            color = tuple(
                round(base + (highlight - base) * self._treble_pulse * 0.5)
                for base, highlight in zip(base_color, TREBLE_HIGHLIGHT)
            )
            wave_points.append((x, self._bar_y + height, color))

        for index, (first, second) in enumerate(
            zip(wave_points, wave_points[1:])
        ):
            first_x, first_y, first_color = first
            second_x, second_y, second_color = second
            upper, lower = self._wave_triangles[index]
            upper.x, upper.y = first_x, first_y
            upper.x2, upper.y2 = second_x, second_y
            upper.x3, upper.y3 = first_x, self._bar_y
            upper.color = first_color
            lower.x, lower.y = second_x, second_y
            lower.x2, lower.y2 = second_x, self._bar_y
            lower.x3, lower.y3 = first_x, self._bar_y
            lower.color = second_color

    def render(self) -> None:
        self.window.clear()
        self._wave_batch.draw()
        self._ui_batch.draw()
        self.window.flip()

    def teardown(self) -> None:
        self.audio_player.pause()
        self.audio_player.delete()
        self.window.close()
