# 场景渲染设计

> 定位：Hero 左侧场景（立方体、网格、地面、光照）的坐标约定、调整不变量与当前参数。回答"为什么这样渲染、改参数时什么不能变"。

## 渲染架构

SVG 由 Python 在构建期完全展开：动态文件只包含预先计算的投影关键帧和 SMIL 插值，不含脚本、CSS、外部图片、外部字体或运行时几何计算。原因是 GitHub README 经 camo 代理展示图片，不执行 JavaScript；SMIL 是静态文件里唯一可用的动画手段。

light/dark 两份产物共用同一次几何计算，只允许墨色不同；`render_hero()` 只计算一次时间线。

## 坐标系与旋转

- 世界坐标：Y 竖直、前方 -Z、地面 XZ；Blender 映射为 `(x,-z,y)`。
- Euler 顺序 `Rz@Ry@Rx`。

## 相机调整不变量

调整 pitch、yaw、距离时，全部顶点的屏幕投影、深度、轮廓和相对旋转必须固定，不能只锁中心或单个顶点。三个调整的补偿公式：

非零 yaw 时的俯角补偿（相机局部轴）：

```text
Q = Ry(yaw) · Rx(old_pitch-new_pitch) · Ry(-yaw)
cube_center1 = C + Q·(cube_center0-C)
cube_rotation1 = Q·cube_rotation0
```

高度轴 yaw：

```text
T = 当前视线中心的地面观察目标
Q = Ry(new_yaw-old_yaw)
C1 = T + Q·(C0-T)
cube_center1 = T + Q·(cube_center0-T)
cube_rotation1 = Q·cube_rotation0
```

滚轮式 zoom（大于 1 拉远，小于 1 拉近）：

```text
L = h / sin(pitch)
Δ = (factor-1)·L
C1 = C + (sin(yaw)·cos(pitch)·Δ, sin(pitch)·Δ, cos(yaw)·cos(pitch)·Δ)
cube_center1 = cube_center0 + (C1-C0)
cube_rotation1 = cube_rotation0
```

## 三轴动态

`gen/hero/scene.json` 的 `motion` 只保存声明式参数（`period_seconds`、`turns`、`angle_step_degrees`），帧数据由构建期派生：

```text
Rworld(t) = C⁻¹ · ΔRcamera(t) · C · R₀
ΔRcamera = Rz(2π·turns.z·t) · Ry(2π·turns.y·t) · Rx(2π·turns.x·t)
```

中心、尺寸、相机、网格和地面固定；最快轴每 1° 采样一次，当前 721 帧（含闭环帧），首末帧直接复用静态几何以避免浮点接缝。调整转速只改 SMIL `dur`，不重新采样。

动态 SVG 只有六面 `points`、面可见性和既有强调棱线的端点/可见性动画；凸体可见面互不覆盖，无需动态 z-index。材质角色在首帧绑定物理面，播放中不重新执行 `classify()`，避免突然换色。

## 网格 LOD

```text
lod_level = max(0, floor(log2(zoom)))
if lod_level <= 3:
    step = base_step · 2^lod_level
    major_every = max(1, base_major_every // 2^lod_level)
else:
    step = base_step · base_major_every · 2^(lod_level-4)
    major_every = 2

major_spacing = step · major_every
screen_spacing = (step / base_step) / zoom
t = max(0, log2(zoom))
major_opacity = 1 / (1+t)
minor_opacity = 0.1 + 0.9 / (1+t)^2
fade[0.18] = min(1, 0.12 / zoom)
fade[0.48] = min(1, 0.65 / sqrt(zoom))
```

每累计 2× 合并一次。LOD 0/1/2/3 的 `major_every=8/4/2/1`，先抽稀次线；8× 只剩旧主线，16× 保持 step 并令 `major_every=2`，旧主线降级为下一尺度的次线。测试覆盖 1×–65536×，该范围内次线最终绘制不透明度始终低于主线。

## 光照与曝光

- 光学地平线位于画外（SVG 计算 `y=-145.442650`），不绘制独立光带或发光核心线。
- 相机水平位置上方 16 个世界单位、半径 72 的环形光源；对 64 个环形采样点的地面辐照度积分，沿视线中心取 17 个地面样本做指数曝光生成地面渐变。双主题共用同一光源几何与曝光公式。
- 浅色：`ambient=2.8`、`intensity=1.3`，边缘接近浏览器白背景。深色：`ambient=0`、`intensity=1000`，受光目标 `#090c11`，周界颜色来自环形光而非常量环境光或覆盖层。
- 金属渐变以相机屏幕中心 `(800,450)` 为中心的宽环形环境反射（反射半径为宽度 0.48、峰值不透明度 0.55），不含独立可见光圈。深色金属从浅色基础 palette 反色出发向白混合 20%，避免浅色提亮经反色使深色变暗。
- 无 `page-fade`、四缘透明矩形、vignette 或独立雾层；`gridA=0.38` 两主题相同，深色网格颜色由浅色 RGB 反色得到。

## 当前视觉参数

- 画布 1600×900；50mm / 36mm sensor，焦距约 2222.22。
- 相机 `[42.458938117,48.7862838,83.279365396]`，pitch 15°、yaw 20°、shift 0。
- 立方体中心 `[33.172317955,46.274368262,75.409745754]`，尺寸 4.24，旋转约 `[25.476959°,-8.449302°,35.614087°]`。
- 网格 LOD 2、step 1、major_every 2（主线世界间距 2）；主副系数 `0.330748951/0.198455382`。
- 动画周期 400s、转速为初版的 60%、turns `[1,2,1]`；完整循环最右投影约 333px，仍在画布左四分之一内。
- 每份动态 SVG 约 490 KiB，静态约 205 KiB。

参数调整一律通过 `scripts/adjust_scene.py`（见 [usage](../usage.md)），不手改 `scene.json`。
