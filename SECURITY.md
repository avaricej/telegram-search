# Security

Never attach Telegram codes, API hashes, passwords, session strings or the
results database to an issue. If a session is exposed, terminate it in the
official Telegram client under Settings / Devices.

The app uses an in-memory Telethon session and stores its serialized credential
with the OS keyring. It does not use a plaintext .session file. On Windows this
is Windows Credential Manager. The OS account and its credential store must be
trusted. Local malware running as the user is outside this protection boundary.

Message matches are stored as plaintext SQLite in the user's local app-data
directory, and exported CSV files contain message text. Uninstalling binaries
does not revoke Telegram sessions or erase user data. Use Logout and Delete
results before removal. No analytics or application server is included.

Only one app process may run per data directory. Telegram client credentials
must never be committed. The application does not send messages or join chats.
