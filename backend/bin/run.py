import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chronata.entrypoints.cli.main import main

sys.exit(main())
