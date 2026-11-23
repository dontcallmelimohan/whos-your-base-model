import { createRouter, createWebHashHistory } from 'vue-router'

import DataPage from '@/modules/data/DataPage.vue'
import AnalysisPage from '@/modules/analysis/AnalysisPage.vue'
import CatalogPage from '@/modules/catalog/CatalogPage.vue'
import EvidencePage from '@/modules/evidence/EvidencePage.vue'
import LineagePage from '@/modules/lineage/LineagePage.vue'
import PlaceholderPage from './PlaceholderPage.vue'

/**
 * 路由登记处。
 *
 * 每个工作包只需要改两行：
 *   1. 把 PlaceholderPage 换成自己的页面组件；
 *   2. 删除 meta.owner 里的“待认领”。
 *
 * 用 hash 模式：静态托管（GitHub Pages / 本地 file://）都不用配服务器回退。
 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/data' },
    {
      path: '/data',
      name: 'data',
      component: DataPage,
      meta: { title: '数据管理', owner: 'A' },
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: CatalogPage,
      meta: { title: '模型目录', owner: 'B' },
    },
    {
      path: '/lineage',
      name: 'lineage',
      component: LineagePage,
      meta: { title: '供应链小图', owner: 'B' },
    },
    {
      path: '/evidence',
      name: 'evidence',
      component: EvidencePage,
      meta: { title: '依赖核验', owner: '3' },
    },
    {
      path: '/galaxy',
      name: 'galaxy',
      component: PlaceholderPage,
      meta: {
        title: '大图 Galaxy',
        owner: 'C',
        desc: '全量点云、家族着色、缩放平移。组件放在 src/modules/galaxy/。',
      },
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: AnalysisPage,
      meta: { title: '生态分析', owner: 'D' },
    },
  ],
})

export default router
