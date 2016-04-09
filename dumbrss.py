#!/usr/bin/env python3

import os
import time
import urllib.error as urlerror
import urllib.parse as urlparse
import urllib.request as urlrequest

import flask
import flask.ext.script as script
import flask.ext.sqlalchemy as f_sqlalchemy
import flask_wtf

from bs4 import BeautifulSoup
import feedparser
import sqlalchemy
import wtforms

app = flask.Flask(__name__)

# Default config
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(app.root_path, "dumbrss.db")
))
if os.getenv("DRSS_CONFIG") is None:
    os.environ["DRSS_CONFIG"] = os.path.join(app.root_path, "config.py")
app.config.from_envvar("DRSS_CONFIG", silent = True)

if app.config["SECRET_KEY"] is None:
    f = open(os.environ["DRSS_CONFIG"], "a")
    app.config["SECRET_KEY"] = os.urandom(32)
    f.write("SECRET_KEY = " + str(app.config["SECRET_KEY"]) + "\n")
    f.close()

db = f_sqlalchemy.SQLAlchemy(app)
manager = script.Manager(app)

# Set the timezone to UTC for consistent time stamps
os.environ["TZ"] = "UTC"
time.tzset()

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    feed_id = db.Column(db.Integer, db.ForeignKey("feed.id"))
    feed = db.relationship("Feed", backref = db.backref("entries", lazy = "dynamic"))
    link = db.Column(db.Text)
    title = db.Column(db.Text)
    author = db.Column(db.Text)
    date = db.Column(db.Integer)
    starred = db.Column(db.Integer)

    def __init__(self, feed, link, title, author, date):
        self.feed = feed
        self.link = link
        self.title = title
        self.author = author
        self.date = date
        self.starred = 0

    def __repr__(self):
        return "<Entry {0} ({1})>".format(self.id, self.title)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    folder_id = db.Column(db.Integer, db.ForeignKey("folder.id"))
    folder = db.relationship("Folder", backref = db.backref("feeds", lazy = "dynamic"))
    name = db.Column(db.Text)
    icon = db.Column(db.Text)
    link = db.Column(db.Text)
    url = db.Column(db.Text)

    def __init__(self, folder, name, icon, link, url):
        self.folder = folder
        self.name = name
        self.icon = icon
        self.link = link
        self.url = url

    def __repr__(self):
        return "<Feed {0} ({1})>".format(self.id, self.name)

    def fetch(self, commit = True):
        app.logger.info("Fetching " + str(self))
        d = feedparser.parse(self.url)

        for entry in d.entries:
            if self.entries.filter_by(link = entry.link).count() == 0:
                if not(hasattr(entry, "author")):
                    entry.author = None
                if hasattr(entry, "published_parsed"):
                    date = int(time.mktime(entry.published_parsed))
                elif hasattr(entry, "updated_parsed"):
                    date = int(time.mktime(entry.updated_parsed))
                else:
                    date = int(time.time())
                dbentry = Entry(self, entry.link, entry.title, entry.author, date)
                db.session.add(dbentry)

        if commit:
            db.session.commit()

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.Text)

    def __init__(self, name):
        self.name = name

    def __repr__():
        return "<Folder {0} ({1})>".format(self.id, self.name)

class AddFeedForm(flask_wtf.Form):
    import wtforms.validators as v
    url = wtforms.StringField("URL",
            validators = [ v.URL(message = "Please enter a valid URL") ])

def redirect_is_local(url):
    url = urlparse.urlparse(urlparse.urljoin(flask.request.host_url, url))
    localhost = urlparse.urlparse(flask.request.host_url)
    return url.scheme in ("http", "https") and url.netloc == localhost.netloc

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flask.flash(error, "danger")

def urlopen_mozilla(url):
    return urlrequest.urlopen(urlrequest.Request(url, headers = { "User-Agent": "Mozilla/5.0" } ))

@app.route("/")
@app.route("/feed/<int:feed_id>")
@app.route("/folder/<int:folder_id>")
@app.route("/starred", defaults = { "starred": True })
def feedview(folder_id = None, feed_id = None, starred = False):
    a = flask.request.args.get("a")
    if a == "setstarred":
        entry = Entry.query.get_or_404(flask.request.args.get("id") or 0)
        try:
            f = int(flask.request.args.get("f"))
        except ValueError:
            flask.abort(401)
        if not(f in [0, 1]):
            flask.abort(400)
        entry.starred = f
        db.session.commit()
        return ""

    entries = Entry.query.order_by(Entry.date.desc())

    if feed_id:
        feed = Feed.query.get_or_404(feed_id)
        title = feed.name
        entries = entries.filter_by(feed_id = feed_id)

    elif folder_id:
        folder = Folder.query.get_or_404(folder_id)
        title = folder.name
        entries = entries.join("feed").filter_by(folder_id = folder_id)

    elif starred:
        title = "Starred"
        entries = entries.filter_by(starred = 1)

    else:
        title = "Home"

    entries = entries.join("feed")

    try:
        page = int(flask.request.args.get("p") or 1)
    except ValueError:
        page = 1
    entries = entries.paginate(page, 30)

    addfeedform = AddFeedForm()

    return flask.render_template("feedview.html", entries = entries, title = title,
            folder_id = folder_id, feed_id = feed_id, starred = starred,
            addfeedform = addfeedform, feeds = Feed.query, folders = Folder.query)

def fetch_feeds():
    for feed in Feed.query.yield_per(1000):
        feed.fetch(commit = False)
    db.session.commit()

def fetch_feed(id):
    f = Feed.query.filter_by(id = id).first().fetch()

@app.route("/addfeed", methods = [ "POST" ])
def add_feed():
    form = AddFeedForm()
    if form.validate_on_submit():
        url = form.url.data
        print(url)
        f = feedparser.parse(url)
        if hasattr(f, "bozo_exception"):
            flask.flash("This is not a valid feed", "danger")
            return flask.redirect("/")
        if Feed.query.filter_by(url = url).count():
            flask.flash("This feed already exists", "danger")
            return flask.redirect("/")
        page = BeautifulSoup(urlopen_mozilla(f.feed.link))
        icon = page.find("link", rel = "shortcut icon")
        if icon is not None:
            icon = urlparse.urljoin(f.feed.link, icon["href"])
        else:
            icon = urlparse.urljoin(f.feed.link, "/favicon.ico")
            try:
                urlopen_mozilla(icon)
            except urlerror.HTTPError:
                icon = None
        newfeed = Feed(None, f.feed.title, icon, f.feed.link, url)
        db.session.add(newfeed)
        db.session.commit()
        newfeed.fetch()
        flask.flash("Feed added!", "success")
        return flask.redirect(flask.url_for("feedview", feed_id = newfeed.id, starred = False))
    flash_errors(form)
    return flask.redirect("/")

@manager.option("-f", "--feed", dest = "id", default = None)
def fetch(id):
    "Fetch feed updates"
    if id is None:
        fetch_feeds()
    else:
        try:
            id = int(id)
        except ValueError:
            print("Feed ID must be an integer")
            return

        try:
            fetch_feed(id)
        except AttributeError:
            print("No feed with ID", id)

@manager.command
def initdb():
    "Initialize the database"
    db.create_all()

if __name__ == "__main__":
    manager.run()

