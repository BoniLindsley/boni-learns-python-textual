# /usr/bin/env python3

# Standard libraries.
import asyncio
import sys
import typing

# External dependencies.
import rich.console
import rich.text
import textual.app
import textual.events
import textual.widget


async def shutdown_app(app: textual.app.App) -> None:
    # Library method is not typed.
    await app.shutdown()  # type: ignore[no-untyped-call]


class MessageArea(textual.widget.Widget):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._text = rich.text.Text()

    def render(self) -> rich.console.RenderableType:
        return self._text

    async def on_focus(self, event: textual.events.Focus) -> None:
        del event
        self._text.set_length(0)
        self.refresh()

    async def on_key(self, event: textual.events.Key) -> None:
        key = event.key
        if key == "enter":
            await self.app.set_focus(None)
            await self.process_command()
            event.stop()
        elif key.isprintable():
            self._text.append(key)
            self.refresh()
            event.stop()

    async def process_command(self) -> None:
        if self._text.plain == ":q":
            await shutdown_app(self.app)


class App(textual.app.App):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._message_area = MessageArea()

    async def on_key(self, event: textual.events.Key) -> None:
        if event.key == ":":
            message_area = self._message_area
            await message_area.focus()
            await message_area.forward_event(event)
        if event.key == "q":
            await shutdown_app(self)
            event.stop()

    async def on_mount(self) -> None:
        await self.view.dock(self._message_area, edge="bottom", size=1)


async def async_main() -> int:
    await App().process_messages()
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
