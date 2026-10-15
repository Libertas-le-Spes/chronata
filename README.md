# Chronata

A record of the time you work that anyone can check, kept wherever you choose.

A timesheet is only worth something if the person reading it can trust it was written when it says. So every entry is sealed to the one before it, and an edit, deletion or backdated entry shows up. After each save, outside timestamp authorities (DigiCert and FreeTSA) sign a receipt for the latest entry, so the times don't rest on your own computer's clock.

Because the proof travels with the log, it can be saved anywhere: an Obsidian vault, a plain folder, a git host or a WebDAV server. Each copy checks out on its own with `chronata verify --folder <copy>`.

Mistakes are corrected or marked as mistakes, never deleted, because a visible correction is more credible than a clean record.

The PC's on and off times are sealed alongside your shifts as corroboration. A PC being on is not work, so it never counts by itself. But a click on a clock-in button proves no more than the PC coming on, so when you were working from the moment the PC came on, the day can start there, proven by the timestamp the PC-on record was sealed with seconds after boot rather than by when you remembered to click.

Overtime is owed by whoever it was worked for. So each client or project keeps its own hours, its overtime is measured against them alone, and what it pays or gives as time off is matched to that overtime and nobody else's. A late start is made up as soon as the time due by then has been worked, and only after that does overtime begin.

## Install

On Linux, run `./install.sh` from a clone. It needs Python 3.10 or newer and installs nothing else: it links the `chronata` command, adds Chronata to the applications menu and starts it in the background at every login. Then run `chronata setup`.
