import os
import tempfile

os.environ["XDG_RUNTIME_DIR"] = tempfile.mkdtemp()

for variable, value in (("GIT_AUTHOR_NAME", "test"), ("GIT_AUTHOR_EMAIL", "test@example.com"),
                        ("GIT_COMMITTER_NAME", "test"), ("GIT_COMMITTER_EMAIL", "test@example.com")):
    os.environ.setdefault(variable, value)
