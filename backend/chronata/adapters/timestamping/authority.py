from dataclasses import dataclass
from pathlib import Path

ANCHORS = Path(__file__).parent / "authorities"


@dataclass(frozen=True)
class Authority:
    id: str
    name: str
    url: str
    anchor: Path


AUTHORITIES = (
    Authority("digicert", "DigiCert", "http://timestamp.digicert.com", ANCHORS / "digicert.pem"),
    Authority("freetsa", "FreeTSA", "https://freetsa.org/tsr", ANCHORS / "freetsa.pem"),
)
