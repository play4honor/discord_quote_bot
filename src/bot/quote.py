import asyncio
import re

from src.bot.utils import block_format, log_msg
from logzero import logger as log

async def bot_quote(ctx, bot, msg_, reply: str=False):
    # This is the old way to quote things, if you don't have the 'Manage
    # WebHooks' permission, but you have a bot user, then this is what will be
    # used.

    quote = False
    author = msg_.author.name
    message_time = msg_.created_at.strftime("%Y-%m-%d %H:%M:%S")

    # If previously quoted, find the original author
    if msg_.author.name == bot.user.name:
        quote = True

        # Run a regex search for the author name and if you can find it
        # re-attribute. If you can't find it, it'll just be the bot's name
        _author = re.search(r"^\*\*(.*)\[(.*)\]\ssaid:\*\*", msg_.clean_content)
        if _author:
            author = _author.group(1)
            log.info(log_msg(['found_original_author', msg_.id, author]))
            message_time = _author.group(2)
            log.info(log_msg(['found_original_timestamp', msg_.id, message_time]))

    clean_content = msg_.clean_content

    # Format output message, handling replies and quotes
    if not reply and not quote:
        log.info(log_msg(['formatting_quote', 'noreply|noquote']))
        # Simplest case, just quoting a non-quotebot message, with no reply
        output = (
            f"**{author} [{message_time}] said:** _via " +
            f"{ctx.message.author.name}_\n" +
            block_format(clean_content)
        )
    elif not reply and quote:
        log.info(log_msg(['formatting_quote', 'noreply|quote']))

        # Find the original quoter
        _quoter = re.search("__via.*?__", msg_.content)
        if _quoter:
            # Replace the original quoter with the new quoter
            output = msg_.content.replace(
                _quoter.group(0),
                f"__via {ctx.message.author.name}__"
            )
        else:
            # If the regex breaks, just forward the old message.
            output = msg_.content
    elif reply and quote:
        log.info(log_msg(['formatting_quote', 'reply|quote']))

        # Detect Last Response so we can hyperlink
        _last_response = re.search(
                r"\*\*[A-Za-z0-9]*\s(\[[A-Za-z0-9\s]*\])\sresponded",
                msg_.content
        )

        if _last_response:
            clean_content = clean_content.replace(
                    _last_response.group(1),
                    f"[{_last_response.group(1)}({msg_.jump_url})]"
            )

        # Reply to a quotebot quote with a reply
        output = (
            f"{clean_content}\n**{ctx.message.author.name} " +
            f"[{ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
            f"responded:** {reply}"
        )
    else:
        log.info(log_msg(['formatting_quote', 'reply|quote']))

        output = (
                f"**{author} [{msg_.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
                f"said:** \n" +
                block_format(clean_content) +
                "\n" +
                f"**{ctx.message.author.name} " +
                f"[{ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] " +
                f"responded:** {reply}"
        )

    log.info(log_msg(['formatted_quote', reply]))

    await ctx.channel.send(output)

    log.info(log_msg(['sent_message', 'quote', ctx.message.channel.name]))
