from config._loader import load, load_secrets

# Non-secret AI settings (provider, models...) are edited in the UI; keys come from `.env`.
globals().update(load("ai"))
globals().update(load_secrets())
