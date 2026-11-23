/**
 * 局部图布局：根在中间，上游往左，下游往右。
 *
 * 不引布局库：节点数被服务端限制在 200 以内，按层排布足够，
 * 而且层次感比力导向更能体现「供应链方向」。
 */

import type { GraphEdge, GraphNode, GraphResponse } from './api'

export interface LaidOutNode extends GraphNode {
  x: number
  y: number
  level: number
}

export interface LaidOutEdge extends GraphEdge {
  path: string
}

export interface Layout {
  nodes: LaidOutNode[]
  edges: LaidOutEdge[]
  bounds: { x: number; y: number; width: number; height: number }
  hidden: number
}

export const NODE_W = 208
export const NODE_H = 54
const LEVEL_GAP = 128 // 层间额外留白
const ROW_GAP = 20
const PER_COLUMN = 8 // 一列最多放几个节点，多了往同一层的外侧折列

export function layoutGraph(graph: GraphResponse, maxPerLevel = 8): Layout {
  const byId = new Map(graph.nodes.map((node) => [node.id, node]))
  const level = new Map<string, number>([[graph.root, 0]])

  // 双向 BFS：走 parent 边往左（-1），走 child 边往右（+1）
  const queue: string[] = [graph.root]
  while (queue.length) {
    const current = queue.shift()!
    const base = level.get(current) ?? 0
    for (const edge of graph.edges) {
      let next: string | null = null
      let delta = 0
      if (edge.target === current && !level.has(edge.source)) {
        next = edge.source
        delta = -1
      } else if (edge.source === current && !level.has(edge.target)) {
        next = edge.target
        delta = 1
      }
      if (next) {
        level.set(next, base + delta)
        queue.push(next)
      }
    }
  }

  // 落单节点（理论上不会有）挂在 0 层
  for (const node of graph.nodes) {
    if (!level.has(node.id)) level.set(node.id, 0)
  }

  const downloads = new Map(graph.nodes.map((node) => [node.id, node.downloads ?? -1]))

  const groups = new Map<number, string[]>()
  for (const [id, lv] of level) {
    const list = groups.get(lv) ?? []
    list.push(id)
    groups.set(lv, list)
  }

  // 每层只保留下载量最高的若干个，避免几十个下游把画布压成蚂蚁
  let hidden = 0
  for (const [lv, ids] of groups) {
    const cap = lv === 0 ? 1 : maxPerLevel
    if (ids.length <= cap) continue
    ids.sort((a, b) => (downloads.get(b) ?? -1) - (downloads.get(a) ?? -1) || a.localeCompare(b))
    hidden += ids.length - cap
    groups.set(lv, ids.slice(0, cap))
  }

  const visible = new Set([...groups.values()].flat())

  const placed: LaidOutNode[] = []
  for (const [lv, ids] of [...groups.entries()].sort((a, b) => a[0] - b[0])) {
    ids.sort((a, b) => (downloads.get(b) ?? -1) - (downloads.get(a) ?? -1) || a.localeCompare(b))
    // 同一层按 PER_COLUMN 折列：上游往外侧（更左），下游往外侧（更右）
    const chunks: string[][] = []
    for (let i = 0; i < ids.length; i += PER_COLUMN) chunks.push(ids.slice(i, i + PER_COLUMN))
    const outward = lv === 0 ? 0 : Math.sign(lv)

    chunks.forEach((chunk, column) => {
      const total = chunk.length
      const x = lv * (NODE_W + LEVEL_GAP) + outward * column * (NODE_W + 36)
      chunk.forEach((id, index) => {
        const node = byId.get(id)
        if (!node) return
        placed.push({
          ...node,
          level: lv,
          x,
          y: (index - (total - 1) / 2) * (NODE_H + ROW_GAP),
        })
      })
    })
  }

  const position = new Map(placed.map((node) => [node.id, node]))
  const edges: LaidOutEdge[] = []
  for (const edge of graph.edges) {
    if (!visible.has(edge.source) || !visible.has(edge.target)) continue
    const from = position.get(edge.source)
    const to = position.get(edge.target)
    if (!from || !to) continue
    const x1 = from.x + NODE_W / 2
    const x2 = to.x - NODE_W / 2
    const mid = (x1 + x2) / 2
    edges.push({
      ...edge,
      path: `M ${x1} ${from.y} C ${mid} ${from.y}, ${mid} ${to.y}, ${x2} ${to.y}`,
    })
  }

  const xs = placed.map((n) => n.x)
  const ys = placed.map((n) => n.y)
  const minX = Math.min(...xs) - NODE_W / 2 - 48
  const maxX = Math.max(...xs) + NODE_W / 2 + 48
  const minY = Math.min(...ys) - NODE_H / 2 - 48
  const maxY = Math.max(...ys) + NODE_H / 2 + 48

  return {
    nodes: placed,
    edges,
    bounds: { x: minX, y: minY, width: maxX - minX, height: maxY - minY },
    hidden,
  }
}
