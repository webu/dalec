# Django Aggregator of a Lot of External Contents aka DALEC 🤖

Django Aggregator of a Lot of External Contents (DALEC) is a generic app to aggregate contents from various
external sources. Purposes are to manage (retrieve, clean, display…) those contents in a
generic way independent of the source.

It's designed to be customized / extended to fit your needs.

![Logo de DALEC](logo.png)

## Concepts

Contents are categorized via :

* `app`: the app which is requested to retrieve contents 
  (eg. `gitlab`)
* `content_type`: the type of contents we want to retrieve from this app 
  (eg. `issue`, `activity`, `commit`, `merge requests`…)
* `channel`: some apps can be requested to get a more or less filtered contents. 
  For exemple, in Gitlab, it's called "scope". You can retrieve issues from:
  * the whole site (`channel=None` and `channel_object=None` for us)
  * a specific group (`channel="group"` and `channel_object="<gitlab_group_id>"`)
  * a specific project (`channel="project"` and `channel_object="<gitlab_project_id>"`)
  * a specific author (`channel="author"` and `channel_object="<gitlab_user_id>"`)
  * a specific assignee (`channel="assignee"` and `channel_object="<gitlab_user_id>"`)
  * etc.
* `channel_object`: the ID (for the app requested) of the channel's related object

Before you ask: yes, some contents can be duplicated (eg. an issue from the "group" channel 
could be duplicated in the "project" channel). It's normal and **wanted**. Remember : the purpose
of this app is to retrieve and display the `last N contents of something`. If the issue we are 
talking about is in the `last N issues of project "cybermen"`, it does not mean it's also in 
`the last N issues of group "dr-who-best-friends"`. To manage different timelines for each channel,
and keep a KISS Model, we need those duplicates.


## Installation

If you are using Django older than 3.1, the JSONField is provided from 
[django-jsonfield-backport](https://pypi.org/project/django-jsonfield-backport/). 
For 3.1+, you **MUST** use a DB supporting the official
[django's `JSONField`](https://docs.djangoproject.com/fr/3.1/ref/models/fields/#jsonfield).

You **SHOULD NOT** install this app but you **SHOULD** install one (or more) of it's children 
(see [external sources supported](#External-sources-supported)). eg:

`pip install dalec-gitlab dalec-nextcloud`

Then, add `dalec`, `dalec_prime` and dalec's children to `INSTALLED_APPS` in `settings.py`:

```python
# settings.py

INSTALLED_APPS = [
    # …
    "dalec",
    "dalec_prime",  # if you want to use your own Content model, does not add it
    "dalec_gitlab",
    "dalec_nextcloud",
    # …
]
```

## Usage

Add `dalec/main.js` inside templates where you need to use the dalec. 

Each dalec's child app will probably need some specific configuration to retrieve external contents 
(eg: token or login/password). Please refer to this dalec's child app configuration section first.

Now your dalec's child app is configured, you can display it's X last contents somewhere in a 
template by using the templatag `dalec`:

```django
{% load dalec %}

{% dalec app content_type [channel=None] [channel_object=None] [template=None] %}

real exemples:

Retrieves last gitlab issues for a specific user:
{% dalec "gitlab" "issue" channel="user" channel_object="doctor-who" %}

Retrieves recent gitlab activity for a group:
{% dalec "gitlab" "activity" channel="group" channel_object='companions' %}

Retrieves recent gitlab activity for a project:
{% dalec "gitlab" "activity" channel="project" channel_object='tardis' %}

Retrieves recent gitlab issues for a project:
{% dalec "gitlab" "issue" channel="project" channel_object='tardis' %}
```

### dalec_exemple

An exemple app is packaged to get a working exemple which does not require any extra configuration.

* add `dalec_exemple`, `dalec_prime` and `dalec` to `INSTALLED_APPS`
* run migrations
* include dalec.urls inside your project's urls
* add `dalec/main.js` inside your base.html or inside the template where you want to display the exemple
* add those fragments of code inside the template where you want to display the exemple:

```django
{% load dalec %}
<h1>Last quarters (very usefull, isn't it ?)</h1>
{% dalec "exemple" "quarter" %}

<h1>Last updated establishments of french national education</h1>
{% dalec "exemple" "french_educ" %}

<h1>Last updated establishments of french national education depending of the Academy of Grenoble</h1>
{% dalec "exemple" "french_educ" channel="academy" channel_object="Grenoble" %}
```


## Configuration

This app have general settings which can be erased for all of it's children and sometimes by 
content type.

* General setting format : `DALEC_SOMETHING`
* overided child version (it's app name, like gitlab for exemple): `DALEC_GITLAB_SOMETHING`
* overided content type version (gitlab's issues for exemple): `DALEC_GITLAB_ISSUE_SOMETHING`

### DALEC_NB_CONTENTS_KEPT

* * *default*: `10`
* per child app setting: yes
* per child app's content type setting: yes

Set the number of contents to keep by type. Oldest will be purged to keep only the last X contents 
of each channel and type.
`0` means "no limit".

### DALEC_AJAX_REFRESH

* *default*: `True`
* per child app setting: yes
* per child app's content type setting: yes

If `True`, when an user display a channel contents, an ajax requests is sent to refresh content. 
It's usefull if you do not want to use a cron task and/or need to get always the last contents.

### DALEC_TTL

* *default*: `900`
* per child app setting: yes
* per child app's content type setting: yes

Number of seconds before an ajax request sends a new query to the instance providing instance.

### DALEC_CONTENT_MODEL

* *default*: `"dalec_prime.Content"`
* per child app setting: no
* per child app's content type setting: no

Concrete model to use to store contents. If you do not want to use the default one,
you should not add `dalec.prime` in `INSTALLED_APPS` to avoid to load a useless model
and have an empty table in your data base.

### DALEC_FETCH_HISTORY_MODEL

* *default*: `"dalec_prime.FetchHistory"`
* per child app setting: no
* per child app's content type setting: no

Same as `DALEC_CONTENT_MODEL` but for the `FetchHistory` model.

### DALEC_CSS_FRAMEWORK

* *default*: `None`
* per child app setting: yes
* per child app's content type setting: no

Name of the (S)CSS framework you use on your website. It changes the default templates used to 
display contents. Templates are priorized in this order (`css_framework` versions only used if 
you set a value to `DALEC_CSS_FRAMEWORK`):

* `dalec/%(app)s/%(tpl)s-list.html`: only if you use a specific template, see templatags `dalec`
* `dalec/%(app)s/%(css_framework)s/%(content_type)s-%(channel)s-list.html`
* `dalec/%(app)s/%(content_type)s-%(channel)s-list.html`
* `dalec/%(app)s/%(css_framework)s/%(content_type)s-list.html`
* `dalec/%(app)s/%(content_type)s-list.html`
* `dalec/%(app)s/%(css_framework)s/list.html`
* `dalec/%(app)s/list.html`
* `dalec/default/%(css_framework)s/list.html`
* `dalec/default/list.html` 

Supported valued are:

* `None`: only dalec classes and data will be added. HTML elements are sementics. Templates are the default ones.

Future supported values could be:

* materialize
* bulma
* bootstrap
* semantic-ui

## Customization

### Styles

No styles are included inside dalec who must remains pure with no feelings. 
But some SCSS framework may be supported. Please refer to `DALEC_CSS_FRAMEWORK` setting.

### Templates

You should always inherit from the default templates and use defined blocks to customise it.

#### List

Each app can have it's own "list" template but if it doesn't, a default one will be used. 
In priority order:

* `dalec/<childappname>/<contenttype>-<channel>-list.html`
* `dalec/<childappname>/<contenttype>-list.html`
* `dalec/<childappname>/list.html`
* `dalec/default/list.html`

#### Item

Each content types can have it's own template. Those filenames will be tried:

* `dalec/<childappname>/<contenttype>-<channel>-item.html`
* `dalec/<childappname>/<contenttype>-item.html`
* `dalec/<childappname>/item.html`
* `dalec/default/item.html`

For "gitlab" app, "issue" content type and "project" channel we will try :

* `dalec/gitlab/issue-project-item.html`
* `dalec/gitlab/issue-item.html`
* `dalec/gitlab/item.html`
* `dalec/default/item.html`

### Models

Model used to store contents is defined by the setting `DALEC_CONTENT_MODEL` which has the
default value `"dalec_prime.Content"`.
If you want to use your own model, in your `settings.py`:

* remove `dalec.prime` from `INSTALLED_APPS`
* set the setting `DALEC_CONTENT_MODEL` with `<yourapp>.<yourModel>`

## External sources supported

* 🦝 [dalec-gitlab](https://dev.webu.coop/w/i/dalec-gitlab/):
  get issues and activities from a gitlab instance
* ☁ [dalec-nextcloud](https://dev.webu.coop/w/i/dalec-nextcloud/):
  get events and activities from a nextcloud instance
* 🗣 [dalec-discourse](https://dev.webu.coop/w/i/dalec-discourse/):
  get last messages or topics from a discourse instance
* 🔗 [dalec-openproject](https://dev.webu.coop/w/i/dalec-openproject/):
  get tasks from an openproject instance

## External sources which could be nice to support

* 🌍 dalec-mediawiki: get last pages from a mediawiki instance
* 📅 dalec-caldav: get events and tasks from a caldav instance (eg: nextcloud agenda)
* 📂 dalec-webdav: get lastmodified files from a webdav instance (eg: nextcloud files)
* 📰 dalec-feedparser: get contents from atom and rss feeds
* 📫 dalec-imap: get emails from imap instance
* 🐥 dalec-mastodon: get toots from a mastodon instance
* 📺 dalec-peertube: get last uploaded videos from a peertube instance
* 🌵 dalec-git: get last commits from a git repository
* 🐱 dalec-github: get issues, pull-requests, activity from github
* 🐦 dalec-twitter: get tweets from twitter
* 🎞 dalec-youtube: get last uploaded videos from youtube
* 🎥 dalec-imdb: get last movies from imdb

## Manage a new external source

If you want to add a specific external source, you just have to extends `dalec.proxy.Proxy`
and override it's `_fetch` method.

To create a dalec child (a proper way), you should create a new django app with the name pattern
`dalec_<yourExternalSourceUname>`

## NAQ (Never Asked Questions)

### Why this logo is so ugly ?

Because I'm a developper

### Aren't you afraid to be accused of blasphemy by the Daleks ?

A Dalek which have a concept of Blasphemy can not be a sane Dalek! 
https://youtu.be/6ThpkjDgdvY?t=162

### What's the dalec origin ?

The Dale**k**s are a fictional extraterrestrial race of mutants principally portrayed in the 
British science fiction television programme Doctor Who. Name (and logo) of this django app is 
directly related to them.

This project was made possible thanks to the 
[Open Space Maker Federation](https://www.federation-openspacemakers.com) whose goal is to open 
up the world of space infrastructure to as many people as possible.  
They need boards to aggregate contents from differents sources (gitlab, discourse…). 
We ([Webu](https://www.webu.coop))didn't find any applications which fit our needs, 
so we create a new one and released it under the MIT licence.
