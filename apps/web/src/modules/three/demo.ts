import type { ThreeViewArtifactData } from '../../lib/types';

/**
 * three_view 本地示例：真实 GET /api/models/M-L-BLOCK 的返回快照。
 * 仅用于后端不可达时的空态演示/自测；正常对话会下发真实 three_view artifact。
 */
export const THREE_VIEW_DEMO_DATA: ThreeViewArtifactData = {
  "model_id": "M-L-BLOCK",
  "name": "L 形块",
  "unit": "mm",
  "size": {
    "L": 100,
    "W": 60,
    "H": 60
  },
  "bbox": [
    [
      0,
      0,
      0
    ],
    [
      100,
      60,
      60
    ]
  ],
  "segments": [
    {
      "view": "front",
      "x1": 46,
      "y1": 128,
      "x2": 146,
      "y2": 128,
      "hidden": false
    },
    {
      "view": "front",
      "x1": 46,
      "y1": 108,
      "x2": 146,
      "y2": 108,
      "hidden": false
    },
    {
      "view": "front",
      "x1": 146,
      "y1": 128,
      "x2": 146,
      "y2": 108,
      "hidden": false
    },
    {
      "view": "front",
      "x1": 46,
      "y1": 128,
      "x2": 46,
      "y2": 68,
      "hidden": false
    },
    {
      "view": "front",
      "x1": 46,
      "y1": 68,
      "x2": 76,
      "y2": 68,
      "hidden": false
    },
    {
      "view": "front",
      "x1": 76,
      "y1": 108,
      "x2": 76,
      "y2": 68,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 46,
      "y1": 168,
      "x2": 146,
      "y2": 168,
      "hidden": true
    },
    {
      "view": "top",
      "x1": 46,
      "y1": 228,
      "x2": 146,
      "y2": 228,
      "hidden": true
    },
    {
      "view": "top",
      "x1": 46,
      "y1": 228,
      "x2": 76,
      "y2": 228,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 81.714,
      "y1": 228,
      "x2": 146,
      "y2": 228,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 146,
      "y1": 228,
      "x2": 146,
      "y2": 168,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 46,
      "y1": 168,
      "x2": 76,
      "y2": 168,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 81.714,
      "y1": 168,
      "x2": 146,
      "y2": 168,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 76,
      "y1": 228,
      "x2": 76,
      "y2": 168,
      "hidden": false
    },
    {
      "view": "top",
      "x1": 46,
      "y1": 228,
      "x2": 46,
      "y2": 168,
      "hidden": false
    },
    {
      "view": "left",
      "x1": 186,
      "y1": 128,
      "x2": 246,
      "y2": 128,
      "hidden": false
    },
    {
      "view": "left",
      "x1": 186,
      "y1": 108,
      "x2": 246,
      "y2": 108,
      "hidden": false
    },
    {
      "view": "left",
      "x1": 246,
      "y1": 128,
      "x2": 246,
      "y2": 68,
      "hidden": false
    },
    {
      "view": "left",
      "x1": 186,
      "y1": 128,
      "x2": 186,
      "y2": 68,
      "hidden": false
    },
    {
      "view": "left",
      "x1": 186,
      "y1": 68,
      "x2": 246,
      "y2": 68,
      "hidden": false
    }
  ],
  "stats": {
    "front": {
      "total": 6,
      "visible": 6,
      "hidden": 0
    },
    "top": {
      "total": 9,
      "visible": 7,
      "hidden": 2
    },
    "left": {
      "total": 5,
      "visible": 5,
      "hidden": 0
    }
  },
  "viewBox": [
    0,
    0,
    292,
    262
  ],
  "labels": [
    {
      "view": "front",
      "text": "主视图",
      "x": 96,
      "y": 146
    },
    {
      "view": "top",
      "text": "俯视图",
      "x": 96,
      "y": 246
    },
    {
      "view": "left",
      "text": "左视图",
      "x": 216,
      "y": 146
    }
  ],
  "aux": [
    {
      "kind": "long",
      "color": "#2563eb",
      "x1": 46,
      "y1": 68,
      "x2": 46,
      "y2": 228,
      "label": "长对正"
    },
    {
      "kind": "long",
      "color": "#2563eb",
      "x1": 146,
      "y1": 68,
      "x2": 146,
      "y2": 228,
      "label": ""
    },
    {
      "kind": "height",
      "color": "#16a34a",
      "x1": 46,
      "y1": 68,
      "x2": 246,
      "y2": 68,
      "label": "高平齐"
    },
    {
      "kind": "height",
      "color": "#16a34a",
      "x1": 46,
      "y1": 128,
      "x2": 246,
      "y2": 128,
      "label": ""
    },
    {
      "kind": "width",
      "color": "#d97706",
      "x1": 186,
      "y1": 168,
      "x2": 246,
      "y2": 228,
      "label": "宽相等"
    },
    {
      "kind": "width",
      "color": "#d97706",
      "x1": 146,
      "y1": 168,
      "x2": 186,
      "y2": 168,
      "label": ""
    },
    {
      "kind": "width",
      "color": "#d97706",
      "x1": 186,
      "y1": 168,
      "x2": 186,
      "y2": 128,
      "label": ""
    },
    {
      "kind": "width",
      "color": "#d97706",
      "x1": 146,
      "y1": 228,
      "x2": 246,
      "y2": 228,
      "label": ""
    },
    {
      "kind": "width",
      "color": "#d97706",
      "x1": 246,
      "y1": 228,
      "x2": 246,
      "y2": 128,
      "label": ""
    }
  ],
  "view_boxes": {
    "front": [
      46,
      68,
      146,
      128
    ],
    "top": [
      46,
      168,
      146,
      228
    ],
    "left": [
      186,
      68,
      246,
      128
    ]
  },
  "projection": "第一角"
};
