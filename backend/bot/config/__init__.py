"""Bot configuration, loaded from the per-run JSON snapshot written by the worker.

Each module keeps the old `from config.X import *` interface: it exposes every setting
of its section as a module global. Without a snapshot (tests, local runs) the
defaults from `app.settings_schema` are used.
"""
