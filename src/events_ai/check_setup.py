import os

from google import genai
from loguru import logger

from events_ai.agents.heygen_client import HeyGenClient


class SetupException(Exception):
    pass


def check():
    success = True
    logger.info("Checking setup...")
    success &= check_environ_variable_exists("GEMINI_API_KEY")
    success &= check_environ_variable_exists("HEYGEN_API_KEY")
    success &= check_environ_variable_exists("GMAIL_USER_APP_PASSWORD")

    models = check_gemini_api_connection()
    success &= len(models) > 0
    success &= check_gemini_api_model_exists("gemini-2.5-flash-lite", models)
    success &= check_gemini_api_model_exists("gemini-2.5-flash", models)
    success &= check_gemini_api_model_exists("gemini-2.5-flash-image", models)

    quota = check_heygen_api_connection()
    success &= quota is not None
    TAKES = 6
    CREDITS_PER_TAKE = 1  # Assumes a take is < 30 seconds
    success &= check_heygen_api_credits(quota, TAKES * CREDITS_PER_TAKE)

    if success:
        logger.info("All checks passed.")
    else:
        logger.error("Some checks failed!")
        raise SetupException()


def check_environ_variable_exists(variable: str) -> bool:
    if variable in os.environ:
        logger.info(f"Environment variable {variable} set.")
        return True
    else:
        logger.error(f"Environment variable not set: {variable}")
        return False


def check_gemini_api_connection() -> list[str]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    try:
        models = client.models.list()
        logger.info("Gemini connection succeeded.")
        return [model.name or "" for model in models]
    except genai.errors.ClientError as e:
        logger.error(f"Gemini API connection failed: {e}")
        return []


def check_gemini_api_model_exists(name: str, models: list[str]) -> bool:
    if f"models/{name}" in models:
        logger.info(f"Gemini API model {name} found.")
        return True
    else:
        logger.error(f"Required Gemini model not found: {name}")
        return False


def check_heygen_api_connection() -> dict | None:
    client = HeyGenClient(os.environ["HEYGEN_API_KEY"])

    quota = client.check_quota()
    quota_data = quota["data"]

    if quota_data is None:
        logger.error(f"Heygen API connection failed: {quota['error']}")
    else:
        logger.info(f"HeyGen connection succeeded: {quota_data}")

    return quota_data


def check_heygen_api_credits(quota, minimum_credits: int) -> bool:
    if quota is None:
        logger.error("HeyGen quota information not available!")
        return False

    credits = quota["remaining_quota"] / 60

    logger.info(f"HeyGen quota info: {quota}")

    if credits >= minimum_credits:
        logger.info(f"HeyGen has sufficient credits: {credits}")
    else:
        logger.error(f"HeyGen has insufficient credits: {credits}")

    return True
