# 示例资料与图片来源

核对日期：2026-10-17。本页记录 tests/fixtures 中离线测试快照的来源；当前示例站在构建时调用真实 API，实际内容可能随 TMDB 更新。

- 电影：[偷天父子兵](https://www.themoviedb.org/movie/1561726-masterplan)，TMDB ID 1561726。页面用户评分 70%，显示为 7.0；页面显示 R、2026-10-16 (FR)、动作／惊悚、1h 49m。分级与地区为网页展示快照，API 实际地区记录可能不同。
- 电影：[搏击俱乐部](https://www.themoviedb.org/movie/550-fight-club)，TMDB ID 550。页面用户评分 84%，按十分制显示为 8.4。
- 电视剧：[绝命毒师](https://www.themoviedb.org/tv/1396-breaking-bad)，TMDB ID 1396。页面用户评分 90%，按十分制显示为 9.0。首播日期另参考 [官方 API 示例](https://developer.themoviedb.org/reference/search-tv)。
- 简介为依据条目剧情重新撰写的简短概述；评分是核对当天的页面快照，不代表实时分数或 API 未取整值。
- 海报来自 TMDB 图片服务，标志来自 TMDB 官方网页所使用的 logo。图片及标志不适用组件 MIT 许可；权利属于相应权利人，使用须遵循 TMDB 条款。
- 个人评分为布局演示数据，不代表作者实际评分。
- 下面的 SHA-256 对应下载后的原始文件；未进行裁切或图像修改，CSS 使用 contain 完整显示海报。

- `exampleSite/static/images/tmdb/fight-club.jpg`
  - 来源：https://image.tmdb.org/t/p/w780/qkrH7rjYKU4KOwwIl6wF6H3ISvm.jpg
  - SHA-256：`033eb39a1aed77b6311ed48853789118f0680cd52c6acf523867184bc9108abc`
- `exampleSite/static/images/tmdb/breaking-bad.jpg`
  - 来源：https://image.tmdb.org/t/p/w780/rqliuvX7NdknSHu5qaSDfESplQi.jpg
  - SHA-256：`5db8a44c9ccfa4a05eb2ac0b2debce2d26d7a7e5775a8bc0118858458a09c030`
- `static/images/hugo-cmpt-tmdb/logo.svg`
  - 来源：https://www.themoviedb.org/assets/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg
  - SHA-256：`8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c`

- `exampleSite/static/images/tmdb/masterplan.jpg`
  - 来源：https://image.tmdb.org/t/p/w780/AqZnhdnnoo4YQiFXm4LmwoMaWWw.jpg
  - SHA-256：`52c06b0b1e0a2091a4e2fc08dc8f9a60c64e162226780bf1d1916316c7533f2f`

- 《搏击俱乐部》编剧 Jim Uhls 另核对 [BFI 演职员资料](https://www.bfi.org.uk/film/204bf5de-a8d2-5341-8d57-66963d757279/fight-club)。人物 ID 缺省时，示例人名链接到 TMDB 人物搜索；《偷天父子兵》人物 ID 来自 TMDB 条目公开演职员链接。
