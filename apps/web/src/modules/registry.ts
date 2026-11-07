import type { ComponentType } from 'react';
import type { CanvasPreview, FeatureProps } from '../lib/canvasFeature';
import type { CanvasFeature } from '../lib/canvasFeature';
import { PlaceholderCanvas } from './placeholder/Canvas';

/** 兼容旧签名：壳与 9 个画布组件都从 `modules/registry` 引 `CanvasProps`。 */
export type CanvasProps = FeatureProps;
export type { FeatureProps } from '../lib/canvasFeature';
export type { CanvasFeature, CanvasPreview } from '../lib/canvasFeature';

export interface CanvasDef {
  title: string;
  hint: string;
  component: ComponentType<CanvasProps>;
}

/**
 * ★ 自注册：扫描 features 目录下每个模块的 index.ts，不需要在这里维护 map / import。
 *
 * 每个 feature 默认导出 `CanvasFeature`（见 lib/canvasFeature.ts）：
 *   id 必须等于目录名；artifactTypes 全局唯一（重复时 warn，后注册覆盖）。
 * 新增画布 = 新建 `features/<id>/index.ts` + 组件，**不改本文件**。
 *
 * Eager 模式在构建期静态展开（与参考作品一致），运行时不读目录。
 */
const modules = import.meta.glob<{ default: CanvasFeature }>('../features/*/index.ts', {
  eager: true,
});

const features: CanvasFeature[] = [];

for (const [path, mod] of Object.entries(modules)) {
  // path 形如 '../features/evidence/index.ts'
  const dir = path.split('/')[2] ?? '';
  const feature = mod?.default;
  if (!feature) {
    console.warn(`[registry] ${path} 没有默认导出 CanvasFeature，已跳过`);
    continue;
  }
  if (feature.id !== dir) {
    console.warn(
      `[registry] feature.id "${feature.id}" 与目录名 "${dir}" 不一致（必须以目录名为准），已跳过 ${path}`,
    );
    continue;
  }
  if (!Array.isArray(feature.artifactTypes) || feature.artifactTypes.length === 0) {
    console.warn(`[registry] feature "${feature.id}" 没有声明 artifactTypes，已跳过`);
    continue;
  }
  features.push(feature);
}

// 按 order 升序，保持改造前 KNOWN_CANVAS_TYPES 的声明顺序（空态列表/计数不变）
features.sort((a, b) => a.order - b.order);

/** artifactType → 渲染器。未知类型不在表里，getCanvasDef 会回落 PlaceholderCanvas。 */
const REGISTRY: Record<string, CanvasDef> = {};
/** feature.id / artifactType → 空态示例 */
const PREVIEWS = new Map<string, CanvasPreview>();
/** feature.id / artifactType → 该 feature 的第一个 artifactType */
const PREVIEW_TYPES = new Map<string, string>();
/** artifactType → 产出该类型时是否自动展开右栏 */
const AUTO_OPEN = new Map<string, boolean>();

for (const feature of features) {
  const def: CanvasDef = {
    title: feature.title,
    hint: feature.hint,
    component: feature.Component,
  };
  const firstType = feature.artifactTypes[0];
  if (firstType) {
    PREVIEW_TYPES.set(feature.id, firstType);
    for (const artifactType of feature.artifactTypes) PREVIEW_TYPES.set(artifactType, artifactType);
  }
  if (feature.preview) {
    PREVIEWS.set(feature.id, feature.preview);
    for (const artifactType of feature.artifactTypes) PREVIEWS.set(artifactType, feature.preview);
  }
  for (const artifactType of feature.artifactTypes) {
    const previous = REGISTRY[artifactType];
    if (previous) {
      console.warn(
        `[registry] artifactType "${artifactType}" 被多个 feature 注册（"${previous.title}" 与 "${feature.id}"），` +
          `后注册的覆盖前者`,
      );
    }
    REGISTRY[artifactType] = def;
    AUTO_OPEN.set(artifactType, Boolean(feature.autoOpenCanvas));
  }
}

/** 取某 feature（或 artifactType）的空态示例；没有返回 null。 */
export function getPreview(featureId: string): CanvasPreview | null {
  return PREVIEWS.get(featureId) ?? null;
}

/** 取某 feature（或 artifactType）的第一个 artifactType，供壳构造示例 artifact。 */
export function getPreviewType(featureId: string): string | null {
  return PREVIEW_TYPES.get(featureId) ?? null;
}

/** 产出该 artifactType 时是否自动展开右栏（未声明默认 false）。 */
export function shouldAutoOpen(artifactType: string): boolean {
  return AUTO_OPEN.get(artifactType) ?? false;
}

export function getCanvasDef(artifactType: string): CanvasDef {
  return (
    REGISTRY[artifactType] ?? {
      title: `${artifactType} 画布`,
      hint: '该 artifactType 尚未在注册表中登记',
      component: PlaceholderCanvas,
    }
  );
}

export const KNOWN_CANVAS_TYPES = Object.keys(REGISTRY);

export function isPlaceholder(artifactType: string): boolean {
  const def = REGISTRY[artifactType];
  return !def || def.component === PlaceholderCanvas;
}

/** 这个 artifactType 有没有画布 owner（用于 store 的 artifact 兜底）。 */
export function hasCanvasOwner(artifactType: string): boolean {
  return Object.prototype.hasOwnProperty.call(REGISTRY, artifactType);
}

/** 已注册的 feature 列表（按 order 排序，只读）。排查重复注册时用。 */
export const CANVAS_FEATURES: readonly CanvasFeature[] = features;

/** 按 feature id 取模块（整页模式按模块 id 查找；目前 graph 的 module id 与 feature id 同名）。 */
export function getCanvasFeature(featureId: string): CanvasFeature | undefined {
  return features.find((feature) => feature.id === featureId);
}
