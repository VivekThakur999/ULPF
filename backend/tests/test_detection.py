import pytest

from app.services.detection.detector import detector

CASES = [
    ("Sep  2 09:02:11 db-02 sshd[4412]: Failed password for admin from 192.168.1.50 port 44210 ssh2",
     "LINUX_AUTH"),
    ('10.20.0.14 - jdoe [02/Sep/2025:08:15:04 +0000] "GET /a HTTP/1.1" 200 18244 "-" "Mozilla/5.0"',
     "APACHE_COMBINED"),
    ('10.20.0.14 - - [02/Sep/2025:08:16:10 +0000] "GET /x HTTP/2.0" 200 91233 "r" "UA" "-" rt=0.004 uct="0.0" urt="0.003"',
     "NGINX_ACCESS"),
    ("Sep  2 09:01:55 fw kernel: [488213.114] IPTABLES DROP IN=eth0 SRC=192.168.1.50 DST=10.20.0.20 PROTO=TCP SPT=44208 DPT=22 SYN",
     "FIREWALL"),
    ('date=2025-09-02 time=09:01:50 devname=fw-01 action=deny srcip=192.168.1.50 dstip=10.20.0.20 dstport=22 proto=6',
     "FIREWALL"),
    ('{"ts":"2025-09-02T09:02:12Z","level":"warning","event":"login_failed","user":"admin"}',
     "JSON"),
    ("<34>Sep  2 07:00:00 gw-01 systemd[1]: Started Daily apt download activities.",
     "SYSLOG"),
]


@pytest.mark.parametrize("line,expected", CASES)
def test_format_detection(line, expected):
    res = detector.detect(line)
    assert res.format == expected, f"{line!r} -> {res.format} ({res.confidence}) cand={res.candidates}"
    assert res.confidence > 0.4


def test_unknown_is_generic_text():
    res = detector.detect("this is just a sentence with no structure whatsoever today")
    assert res.format in ("GENERIC_TEXT", "UNKNOWN")


def test_empty_input():
    res = detector.detect("   \n  ")
    assert res.format == "UNKNOWN"
    assert res.confidence == 0.0
