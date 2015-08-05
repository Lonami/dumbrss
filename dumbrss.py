#!/usr/bin/env python3

import os
from flask import Flask, g
import sqlite3
from time import ctime, tzset, mktime
import feedparser
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
manager = Manager(app)

# Default config
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, "dumbrss.db")
))
if os.getenv("DRSS_CONFIG") == None:
    os.environ["DRSS_CONFIG"] = os.path.join(app.root_path, "config.py")
app.config.from_envvar("DRSS_CONFIG", silent = True)

# Set the timezone to UTC for consistent time stamps
os.environ["TZ"] = "UTC"
tzset()

def connect_db(autocommit = False):
    if not(autocommit):
        db = sqlite3.connect(app.config["DATABASE"])
    else:
        db = sqlite3.connect(app.config["DATABASE"], isolation_level = None)
    db.row_factory = sqlite3.Row
    return db

def get_db(autocommit = False):
    if not(hasattr(g, "sqlite_db")):
        g.sqlite_db = connect_db(autocommit)
    return g.sqlite_db

@app.teardown_appcontext
def close_db_connection(exception):
    if hasattr(g, "sqlite_db"):
        g.sqlite_db.close()

@app.route("/")
def root():
    db = get_db()
    cur = db.cursor()
    cur.execute("select link, title, author, date, feed_id from entries order by date desc")
    asdf = cur.fetchall()
    hjkl = ""
    for stuff in asdf:
        cur.execute("select name from feeds where id = " + str(stuff["feed_id"]))
        name = cur.fetchone()["name"]
        hjkl += name + ": " + "<a href=\"" + stuff["link"] + "\">" + stuff["title"] + "</a> by " + stuff["author"] + " on " + ctime(stuff["date"]) + "<br />"
    return hjkl

@app.route("/fetch")
def fetch_feeds():
    db = get_db(autocommit = True)
    cur = db.cursor()
    cur.execute("select id, url, name from feeds")

    while 1:
        row = cur.fetchone()
        if row == None:
            break

        app.logger.info("Fetching feed " + row["name"] + " (" + row["url"] + ")")
        d = feedparser.parse(row["url"])

        for entry in d.entries:
            altcur = db.cursor()
            altcur.execute("select rowid from entries where link = ? and feed_id = ?",
                    [ entry.link, row["id"] ])

            if altcur.fetchone() == None:
                try:
                    author = entry.author
                except AttributeError:
                    author = "&lt;none&gt;"
                date = int(mktime(entry.published_parsed))

                db.execute("insert into entries"
                        "(feed_id, title, link, author, summary, date, read, starred)"
                        "values (?, ?, ?, ?, ?, ?, ?, ?)", [
                            row["id"],
                            entry.title,
                            entry.link,
                            author,
                            entry.summary,
                            date,
                            0,
                            0
                        ])
    return ""

@manager.command
def fetch():
    "Fetch feed updates"
    fetch_feeds()

if __name__ == "__main__":
    manager.run()

