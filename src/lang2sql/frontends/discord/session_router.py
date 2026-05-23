"""session_router — interaction coordinates → :class:`Identity` (pure).

This module is deliberately free of ``discord`` imports so the mapping is unit-
testable without a live gateway. ``bot.py`` extracts the raw ids from a
discord.py interaction/message and hands them here; everything downstream
(session key, federation scope chain) follows from the :class:`Identity` these
functions build.

The three conversation shapes of v4.1 §4.1 map cleanly onto the optional id
fields of :class:`Identity`:

* **DM** — no ``guild_id``; the user is the unit of conversation.
* **channel @mention** — ``guild_id`` + ``channel_id``; a reply normally opens
  a thread, so the bot fills ``thread_id`` once that thread exists.
* **thread reply** — ``guild_id`` + ``channel_id`` + ``thread_id``; the thread
  is the narrowest conversation container and drives both the session key and
  the top of the federation scope chain.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.identity import Identity


@dataclass(frozen=True)
class InteractionContext:
    """Frontend-neutral snapshot of where an interaction happened.

    ``bot.py`` populates this from a discord.py object; the router turns it into
    an :class:`Identity`. Ids are strings (Discord snowflakes stringified) or
    ``None`` when the platform doesn't supply that level — a DM has no guild.
    """

    user_id: str
    guild_id: str | None = None
    channel_id: str | None = None
    thread_id: str | None = None
    is_admin: bool = False


def to_identity(ctx: InteractionContext) -> Identity:
    """Map an :class:`InteractionContext` to an :class:`Identity`.

    A pure 1:1 field copy — the semantics (session key, scope chain, default
    write scope) live on :class:`Identity` itself, so the router stays a thin,
    obvious translation layer with nothing to get subtly wrong.
    """
    return Identity(
        user_id=ctx.user_id,
        guild_id=ctx.guild_id,
        channel_id=ctx.channel_id,
        thread_id=ctx.thread_id,
        is_admin=ctx.is_admin,
    )


def is_dm(identity: Identity) -> bool:
    """True when this conversation is a direct message (no guild)."""
    return identity.guild_id is None


def is_thread(identity: Identity) -> bool:
    """True when the conversation is anchored to a thread."""
    return identity.thread_id is not None


def is_channel(identity: Identity) -> bool:
    """True for a guild channel conversation that isn't (yet) in a thread."""
    return identity.guild_id is not None and identity.thread_id is None
