import yaml

with open("settings.yaml", "r") as file:
    config = yaml.safe_load(file)

    # Get settings
    BOT_TOKEN = config.get("BOT_TOKEN")
    API_ID = config.get("API_ID")
    API_HASH = config.get("API_HASH")
    BOT_USERNAME = config.get("BOT_USERNAME")
    BOT_NAME = config.get("BOT_NAME")
    ADMIN_IDS = config.get("ADMIN_IDS")
    FEEDBACK_CHAT_ID = config.get("FEEDBACK_CHAT_ID")
    GEMINI_API_KEY = config.get("GEMINI_API_KEY")
    GEMINI_MODEL = config.get("GEMINI_MODEL")
    HUGGINGFACE_TOKEN = config.get("HUGGINGFACE_TOKEN")
    REDDIT_CLIENT_ID = config.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = config.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = config.get("REDDIT_USER_AGENT")
    HADITH_API_BASE = config.get("HADITH_API_BASE", "https://hadith-searcher-dorar-api-amx.vercel.app")

    DEBUG = config.get("DEBUG")
    ENABLE_GEMINI_COMMAND = config.get("ENABLE_GEMINI_COMMAND")
    ENABLE_IMAGINE_COMMAND = config.get("ENABLE_IMAGINE_COMMAND")
    ENABLE_MEME_COMMAND = config.get("ENABLE_MEME_COMMAND")
    ENABLE_TRIVIA_EVENTS = config.get("ENABLE_TRIVIA_EVENTS")