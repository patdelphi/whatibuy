# WhatIBuy - 个人消费分析工具

WhatIBuy是一款个人购物历史分析工具，帮助用户自动整理和分析在多个电商平台的购物数据。通过本地浏览器自动化技术采集订单信息，提供消费趋势分析和可视化报告。

## 🌟 功能特性

### 数据采集
- **淘宝订单采集**：支持淘宝网页端订单历史自动采集
- **京东订单采集**：支持京东订单页面数据抓取  
- **闲鱼订单采集**：支持闲鱼平台交易记录获取
- **增量更新**：智能识别新订单，避免重复采集

### 数据分析
- **消费总览**：总消费金额、订单数量、平均单价统计
- **趋势分析**：按月份展示消费趋势折线图
- **分类分析**：商品类别消费占比和TOP类别排行
- **平台对比**：不同平台消费金额和订单数量对比
- **高价商品**：单笔消费最高的商品列表展示

### AI购物助手
- **智能对话**：基于自然语言查询购物历史
- **消费建议**：AI分析消费习惯提供个性化建议
- **历史记录**：保存对话历史，支持查看过往问答

### 数据可视化
- **交互式图表**：支持悬停显示详细数据
- **时间筛选**：灵活的时间范围选择
- **多维度分析**：平台、类别、时间等多维度数据展示

## 🛠 技术栈

### 后端
- **Python 3.12+**：主要后端开发语言
- **FastAPI**：高性能Web API框架
- **Playwright**：浏览器自动化工具
- **SQLite**：轻量级本地数据库
- **Pandas**：数据处理和分析
- **Matplotlib**：数据可视化图表

### 前端
- **React 18**：现代化前端框架
- **TypeScript**：类型安全的JavaScript
- **Vite**：快速构建工具
- **Tailwind CSS**：实用优先的CSS框架
- **Recharts**：React图表库
- **Zustand**：轻量级状态管理

### 开发工具
- **pnpm**：快速、节省磁盘空间的包管理器
- **ESLint**：代码质量检查
- **Playwright**：端到端测试

## 📦 安装部署

### 环境要求
- Python 3.12+
- Node.js 18+
- pnpm包管理器

### 后端设置

1. **克隆项目**
```bash
git clone https://github.com/patdelphi/whatibuy.git
cd whatibuy
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **初始化数据库**
```bash
cd src/database
python init_db.py
```

5. **启动API服务**
```bash
cd src/api
python main.py
```

### 前端设置

1. **安装依赖**
```bash
cd frontend
pnpm install
```

2. **启动开发服务器**
```bash
pnpm dev
```

3. **构建生产版本**
```bash
pnpm build
```

### 数据采集

1. **运行爬虫**
```bash
python run_scraper.py
```

2. **浏览器自动化**
- 程序会自动启动浏览器
- 用户需要手动登录电商平台
- 登录完成后点击"登录完成"按钮
- 系统自动采集订单数据

## 🎯 使用指南

### 首次使用
1. 访问 `http://localhost:5173` 打开前端界面
2. 在设置页面配置AI接口参数（可选）
3. 在数据管理页面添加电商平台配置
4. 启动数据采集流程
5. 在分析仪表板查看消费报告

### 数据采集流程
1. 选择要采集的电商平台
2. 点击"开始采集"按钮
3. 系统自动启动浏览器并导航至登录页面
4. 用户手动完成登录流程
5. 点击"登录完成"通知系统
6. 系统自动采集订单数据并存储

### 支持平台
| 平台 | 登录URL | 订单URL | 状态 |
|------|---------|---------|------|
| 淘宝 | https://www.taobao.com/ | https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm | ✅ |
| 京东 | https://www.jd.com/ | https://order.jd.com/center/list.action | ✅ |
| 闲鱼 | https://www.goofish.com/ | https://www.goofish.com/bought | ✅ |
| 拼多多 | - | - | ❌ |

## 🔧 配置说明

### 数据库配置
- 数据库文件：`data/whatibuy.db`
- 自动创建表结构，无需手动配置
- 支持数据备份和导出

### AI服务配置
支持以下AI服务提供商：
- OpenAI GPT系列
- Google Gemini
- Anthropic Claude

### 浏览器配置
- 使用Playwright管理浏览器实例
- 支持Chromium、Firefox、WebKit
- 用户数据存储在`data/user_data/`目录

## 📊 数据隐私

### 本地存储
- 所有数据存储在本地SQLite数据库
- 不上传用户个人信息到外部服务器
- 浏览器配置文件本地保存

### 数据安全
- 不存储用户登录凭证
- 数据采集过程用户可控
- 支持数据导出和删除

## 🤝 贡献指南

1. Fork项目到个人仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交修改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建Pull Request

## 📝 开发计划

- [ ] 支持更多电商平台
- [ ] 增强AI分析能力
- [ ] 数据导出格式扩展
- [ ] 移动端适配
- [ ] 多语言支持

## 📞 联系方式

- 项目地址：https://github.com/patdelphi/whatibuy
- 问题反馈：请在GitHub Issues中提交

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**注意**：本项目仅供个人学习使用，请遵守相关平台的使用条款和隐私政策。