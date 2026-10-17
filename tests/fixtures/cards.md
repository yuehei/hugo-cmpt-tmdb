---
title: 影视卡片示例
date: 2026-10-17
draft: false
---

采用 TMDB 风格：桌面左图右文，手机上图下文。个人评分为演示数据。

[《偷天父子兵》两行信息布局示例](/masterplan/)

## 电影 · 搏击俱乐部

{{< tmdb type="movie" id="550" >}}

## 电视剧 · 绝命毒师

{{< tmdb type="tv" id="1396" >}}

资料、简介、演职员及海报在构建时通过 TMDB API 获取并缓存；个人评分为演示数据。

## 精简信息

{{< tmdb type="movie" id="550" show_summary=false show_rating=false show_personal_rating=false new_tab=false >}}

## 另一部电影 · 星球大战

此卡片同样从 API 获取真实资料。

{{< tmdb type="movie" id="11" >}}
