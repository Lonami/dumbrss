# dumbrss
A bloat-free, web-based RSS reader  
![Screenshot](https://sr.ht/Y-XD.png)

## Features
- Collects only links
- Global, categorized and single feed views
- Minimal JavaScript usage

## To do
- Rewrite it in Rust™
- Have proper features

## Setup
dumbrss uses [Flask](http://flask.pocoo.org/). To install, simply set up your favority WSGI
server and create a virtualenv to run dumbrss into:  
```
virtualenv3 venv
source venv/bin/activate
pip install -r requirements.txt
```
Finally, initialize the database with `./dumbrss.py initdb`.  
You need to set up a cronjob to run `./dumbrss.py fetch` from within the virtualenv
as often as you want.  

