"""Online track: game state from telemetry the game sends on purpose (UDP), never from its memory.

Many games stream state to a local UDP port when you enable it in their settings (racing games:
F1, Forza "Data Out", Assetto Corsa...). A game subclasses UdpTelemetryReader and implements parse()."""
import socket

from .effects import GameState


class UdpTelemetryReader:
    """Listens on 127.0.0.1:<port>; each read() drains pending packets and returns the latest state.
    No packet for `timeout` seconds -> the game is not sending (menu, closed, telemetry off)."""

    def __init__(self, port, clock, timeout=1.0, host="127.0.0.1"):
        self.clock = clock
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.setblocking(False)
        self.state = GameState()
        self.last_packet = None

    def parse(self, data, state):
        """Turn one packet into a GameState. `state` is the previous one (for counters such as shots).
        Return None to ignore the packet."""
        raise NotImplementedError

    def read(self):
        now = self.clock()
        shots = 0
        while True:
            try:
                data = self.sock.recv(65535)
            except (BlockingIOError, ConnectionResetError):
                break
            state = self.parse(data, self.state)
            if state is not None:
                shots += state.shots              # shots reported by several packets in one frame add up
                self.state, self.last_packet = state, now
        if self.last_packet is None or now - self.last_packet > self.timeout:
            return GameState()
        return GameState(attached=True, in_flight=self.state.in_flight, energy=self.state.energy,
                         hull=self.state.hull, shots=shots)

    def close(self):
        self.sock.close()
