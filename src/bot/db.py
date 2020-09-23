import sqlite3
import boto3
import botocore
import os
from logzero import logger as log
from pathlib import Path

from src.bot.utils import log_msg

# --- Database functions
def db_load(bucket):
    """Checks if a local copy of the Sqlite3 database exist. If not,
    attempts to download a backup from S3. If there is no backup,
    then it initializes a new Sqlite3 database.

    Tries to create (if it doesn't already exist) the `pins` table.

    Returns the connection to the databse.

    Unless absolutely necessary, don't call this directly.
    Use `db_execute()` instead.
    """

    db_filename = os.environ['DISCORD_QUOTEBOT_DB_FILENAME']
    # Check if the database exists
    if not Path(f'./{db_filename}').exists() and bucket:
        # If missing, attempt to download backup file
        log.info(log_msg(['db_backup', 'download', 'attempt']))

        try:
            bucket.download_file(db_filename, db_filename)
        except botocore.exceptions.ClientError as e:
            log.error(log_msg(['db_backup', 'download', 'failed', e]))

        log.info(log_msg(['db_backup', 'download', 'successful']))

    if Path(f'./{db_filename}').exists():
        log.info(log_msg(['database_found']))
    else:
        log.info(log_msg(['creating_new_database']))

    conn = sqlite3.connect(f'./{db_filename}')
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pins (
        alias TEXT, msg_url TEXT, pin_user TEXT, pin_time TEXT
        )
        """
    )

    return(conn)

def db_execute(query):
    """Wrapper to ensure that any queries that are launched at the
    database are launched inside a database context (i.e., the connection
    is closed after the query is run).

    Returns all the results of the query.
    """
    # We define this helper function to make sure that the db is closed
    # after every query. If not, easy way to corrupt the db.
    with db_load() as conn:
        c = conn.cursor()
        c.execute(query)
        return(c.fetchall())

def db_backup():
    """When called, backs up the sqlite database to a pre-specified S3 bucket.
    """
    log.info(log_msg(['db_backup', 'upload', 'attempt']))

    db_filename = os.environ['DISCORD_QUOTEBOT_DB_FILENAME']
    bucket.upload_file(
        f'./{db_filename}',
        f'{db_filename}'
    )

    log.info(log_msg(['db_backup', 'upload', 'successful']))
