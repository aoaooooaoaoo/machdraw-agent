"""极简实体建模内核（供三视图真投影使用）。

只支持机械制图教学需要的形体：**轴对齐长方体 + 正多棱柱**，通过
「若干实体求并 − 若干实体挖除」构成 CSG 模型。棱柱用 n 边近似圆柱，
n=32 时肉眼已看不出棱（同时保证所有面都是平面，求交/判内外都简单可靠）。

不追求 CAD 级精度，追求：
  · 纯 Python 标准库，无依赖；
  · inside() 判定可靠 —— 隐藏线消除靠它；
  · 足以覆盖教学形体（L 形块、台阶、带孔方块、圆筒、支架、阶梯轴…）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Vec = tuple[float, float, float]


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a: Vec) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Vec) -> Vec:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)


@dataclass
class Poly:
    """凸多面体：顶点表 + 面（每个面是顶点索引的逆时针环，法向朝外）。"""

    verts: list[Vec]
    faces: list[list[int]]
    _normals: list[Vec] = field(default_factory=list, repr=False)
    _fcenters: list[Vec] = field(default_factory=list, repr=False)
    _center: Vec = (0.0, 0.0, 0.0)
    bbox: tuple[Vec, Vec] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def __post_init__(self) -> None:
        self._orient()
        xs = [v[0] for v in self.verts]
        ys = [v[1] for v in self.verts]
        zs = [v[2] for v in self.verts]
        self.bbox = ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

    def _orient(self) -> None:
        n = len(self.verts)
        self._center = (
            sum(v[0] for v in self.verts) / n,
            sum(v[1] for v in self.verts) / n,
            sum(v[2] for v in self.verts) / n,
        )
        self._normals = []
        self._fcenters = []
        for f in self.faces:
            # Newell 法求多边形法向
            nx = ny = nz = 0.0
            m = len(f)
            for i in range(m):
                a = self.verts[f[i]]
                b = self.verts[f[(i + 1) % m]]
                nx += (a[1] - b[1]) * (a[2] + b[2])
                ny += (a[2] - b[2]) * (a[0] + b[0])
                nz += (a[0] - b[0]) * (a[1] + b[1])
            nrm = unit((nx, ny, nz))
            c = (
                sum(self.verts[i][0] for i in f) / m,
                sum(self.verts[i][1] for i in f) / m,
                sum(self.verts[i][2] for i in f) / m,
            )
            # 朝外：法向应背离形心
            if dot(nrm, sub(c, self._center)) < 0:
                nrm = (-nrm[0], -nrm[1], -nrm[2])
                self.faces[self.faces.index(f)] = list(reversed(f))
            self._normals.append(nrm)
            self._fcenters.append(c)

    # ---------------- 几何谓词
    def inside(self, p: Vec, eps: float = 1e-9) -> bool:
        bb0, bb1 = self.bbox
        if not (
            bb0[0] - eps <= p[0] <= bb1[0] + eps
            and bb0[1] - eps <= p[1] <= bb1[1] + eps
            and bb0[2] - eps <= p[2] <= bb1[2] + eps
        ):
            return False
        for nrm, c in zip(self._normals, self._fcenters):
            if dot(nrm, sub(p, c)) > eps:
                return False
        return True

    def face_normal(self, fi: int) -> Vec:
        return self._normals[fi]

    def edges(self) -> dict[tuple[int, int], list[int]]:
        """无向边 → 相邻面索引列表。"""
        out: dict[tuple[int, int], list[int]] = {}
        for fi, f in enumerate(self.faces):
            m = len(f)
            for i in range(m):
                a, b = f[i], f[(i + 1) % m]
                key = (a, b) if a < b else (b, a)
                out.setdefault(key, []).append(fi)
        return out


# ---------------------------------------------------------------- 体素构造


def box(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Poly:
    """轴对齐长方体。"""
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    f = [
        [0, 3, 2, 1],  # z0 底
        [4, 5, 6, 7],  # z1 顶
        [0, 1, 5, 4],  # y0 前
        [2, 3, 7, 6],  # y1 后
        [1, 2, 6, 5],  # x1 右
        [3, 0, 4, 7],  # x0 左
    ]
    return Poly(v, f)


def prism(axis: str, cx: float, cy: float, cz: float, r: float,
          lo: float, hi: float, n: int = 32) -> Poly:
    """正 n 棱柱（近似圆柱）。

    axis: 'x'|'y'|'z'  —— 轴线方向
    cx,cy,cz: 轴线上一点（该轴坐标被忽略，由 lo/hi 给出范围）
    lo, hi: 沿轴线的起止坐标
    """
    ring: list[Vec] = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t) * r, math.sin(t) * r
        if axis == "z":
            ring.append((cx + c, cy + s, 0.0))
        elif axis == "x":
            ring.append((0.0, cy + c, cz + s))
        else:  # y
            ring.append((cx + c, 0.0, cz + s))

    verts: list[Vec] = []
    for z in (lo, hi):
        for p in ring:
            if axis == "z":
                verts.append((p[0], p[1], z))
            elif axis == "x":
                verts.append((z, p[1], p[2]))
            else:
                verts.append((p[0], z, p[2]))

    faces: list[list[int]] = []
    faces.append(list(range(n - 1, -1, -1)))            # 底面（反向）
    faces.append(list(range(n, 2 * n)))                  # 顶面
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return Poly(verts, faces)


@dataclass
class Solid:
    """CSG：adds 求并，subs 挖除。"""

    adds: list[Poly]
    subs: list[Poly] = field(default_factory=list)

    def inside(self, p: Vec) -> bool:
        for s in self.subs:
            if s.inside(p):
                return False
        for a in self.adds:
            if a.inside(p):
                return True
        return False

    def bbox(self) -> tuple[Vec, Vec]:
        bs = [p.bbox for p in self.adds] or [((0, 0, 0), (0, 0, 0))]
        lo = (min(b[0][0] for b in bs), min(b[0][1] for b in bs), min(b[0][2] for b in bs))
        hi = (max(b[1][0] for b in bs), max(b[1][1] for b in bs), max(b[1][2] for b in bs))
        return lo, hi


def _seam_edge(solid: Solid, mid: Vec, own: int) -> bool:
    """判断这条棱是不是"并集伪接缝"。

    两个长方体并在一起且**表面平齐**时，接合处会多出一条并不存在的棱
    （例如 L 形块由底板 + 竖板拼成，前面共面，接缝处不该画线）。
    判据：中点落在另一个体的某个**共面同向**面上 → 是伪接缝。
    凸多面体有个好性质：点在某面的平面上且在体内 ⟹ 点在该面内。
    """
    polys = solid.adds + solid.subs
    for qi, q in enumerate(polys):
        if qi == own or not q.inside(mid, eps=1e-6):
            continue
        for nq, cq in zip(q._normals, q._fcenters):
            plane = dot(nq, cq)
            if abs(dot(nq, mid) - plane) > 1e-6:
                continue
            # 中点落在 q 的这个面上；再去 own 体里找有没有共面同向的面
            for pi, p in enumerate(polys):
                if pi == qi or pi == own:
                    continue
                for np_, cp in zip(p._normals, p._fcenters):
                    if dot(np_, nq) > 1 - 1e-6 and abs(dot(np_, cp) - plane) < 1e-6:
                        return True
    return False


def edge_segments(solid: Solid, sharp_deg: float = 25.0) -> list[dict]:
    """提取候选棱边：锐边（二面角 > sharp_deg）与轮廓线（silhouette）。

    返回 [{p, q, sharp, faces:[(poly_idx, face_idx), ...]}]，供投影阶段按视角筛轮廓。
    """
    keys: dict[tuple[tuple[float, float, float], tuple[float, float, float]], dict] = {}
    for pi, poly in enumerate(solid.adds + solid.subs):
        for (i, j), adj in poly.edges().items():
            if len(adj) != 2:
                continue
            a = poly._normals[adj[0]]
            b = poly._normals[adj[1]]
            cosang = max(-1.0, min(1.0, dot(a, b)))
            ang = math.degrees(math.acos(cosang))
            p, q = poly.verts[i], poly.verts[j]
            k = (tuple(round(x, 6) for x in p), tuple(round(x, 6) for x in q))
            kr = (k[1], k[0]) if k[1] < k[0] else k
            rec = keys.get(kr)
            if rec is None:
                keys[kr] = {
                    "p": k[0],
                    "q": k[1],
                    "sharp": ang > sharp_deg,
                    "faces": [(pi, adj[0]), (pi, adj[1])],
                    "owners": {pi},
                }
            else:
                rec["sharp"] = rec["sharp"] or ang > sharp_deg
                rec["faces"].extend([(pi, adj[0]), (pi, adj[1])])
                rec["owners"].add(pi)

    out: list[dict] = []
    for rec in keys.values():
        mid = (
            (rec["p"][0] + rec["q"][0]) / 2,
            (rec["p"][1] + rec["q"][1]) / 2,
            (rec["p"][2] + rec["q"][2]) / 2,
        )
        owner = min(rec["owners"])
        if _seam_edge(solid, mid, owner):
            continue
        rec["mid"] = mid
        out.append(rec)
    return out
