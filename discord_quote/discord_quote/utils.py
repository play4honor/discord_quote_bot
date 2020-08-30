import re

def log_msg(data):
    """
    Accepts a list of data elements, removes the  u'\u241e'character
    from each element, and then joins the elements using u'\u241e'.

    Messages should be constructed in the format:

        {message_type}\u241e{data}

    where {data} should be a \u241e delimited row.
    """
    tmp = [str(d).replace(u'\u241e', ' ') for d in data]
    return u'\u241e'.join(tmp)

# Format a message as a block quotes.
def block_format(message):

    # Find new line positions
    insert_idx = [pos for pos, char in enumerate(message) if char == "\n"]
    insert_idx.insert(0, -1)

    # Insert "> " for block quote formatting
    for offset, i in enumerate(insert_idx):

        message = (message[:i + (2 * offset) + 1] + 
                  "> " + 
                  message[i + (2 * offset) + 1:])

    return(message)

def parse_msg_url(url):
    """
    Parses out the message id from a discord mesasge url
    """
    
    url_template = re.compile(
        r"https:\/\/discord[a-z]*\.com\/channels\/([0-9]*)\/([0-9]*)\/([0-9]*)"
    )

    server, channel, message = re.search(url_template, url).groups()

    return server, channel, message
