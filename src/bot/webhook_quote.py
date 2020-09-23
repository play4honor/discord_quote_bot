import asyncio
import arrow
import re

from src.bot.utils import block_format, log_msg
from logzero import logger as log

# Helper function for quote: gets a WebHook
async def get_hook(ctx, bot, channel_id=None):
    # If no specific channel_id is specified, then we want the channel of
    # the ctx
    if not channel_id:
        channel = ctx.channel
    else:
        channel = ctx.guild.get_channel(channel_id)

    # Check for 'Manage WebHook' permission and return if missing permission
    if not channel.permissions_for(ctx.guild.me).manage_webhooks:
        return

    # Figure out the appropriate webhook
    hook = None
    webhooks = await channel.webhooks()
    if webhooks:
        # If there's an existing webhook, just use that.
        hook = webhooks[0]
        log.info(log_msg(['webhook_found', hook.name]))
    else:
        log.info(log_msg(['webhook_not_found']))

        # Otherwise, create a webhook.
        hook = await channel.create_webhook(name=bot.user.name)
        log.info(log_msg(['webhook_created', hook.name]))

    return(hook)

async def webhook_quote(ctx, bot, msg_, *reply: str):
    # This version depends on everything being well quoted (e.g., with jumpurls)
    # If the message that has been passed is assigned to the bot, then it is a
    # previous quote.
    quote = (msg_.author.name == bot.user.name)
    if not quote:
        if reply:
            output = (
                await _format_message(ctx, msg_, 'said') +
                f"**{ctx.message.author.name} responded:** {' '.join(reply)}"
            )
        if not reply:
            output = (
                await _format_message(ctx, msg_, 'said') +
                f"_via {ctx.message.author.name}_"
            )
    elif quote:

        if reply:
            output = (
                await _format_quote(ctx, msg_) +
                f"\n**{ctx.message.author.name} responded:** {' '.join(reply)}"
            )
        elif not reply:
            output = await _format_quote(ctx, msg_)
    else:
        pass

    return(output)

# Helper function for WebHook Quote (quoting simple messages)
async def _format_message(ctx, msg_, action):
    # Figure out the respective times
    current_time = arrow.get(ctx.message.created_at)
    original_message_time = arrow.get(msg_.created_at)
    relative_time = original_message_time.humanize(current_time)

    # Construct the channel jump_url
    channel_url = (
            f"https://discord.com/channels/"
        f"{msg_.guild.id}/{msg_.channel.id}"
    )

    output = (
        f"**{msg_.author.name} {action} " +
        f"[{relative_time}](<{msg_.jump_url}>) " +
        f"in [#{msg_.channel.name}](<{channel_url}>):**\n"+
        block_format(msg_.clean_content) + "\n"
    )

    return(output)

# Helper function for WebHook Quote (quoting quotes)
async def _format_quote(ctx, msg_):
    output = msg_.content

    # Identify the response in the quote without a jump url
    last_responder = re.search(r'\*\*(.*)\sresponded:\*\*\s', output)

    current_time = arrow.get(ctx.message.created_at)

    # Adjust old relative times
    # First, identify the old times
    old_relative_times = re.findall(
        r'(\*\*.*\[(.*)\]\(\<' +
        r'https:\/\/discordapp\.com\/channels\/[0-9]*\/[0-9]*\/([0-9]*)' +
        r'\>\))',
        output
    )

    # Now, re-humanize these times:
    if old_relative_times:
        log.info(log_msg(['old_relative_times', 'found']))
        for i in range(len(old_relative_times)):
            _temp = old_relative_times[i]

            # initialize the target (_old_speaker)
            # and the new content (_new_speaker)
            _old_speaker = _temp[0]
            _new_speaker = _temp[0]

            # get the associated old message
            _old_msg = await ctx.channel.fetch_message(_temp[2])
            log.info(log_msg(['retrieved_quote',
                          _old_msg.id,
                          ctx.message.channel.name,
                          _old_msg.author.name,
                          _old_msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                          ctx.message.author.name,
                          _old_msg.clean_content]))

            # rehumanize the time
            _old_msg_time = arrow.get(_old_msg.created_at)
            _new_relative_time = _old_msg_time.humanize(current_time)

            # format the replacement string
            _new_speaker = _new_speaker.replace(_temp[1], _new_relative_time)

            # update the output
            output = output.replace(_old_speaker, _new_speaker)


    # Edit in the new relative time for the last response
    quotebot_message_time = arrow.get(msg_.created_at)
    relative_time = quotebot_message_time.humanize(current_time)

    # Append the jump url into the quote
    if last_responder:
        _old_speaker = f"**{last_responder.group(1)} responded:**"
        _new_speaker = (
            f"**{last_responder.group(1)} responded " +
            f"[{relative_time}](<{msg_.jump_url}>):**"
        )

        output = output.replace(_old_speaker, _new_speaker)

    return(output)