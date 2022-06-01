# /usr/bin/env python3

# Standard libraries.
import asyncio
import sys

# External dependencies.
import textual.app
import textual.events


class App(textual.app.App):
    async def on_key(self, event: textual.events.Key) -> None:
        del event
        await self.shutdown()


async def async_main() -> int:
    await App().process_messages()
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
