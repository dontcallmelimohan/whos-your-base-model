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
 *   2. 把 meta.owner 写成 v5 的任务号（1/2/3/4）或“扩展”。
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
      meta: { title: '数据管理', owner: '1' },
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: CatalogPage,
      meta: { title: '模型目录', owner: '1' },
    },
    {
      path: '/lineage',
      name: 'lineage',
      component: LineagePage,
      meta: { title: '谱系图', owner: '2' },
    },
    {
      path: '/evidence',
      name: 'evidence',
      component: EvidencePage,
      meta: { title: '核验与补全', owner: '4' },
    },
    {
      path: '/galaxy',
      name: 'galaxy',
      component: PlaceholderPage,
      meta: {
        title: '大图 Galaxy（扩展）',
        owner: '扩展',
        desc: '全量点云、家族着色、缩放平移。v5 不验收，组件放在 src/modules/galaxy/。',
      },
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: AnalysisPage,
      meta: { title: '生态分析', owner: '1' },
    },
  ],
})

export default router
