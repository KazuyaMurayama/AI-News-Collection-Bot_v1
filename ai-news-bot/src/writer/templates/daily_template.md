# AI ニュース - {{ date }}

{% for story in stories %}
## 記事 {{ story.id }}: {{ story.title }}

> 出典: [{{ story.source }}]({{ story.url }})

{{ story.body }}

{% endfor %}
## 本日のインサイト

{{ insight }}
