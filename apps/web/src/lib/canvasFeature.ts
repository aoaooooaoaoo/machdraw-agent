/**
 * 画布功能模块的自注册契约（strangler 阶段 2）。
 *
 * 机制与参考作品一致：`modules/registry.ts` 用 `import.meta.glob` 扫描
 * `features/<id>/index.ts`，每个默认导出一个 `CanvasFeature`。
 * 新增画布只需要：新建目录 + index.ts + Canvas 组件，**不改壳、不改 registry**。
 *
 * 注意：`id` 必须等于目录名（registry 会校验，不一致就跳过并 warn）。
 * `artifactTypes` 全局唯一；重复时后注册覆盖（与参考作品一致，warn 不阻断）。
 */
import type { ComponentType } from 'react';
import type { ArtifactState, ChatMessage } from './types';

/** 画布/整页组件能拿到的 props（与历史 `CanvasProps` 等价，保留 demo 兼容示例数据）。 */
export interface FeatureProps {
  artifact: ArtifactState;
  /** 画布里的追问按钮 → 写进中栏输入框 */
  onAsk: (text: string) => void;
  /** true = 本地示例数据（非后端产出），画布上会显示"示例"标记 */
  demo?: boolean;
  /** 整页模式：当前对话消息（只读，用于 Agent 抽屉） */
  messages?: ChatMessage[];
  /** 整页模式：Agent 是否在生成 */
  busy?: boolean;
  /** 整页模式：直接发消息给 Agent（不经过中栏输入框） */
  onSendMessage?: (text: string) => void;
}

/** 空态里的本地示例。data 直接作为 artifact.data 喂给 Component。 */
export interface CanvasPreview {
  /** 空态按钮文案，如「查看公差带示例」 */
  label: string;
  /** 样例 artifact 数据 */
  data: Record<string, unknown>;
}

/** 每个 `apps/web/src/features/<id>/index.ts` 默认导出的结构。 */
export interface CanvasFeature {
  /** 必须等于 features 下的目录名 */
  id: string;
  /** 画布标题（逐字沿用旧 registry 文案） */
  title: string;
  /** 画布副标题/提示 */
  hint: string;
  /** 这个模块认领的 artifactType；全局唯一 */
  artifactTypes: string[];
  /** 左栏/空态列表排序，小的在前（保持旧 registry 声明顺序） */
  order: number;
  /** 空态示例数据（可选；不填就没有「查看示例」按钮） */
  preview?: CanvasPreview;
  /**
   * 产出 artifact 时是否自动展开右栏（可选，默认 false）。
   * 判据：交付物是不是画布本身——展示型 true，对话型 false。
   */
  autoOpenCanvas?: boolean;
  /** 画布模式组件（右栏） */
  Component: ComponentType<FeatureProps>;
  /**
   * 整页模式组件（可选）。填了它，点左栏该模块时主区整个让给它，
   * 左栏仍保留作为退出出口；Agent 能力通过 messages/busy/onSendMessage 注入。
   */
  page?: ComponentType<FeatureProps>;
}
