# Windows Platform Note

This project is developed and run exclusively on Windows. All file and directory names, as well as path handling, must be compatible with Windows conventions:

- Use backslashes (`\\`) for paths in code, or use `os.path.join` for cross-version compatibility.
- Avoid reserved Windows filenames (e.g., `CON`, `PRN`, `AUX`, `NUL`, etc.).
- Be aware that Windows file systems are case-insensitive by default.
- Spaces in filenames are allowed, but consider using underscores or CamelCase for consistency.
- Always test file and directory creation on Windows to ensure compatibility.

This note should be reviewed by all contributors.
