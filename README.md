# Chronata

A record of the time you work that anyone can check, kept wherever you choose.

A timesheet is only worth something if the person reading it can trust it was written when it says. So every entry is sealed to the one before it, and an edit, deletion or backdated entry shows up. After each save, outside timestamp authorities (DigiCert and FreeTSA) sign a receipt for the latest entry, so the times don't rest on your own computer's clock.

Because the proof travels with the log, it can be saved anywhere: an Obsidian vault, a plain folder, a git host or a WebDAV server. Each copy checks out on its own with `chronata verify --folder <copy>`.

Mistakes are corrected or struck out, never deleted, because a visible correction is more credible than a clean record. The PC's on and off times are sealed alongside your shifts as corroboration, but never counted as work, because a PC being on is not work.
