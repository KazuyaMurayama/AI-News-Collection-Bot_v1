# AI News - {{ date }}

{% for story in stories %}
## Story {{ story.id }}: {{ story.title }}

> Source: [{{ story.source }}]({{ story.url }})

{{ story.body }}

{% endfor %}
## Today's Insight

{{ insight }}
