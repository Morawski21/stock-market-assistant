import asyncio

from dotenv import load_dotenv

from app.chat import StockMarketChat
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


async def main() -> None:
    logger.info("Stock Market Assistant — type 'quit' to exit\n")

    async with StockMarketChat() as chat:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                logger.info("\nGoodbye.")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                logger.info("Goodbye.")
                break

            response = await chat.send(user_input)
            logger.info("Assistant: %s\n", response)


if __name__ == "__main__":
    asyncio.run(main())
