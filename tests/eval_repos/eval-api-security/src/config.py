# Configuration for the internal notes API.
#
# NOTE: This is seed code for a harness eval scenario. The hardcoded
# secrets below are an intentional vulnerability the agent is expected
# to fix (move to environment variables, never commit real values).

SECRET_KEY = "super-secret-flask-key-do-not-share"
ADMIN_API_TOKEN = "sk-internal-9f8a7b6c5d4e3f2a1b0c"
DATABASE_PATH = "notes.db"
