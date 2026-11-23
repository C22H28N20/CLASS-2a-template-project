from abc import abstractmethod
import math
from pathlib import Path
import time
import pyglet
from pyglet.gl import glClearColor
from pyglet.window import key
from engines.base_engine import BACKGROUND_COLOR, BaseEngine

_BG = tuple(c / 255 for c in BACKGROUND_COLOR) + (1.0,)
AUDIO_FILE = "audio/smith.mp3"
CALM_DARK = (8, 28, 70)
CALM_LIGHT = (35, 120, 185)
ENERGETIC_DARK = (5, 125, 145)
ENERGETIC_LIGHT = (190, 255, 235)
TREBLE_HIGHLIGHT = (255, 245, 180)
WAVE_POINTS = 128
BAND_CENTERS = (0.17, 0.5, 0.83)
BAND_SMOOTHING = 0.2
MIN_BAND_GAIN = 0.0
MAX_BAND_GAIN = 2.0
BAND_GAIN_STEP = 0.1


class PygletEngine(BaseEngine):
    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        target_fps: int = 60,
        audio_file: str = AUDIO_FILE,
    ) -> None:
        super().__init__(width, height, title, target_fps)
        self.audio_file = audio_file

    def restart_audio(self) -> None:
        now = time.perf_counter()
        if now - self._last_audio_restart_at < 0.25:
            return
        self._last_audio_restart_at = now

        self.audio_player.loop = True
        self.audio_player.pause()
        self.audio_player.seek(0)
        self.audio_player.play()

        if self._restart_playback_callback is not None:
            self._restart_playback_callback()

        self._wave_phase = 0.0
        self._wave_heights = [0.0] * WAVE_POINTS
        self._previous_bass = 0.0
        self._previous_amplitude = 0.0
        self._kick_strength = 0.0
        self._colour_drive = 0.0
        self._treble_pulse = 0.0

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
        self._band_gain = {"bass": 1.0, "mid": 1.0, "treble": 1.0}
        self._selected_band = "bass"
        self._pitch = 1.0
        self._paused = False
        self._last_audio_restart_at = -1.0
        self._pause_playback_callback = None
        self._set_playback_speed_callback = None
        self._restart_playback_callback = None
        self._wave_batch = pyglet.graphics.Batch()
        self._ui_batch = pyglet.graphics.Batch()
        stats_panel_x = 10
        stats_panel_y = self.height - 220
        stats_panel_width = 390
        stats_panel_height = 210
        self._stats_title = pyglet.text.Label(
            "AUDIO STATISTICS",
            x=stats_panel_x + 10,
            y=self.height - 58,
            font_size=15,
            color=(235, 245, 255, 255),
            batch=self._ui_batch,
        )
        self._track_label = pyglet.text.Label(
            Path(self.audio_file).name,
            x=10,
            y=self.height - 36,
            font_size=20,
            color=(245, 250, 255, 255),
            batch=self._ui_batch,
        )
        self._time_label = pyglet.text.Label(
            "00:00 / 00:00",
            x=10,
            y=self.height - 82,
            font_size=12,
            color=(210, 230, 245, 255),
            batch=self._ui_batch,
        )

        stat_names = ("BASS", "MID", "TREBLE", "CENTROID", "ONSET")
        stat_colours = (
            (255, 70, 145),
            (70, 210, 255),
            (255, 235, 100),
            (255, 210, 95),
            (190, 220, 255),
        )
        self._stat_names = []
        self._stat_values = []
        self._stat_bar_backgrounds = []
        self._stat_bars = []
        self._stat_colours = stat_colours

        for index, name in enumerate(stat_names):
            row_y = self.height - 112 - index * 31
            name_label = pyglet.text.Label(
                name,
                x=stats_panel_x + 12,
                y=row_y,
                font_size=11,
                color=stat_colours[index] + (255,),
                batch=self._ui_batch,
            )
            value_label = pyglet.text.Label(
                "0.00",
                x=stats_panel_x + 126,
                y=row_y,
                font_size=11,
                anchor_x="right",
                color=(235, 245, 255, 255),
                batch=self._ui_batch,
            )
            bar_background = pyglet.shapes.Rectangle(
                stats_panel_x + 138,
                row_y - 5,
                115,
                10,
                color=(70, 90, 115),
                batch=self._ui_batch,
            )
            bar = pyglet.shapes.Rectangle(
                stats_panel_x + 138,
                row_y - 5,
                1,
                10,
                color=stat_colours[index],
                batch=self._ui_batch,
            )
            self._stat_names.append(name_label)
            self._stat_values.append(value_label)
            self._stat_bar_backgrounds.append(bar_background)
            self._stat_bars.append(bar)
        self._band_selection_label = pyglet.text.Label(
            "SELECTED: BASS  |  Gain: 1.00x",
            x=self.width / 2,
            y=self.height - 36,
            anchor_x="center",
            font_size=13,
            color=(190, 255, 235, 255),
            batch=self._ui_batch,
        )
        self._controls_label = pyglet.text.Label(
            "1 bass | 2 mid | 3 treble | UP/DOWN selected boost | LEFT/RIGHT pitch | SPACE pause",
            x=self.width / 2,
            y=14,
            anchor_x="center",
            font_size=11,
            color=(225, 242, 250, 255),
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
        self.audio_source = pyglet.media.load(self.audio_file, streaming=False)
        self.audio_player.volume = 0.5
        self.audio_player.loop = True
        self.audio_player.queue(self.audio_source)

        def on_audio_end() -> None:
            self.restart_audio()

        self.audio_player.push_handlers(on_eos=on_audio_end)
        self.audio_player.loop = True
        self.audio_player.play()
        self.audio_player.loop = True
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
            if symbol == key._1:
                self._selected_band = "bass"
            elif symbol == key._2:
                self._selected_band = "mid"
            elif symbol == key._3:
                self._selected_band = "treble"
            elif symbol == key.UP:
                gain = self._band_gain[self._selected_band]
                self._band_gain[self._selected_band] = min(
                    MAX_BAND_GAIN,
                    round(gain + BAND_GAIN_STEP, 1),
                )
            elif symbol == key.DOWN:
                gain = self._band_gain[self._selected_band]
                self._band_gain[self._selected_band] = max(
                    MIN_BAND_GAIN,
                    round(gain - BAND_GAIN_STEP, 1),
                )
            elif symbol == key.LEFT:
                self._pitch = max(0.5, self._pitch - 0.1)
                self.audio_player.pitch = self._pitch
                if self._set_playback_speed_callback is not None:
                    self._set_playback_speed_callback(self._pitch)
            elif symbol == key.RIGHT:
                self._pitch = min(2.0, self._pitch + 0.1)
                self.audio_player.pitch = self._pitch
                if self._set_playback_speed_callback is not None:
                    self._set_playback_speed_callback(self._pitch)
            elif symbol == key.SPACE:
                self._paused = not self._paused
                if self._paused:
                    self.audio_player.pause()
                else:
                    self.audio_player.play()
                if self._pause_playback_callback is not None:
                    self._pause_playback_callback(self._paused)
            self._update_controls_label()

    def _update_controls_label(self) -> None:
        selected_name = self._selected_band.upper()
        gain = self._band_gain[self._selected_band]
        playback = "PAUSED" if self._paused else "PLAYING"
        self._band_selection_label.text = (
            f"SELECTED: {selected_name}  |  Gain: {gain:.2f}x  |  "
            f"Pitch: {self._pitch:.1f}x  |  {playback}"
        )
        self._controls_label.text = (
            "1 bass | 2 mid | 3 treble | "
            "UP/DOWN selected boost | LEFT/RIGHT pitch | SPACE pause/play"
        )

    def set_playback_callbacks(
        self,
        pause_callback,
        speed_callback,
        restart_callback,
    ) -> None:
        self._pause_playback_callback = pause_callback
        self._set_playback_speed_callback = speed_callback
        self._restart_playback_callback = restart_callback

    def handle_events(self) -> bool:
        # BaseEngine.run() owns the loop, so events are dispatched manually
        # here each frame rather than handing control to pyglet.app.run().
        pyglet.clock.tick()
        self.window.dispatch_events()
        return not self._should_close

    def update(self, audio_features: dict) -> None:
        if (
            not self._paused
            and self.audio_source.duration is not None
            and self.audio_player.time >= max(0.0, self.audio_source.duration - 0.05)
        ):
            self.restart_audio()

        if self._paused:
            elapsed_seconds = int(round(self.audio_player.time))
            elapsed_minutes, elapsed_remainder = divmod(elapsed_seconds, 60)
            total_seconds = int(self.audio_source.duration)
            total_minutes, total_remainder = divmod(total_seconds, 60)
            self._time_label.text = (
                f"{elapsed_minutes:02d}:{elapsed_remainder:02d} / "
                f"{total_minutes:02d}:{total_remainder:02d}"
            )
            return

        amplitude = float(audio_features.get("peak", 0.0))
        amplitude = min(1.0, max(0.0, amplitude))
        band_levels = {
            band: min(
                1.0,
                max(
                    0.0,
                    float(audio_features.get(band, 0.0))
                    * self._band_gain[band],
                ),
            )
            for band in ("bass", "mid", "treble")
        }
        centroid = float(audio_features.get("centroid", 0.0))
        centroid_display = min(1.0, centroid / 22050.0)
        onset = float(audio_features.get("onset", 0.0))
        onset_display = min(1.0, abs(onset) / 100.0)
        stat_values = (
            band_levels["bass"],
            band_levels["mid"],
            band_levels["treble"],
            centroid_display,
            onset_display,
        )
        for value_label, bar, stat_value in zip(
            self._stat_values,
            self._stat_bars,
            stat_values,
        ):
            stat_value = min(1.0, max(0.0, stat_value))
            value_label.text = f"{stat_value:.2f}"
            bar.width = max(1.0, 115 * stat_value)

        elapsed_seconds = int(round(self.audio_player.time))
        elapsed_minutes, elapsed_remainder = divmod(elapsed_seconds, 60)
        total_seconds = int(self.audio_source.duration)
        total_minutes, total_remainder = divmod(total_seconds, 60)
        self._time_label.text = (
            f"{elapsed_minutes:02d}:{elapsed_remainder:02d} / "
            f"{total_minutes:02d}:{total_remainder:02d}"
        )
        audio_drive = min(1.0, math.sqrt(amplitude) * 1.25)
        audio_drive = min(1.0, audio_drive * 1.35)
        average_gain = sum(self._band_gain.values()) / len(self._band_gain)
        gain_colour_drive = (average_gain - MIN_BAND_GAIN) / (
            MAX_BAND_GAIN - MIN_BAND_GAIN
        )
        colour_target = audio_drive * 0.7 + gain_colour_drive * 0.3
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
        wave_speed = (
            0.035
            + audio_drive * 0.09
            + band_levels["bass"] * 0.05
        ) * self._pitch
        self._wave_phase += wave_speed

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

            swell = math.sin(
                self._wave_phase + position * math.tau * 1.2
            )
            ripple = math.sin(
                self._wave_phase * 1.35 + position * math.tau * 2.8
            )
            fine_ripple = math.sin(
                self._wave_phase * 2.1 + position * math.tau * 5.5
            )
            surface_shape = swell * 0.62 + ripple * 0.28 + fine_ripple * 0.1
            wave = 0.5 + surface_shape * 0.5
            band_drive = min(1.0, math.sqrt(band_level) * 1.55)
            kick_position = math.exp(
                -((position - 0.17) / 0.09) ** 2
            )
            kick_spike = self._kick_strength * kick_position
            swell_height = (
                audio_drive
                * band_drive
                * (0.15 + wave * 0.85 + kick_spike * 1.8)
                * self._max_bar_height
            )
            baseline_swell = (
                self._max_bar_height
                * (0.07 + abs(surface_shape) * 0.14)
            )
            swell_height += baseline_swell
            target_height = swell_height * (0.62 + surface_shape * 0.72)
            target_height = max(0.0, min(target_height, self._max_bar_height))
            response_rate = 0.48 if target_height > self._wave_heights[index] else 0.28
            self._wave_heights[index] += (
                target_height - self._wave_heights[index]
            ) * response_rate
            height = self._wave_heights[index]
            base_color = tuple(
                round(dark + (light - dark) * max(0.0, wave))
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
