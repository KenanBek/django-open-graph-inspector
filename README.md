Django Open Graph Inspector
===========================

Parse given URL and get following information from web page:

1. HEAD tags

    1. title
    2. description meta
    3. keywords meta
    4. author meta

2. The Open Graph Protocol

    1. title
    2. type
    3. image (list)
    4. url
    5. description
    6. site_name

3. All page images (img tag)

Install and run:

    git clone https://github.com/KenanBek/django-open-graph-inspector.git
    cd django-open-graph-inspector
    virtualenv env
    .\env\Scripts\activate
    cd app
    python manage.py init
    python manage.py runserver
    
And the go to link: http://localhost:8000/blog/og/inspector/

Also, you can open Administration page and see history.

# License

Licensed under GNU GPL v3.0

