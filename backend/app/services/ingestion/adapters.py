"""Log source adapter architecture (Module 2).

The MVP genuinely supports FILE (upload), SIMULATED (synthetic stream) and
sample import. SYSLOG / HTTP / WINDOWS / FIREWALL adapters expose the real
interface a production connector would implement but honestly report that they
are not configured/verified - we never claim a live enterprise link works.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class LogSourceAdapter(ABC):
    kind: str = "BASE"
    #: does this adapter work end-to-end in the MVP?
    mvp_supported: bool = False
    #: human description of what a production implementation requires
    requires: str = ""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def status(self) -> dict:
        ...

    def fetch(self) -> bytes:
        """Pull available data as raw bytes. Raises if not supported."""
        raise NotImplementedError(f"{self.kind} adapter cannot fetch in the MVP")


class FileAdapter(LogSourceAdapter):
    kind = "FILE"
    mvp_supported = True
    requires = "user uploads a file or imports a bundled sample"

    def status(self) -> dict:
        return {"kind": self.kind, "status": "READY",
                "detail": "accepts uploads and sample imports"}


class SimulatedAdapter(LogSourceAdapter):
    kind = "SIMULATED"
    mvp_supported = True
    requires = "generates synthetic records for demos"

    _TEMPLATES = [
        "{ts} host-{h} sshd[{pid}]: Failed password for {user} from {ip} port {port} ssh2",
        "{ts} host-{h} sshd[{pid}]: Accepted password for {user} from {ip} port {port} ssh2",
        '{ip} - - [{ap_ts}] "GET /api/status HTTP/1.1" 200 512 "-" "curl/8.4"',
    ]

    def status(self) -> dict:
        return {"kind": self.kind, "status": "READY", "detail": "synthetic stream generator"}

    def fetch(self) -> bytes:
        n = int(self.config.get("count", 25))
        users = ["admin", "root", "svc-backup", "jdoe"]
        now = datetime.now(timezone.utc)
        lines = []
        for i in range(n):
            t = now - timedelta(seconds=(n - i) * 3)
            lines.append(random.choice(self._TEMPLATES).format(
                ts=t.strftime("%b %d %H:%M:%S"),
                ap_ts=t.strftime("%d/%b/%Y:%H:%M:%S +0000"),
                h=random.randint(1, 4), pid=random.randint(1000, 9999),
                user=random.choice(users),
                ip=f"192.168.1.{random.randint(2, 254)}",
                port=random.randint(1024, 65535),
            ))
        return "\n".join(lines).encode()


class _UnconfiguredAdapter(LogSourceAdapter):
    def status(self) -> dict:
        return {
            "kind": self.kind,
            "status": "NOT_CONFIGURED",
            "detail": f"interface defined; production connector requires: {self.requires}",
        }


class SyslogAdapter(_UnconfiguredAdapter):
    kind = "SYSLOG"
    requires = "a bound UDP/TCP 514 listener or relay endpoint + network access"


class HTTPAdapter(_UnconfiguredAdapter):
    kind = "HTTP"
    requires = "an authenticated pull endpoint URL + credentials in the environment"


class WindowsAdapter(_UnconfiguredAdapter):
    kind = "WINDOWS"
    requires = "Windows Event Forwarding / WinRM or an agent exporting EVTX"


class FirewallAdapter(_UnconfiguredAdapter):
    kind = "FIREWALL"
    requires = "vendor API credentials or a syslog feed from the appliance"


_REGISTRY: dict[str, type[LogSourceAdapter]] = {
    a.kind: a
    for a in (FileAdapter, SimulatedAdapter, SyslogAdapter, HTTPAdapter,
              WindowsAdapter, FirewallAdapter)
}


def get_adapter(kind: str, config: dict | None = None) -> LogSourceAdapter:
    cls = _REGISTRY.get(kind, FileAdapter)
    return cls(config)


def adapter_catalog() -> list[dict]:
    out = []
    for kind, cls in _REGISTRY.items():
        inst = cls()
        out.append({
            "kind": kind,
            "mvp_supported": cls.mvp_supported,
            "requires": cls.requires,
            **inst.status(),
        })
    return out
