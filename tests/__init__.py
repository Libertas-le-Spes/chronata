import os

for variable, value in (("GIT_AUTHOR_NAME", "test"), ("GIT_AUTHOR_EMAIL", "test@example.com"),
                        ("GIT_COMMITTER_NAME", "test"), ("GIT_COMMITTER_EMAIL", "test@example.com")):
    os.environ.setdefault(variable, value)
