# /usr/bin/env python3

# Standard libraries.
import asyncio
import pathlib
import sys
import typing

# External dependencies.
import rich.console
import rich.text
import textual.app
import textual.events
import textual.widget
import textual.widgets

_T = typing.TypeVar("_T")


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


class TreeControl(textual.widgets.TreeControl[_T]):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.show_cursor = True

    def watch_show_cursor(self, value: bool) -> None:
        if value:
            self.hover_node = self.cursor
        super().watch_show_cursor(value)

    def watch_cursor_line(self, value: int) -> None:
        if self.show_cursor:
            self.hover_node = self.cursor
        super().watch_cursor_line(value)

    async def handle_tree_click(self, message: textual.widgets.TreeClick[_T]) -> None:
        node = message.node
        if node.children:
            await node.toggle()

    async def remove(self, node_id: textual.widgets.NodeID) -> None:
        """
        :raise KeyError: If there are no nodes with given ID.
        """
        assert node_id != self.root.id, "Cannot remove root node."
        node = self.nodes.pop(node_id)
        parent = node.parent
        assert parent is not None
        parent.children.remove(node)
        parent.tree.children.remove(node.tree)


class DirectoryTree(TreeControl[pathlib.Path]):
    def __init__(
        self, *args: typing.Any, directory: pathlib.Path, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, label=directory.name, data=directory, **kwargs)

    async def on_mount(self) -> None:
        message = textual.widgets.TreeClick[pathlib.Path](sender=self, node=self.root)
        await self.handle_tree_click(message=message)

    async def handle_tree_click(
        self, message: textual.widgets.TreeClick[pathlib.Path]
    ) -> None:
        node = message.node
        if not node.children:
            for path in node.data.iterdir():
                await node.add(label=path.name, data=path)
        await super().handle_tree_click(message)


class App(textual.app.App):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._file_tree = DirectoryTree(directory=pathlib.Path.home().resolve())
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
        file_tree = self._file_tree
        await self.view.dock(self._message_area, edge="bottom", size=1)
        await self.view.dock(file_tree, edge="top")
        await file_tree.focus()


async def async_main() -> int:
    await App().process_messages()
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
