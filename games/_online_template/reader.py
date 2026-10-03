"""<Game name> (online) -> GameState, from the game's own telemetry. Copy to games/<name>/ and fill in.
Rules: ONLINE_RULES.md. Never open the game process; tests/test_online.py enforces it."""
from dualsense.telemetry import UdpTelemetryReader


class TemplateTelemetry(UdpTelemetryReader):
    """TODO: decode the game's documented packet format in parse(). Until then every packet is ignored,
    so the bridge reports "waiting for game" and the controller keeps its DSX profile.

    Example for a made-up format <float health, float health_max, float ammo, uint32 shots_total>:

        health, health_max, ammo, total = struct.unpack_from("<fffI", data)
        shots = total - self.prev_total if self.prev_total is not None else 0
        self.prev_total = total
        return GameState(attached=True, in_flight=True, hull=health / health_max, energy=ammo, shots=shots)
    """

    def parse(self, data, state):
        return None
