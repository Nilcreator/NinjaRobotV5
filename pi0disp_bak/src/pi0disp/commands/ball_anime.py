#
# (c) 2025 Yoichi Tanibayashi
#
"""
ST7789Vディスプレイで動作する、物理ベースのアニメーションデモ。
見た目維持・計算処理最適化版。
"""
import time
import colorsys
from typing import List
import math

import click
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import importlib.resources

from ..disp.st7789v import ST7789V
from ..utils.performance_core import RegionOptimizer


# --- 元の見た目設定を維持 ---
SPI_SPEED_HZ = 16000000
TARGET_FPS = 30.0
BALL_RADIUS = 20
TEXT_COLOR = (255, 255, 255)
FPS_UPDATE_INTERVAL = 0.2

# --- 計算最適化のみの設定 ---
PHYSICS_SUBSTEPS = 4  # 物理精度維持
COLLISION_CHECK_SKIP = 2  # 衝突チェックのみ軽量化
MAX_SPEED_SQ = 1000000.0  # speed^2での比較用（1000^2）

# 事前計算済み定数
TWO_PI = 2.0 * math.pi
SQRT_CACHE = {}  # 平方根キャッシュ
COS_SIN_CACHE = {}  # 三角関数キャッシュ

# --- 高速化ヘルパー関数 ---
def fast_sqrt(value):
    """キャッシュ付き高速平方根計算"""
    if value in SQRT_CACHE:
        return SQRT_CACHE[value]
    result = math.sqrt(value)
    if len(SQRT_CACHE) < 1000:  # キャッシュサイズ制限
        SQRT_CACHE[value] = result
    return result

def fast_cos_sin(angle):
    """キャッシュ付き三角関数計算"""
    # 角度を適度に量子化してキャッシュヒット率向上
    quantized = round(angle * 100) / 100
    if quantized in COS_SIN_CACHE:
        return COS_SIN_CACHE[quantized]
    
    cos_val = math.cos(quantized)
    sin_val = math.sin(quantized)
    if len(COS_SIN_CACHE) < 500:
        COS_SIN_CACHE[quantized] = (cos_val, sin_val)
    return cos_val, sin_val

# --- 最適化されたクラス定義 ---
class Ball:
    """計算最適化版ボールクラス（見た目は同じ）"""
    __slots__ = ('x', 'y', 'radius', 'speed_x', 'speed_y', 'fill_color', 'prev_bbox', 
                 'speed_sq', '_bbox_cache', '_bbox_dirty')

    def __init__(self, x, y, radius, speed, angle, fill_color):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        
        # 三角関数計算を事前実行
        cos_a, sin_a = fast_cos_sin(angle)
        self.speed_x = speed * cos_a
        self.speed_y = speed * sin_a
        self.speed_sq = speed * speed  # 速度の二乗を事前計算
        
        self.fill_color = fill_color
        self.prev_bbox = None
        self._bbox_cache = None
        self._bbox_dirty = True

    def update_position(self, delta_t, screen_width, screen_height):
        """位置更新（計算最適化版）"""
        # インライン計算で関数呼び出しオーバーヘッド削減
        new_x = self.x + self.speed_x * delta_t
        new_y = self.y + self.speed_y * delta_t
        
        # 境界チェック（分岐予測最適化）
        r = self.radius
        width_limit = screen_width - r
        height_limit = screen_height - r
        
        # X軸境界チェック
        if new_x <= r:
            new_x = r
            self.speed_x = -self.speed_x
        elif new_x >= width_limit:
            new_x = width_limit - 1
            self.speed_x = -self.speed_x
        
        # Y軸境界チェック
        if new_y <= r:
            new_y = r
            self.speed_y = -self.speed_y
        elif new_y >= height_limit:
            new_y = height_limit - 1
            self.speed_y = -self.speed_y
        
        # 位置更新時に速度の二乗も更新
        self.speed_sq = self.speed_x * self.speed_x + self.speed_y * self.speed_y
        
        # 位置が変わったらbboxキャッシュを無効化
        if new_x != self.x or new_y != self.y:
            self.x = new_x
            self.y = new_y
            self._bbox_dirty = True

    def get_bbox(self):
        """バウンディングボックス取得（キャッシュ付き）"""
        if self._bbox_dirty or self._bbox_cache is None:
            r = self.radius
            x_int = int(self.x)
            y_int = int(self.y)
            self._bbox_cache = (x_int - r, y_int - r, x_int + r, y_int + r)
            self._bbox_dirty = False
        return self._bbox_cache

    def draw(self, draw: ImageDraw.ImageDraw):
        """描画処理（変更なし）"""
        bbox = self.get_bbox()
        draw.ellipse(bbox, fill=self.fill_color, outline=self.fill_color)

class FpsCounter:
    """FPSカウンター（計算最適化版）"""
    __slots__ = ('frame_count', 'last_update_time', 'fps_text', '_update_threshold')
    
    def __init__(self):
        self.frame_count = 0
        self.last_update_time = time.time()
        self.fps_text = "FPS: --"
        self._update_threshold = FPS_UPDATE_INTERVAL  # 閾値を事前計算

    def update(self) -> bool:
        """FPS更新（除算最小化）"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        if elapsed >= self._update_threshold:
            # 除算を1回のみ実行
            fps = self.frame_count / elapsed
            self.fps_text = f"FPS: {fps:.0f}"
            self.frame_count = 0
            self.last_update_time = current_time
            return True
        return False

# --- 計算最適化されたヘルパー関数 ---
def _initialize_balls_optimized(num_balls: int, width: int, height: int, ball_speed: float) -> List[Ball]:
    """ボール初期化（計算最適化版）"""
    balls: List[Ball] = []
    speed = ball_speed if ball_speed is not None else 300.0
    max_attempts_per_ball = 100
    
    # 色相計算を事前実行
    hue_values = [i / num_balls for i in range(num_balls)]
    np.random.shuffle(hue_values)
    
    # 配置範囲を事前計算
    min_pos = BALL_RADIUS
    max_x = width - BALL_RADIUS
    max_y = height - BALL_RADIUS
    
    for i in range(num_balls):
        ball_placed = False
        hue = hue_values[i]
        
        # RGB色を事前計算
        rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        fill_color = tuple(int(c * 255) for c in rgb_float)
        
        for attempt in range(max_attempts_per_ball):
            x = np.random.randint(min_pos, max_x)
            y = np.random.randint(min_pos, max_y)
            
            # 重なりチェック（距離の二乗で比較して平方根計算を回避）
            min_dist_sq = (BALL_RADIUS * 2) ** 2
            is_valid = True
            
            for existing_ball in balls:
                dx = x - existing_ball.x
                dy = y - existing_ball.y
                dist_sq = dx * dx + dy * dy
                
                if dist_sq <= min_dist_sq:
                    is_valid = False
                    break
            
            if is_valid:
                angle = np.random.rand() * TWO_PI
                balls.append(Ball(x, y, BALL_RADIUS, speed, angle, fill_color))
                ball_placed = True
                break
                
        if not ball_placed:
            print(f"Could not place ball {len(balls)+1}")

    return balls

def _handle_ball_collisions_optimized(balls: List[Ball], frame_count: int):
    """衝突処理（計算最適化版）"""
    # フレームスキップで計算負荷削減（見た目への影響は最小）
    if frame_count % COLLISION_CHECK_SKIP != 0:
        return
    
    num_balls = len(balls)
    radii_sum = BALL_RADIUS * 2  # 全ボール同サイズなので事前計算
    radii_sum_sq = radii_sum * radii_sum
    min_dist_sq = (radii_sum * 0.05) ** 2
    
    for i in range(num_balls):
        ball1 = balls[i]
        for j in range(i + 1, num_balls):
            ball2 = balls[j]
            
            # 距離計算（平方根回避）
            dx = ball1.x - ball2.x
            dy = ball1.y - ball2.y
            dist_sq = dx * dx + dy * dy
            
            # 早期リターン（衝突していない）
            if dist_sq >= radii_sum_sq:
                continue
            
            # 極近距離処理
            if dist_sq <= min_dist_sq:
                # ランダム分離（三角関数キャッシュ使用）
                angle = np.random.rand() * TWO_PI
                cos_a, sin_a = fast_cos_sin(angle)
                sep_dist = radii_sum * 0.55
                
                sep_x = cos_a * sep_dist * 0.5
                sep_y = sin_a * sep_dist * 0.5
                
                ball1.x += sep_x
                ball1.y += sep_y
                ball2.x -= sep_x
                ball2.y -= sep_y
                
                ball1._bbox_dirty = True
                ball2._bbox_dirty = True
                continue
            
            # 通常の衝突処理
            # 平方根計算を1回のみ実行
            dist = fast_sqrt(dist_sq)
            inv_dist = 1.0 / dist  # 除算を1回のみ
            nx = dx * inv_dist
            ny = dy * inv_dist
            
            # 相対速度計算
            rel_vx = ball1.speed_x - ball2.speed_x
            rel_vy = ball1.speed_y - ball2.speed_y
            rel_v_normal = rel_vx * nx + rel_vy * ny
            
            # 接近している場合のみ処理
            if rel_v_normal < 0:
                # 接線ベクトル
                tx = -ny
                ty = nx
                
                # 速度成分分解
                v1n = ball1.speed_x * nx + ball1.speed_y * ny
                v1t = ball1.speed_x * tx + ball1.speed_y * ty
                v2n = ball2.speed_x * nx + ball2.speed_y * ny
                v2t = ball2.speed_x * tx + ball2.speed_y * ty
                
                # 速度交換
                new_v1x = v2n * nx + v1t * tx
                new_v1y = v2n * ny + v1t * ty
                new_v2x = v1n * nx + v2t * tx
                new_v2y = v1n * ny + v2t * ty
                
                # 速度上限チェック（二乗比較で高速化）
                if (new_v1x * new_v1x + new_v1y * new_v1y <= MAX_SPEED_SQ and
                    new_v2x * new_v2x + new_v2y * new_v2y <= MAX_SPEED_SQ):
                    
                    ball1.speed_x = new_v1x
                    ball1.speed_y = new_v1y
                    ball2.speed_x = new_v2x
                    ball2.speed_y = new_v2y
                    
                    # 速度の二乗を更新
                    ball1.speed_sq = new_v1x * new_v1x + new_v1y * new_v1y
                    ball2.speed_sq = new_v2x * new_v2x + new_v2y * new_v2y
            
            # 位置補正
            overlap = radii_sum - dist
            if overlap > 0:
                correction = overlap * 0.4  # 補正係数
                correction_x = correction * nx
                correction_y = correction * ny
                
                ball1.x += correction_x
                ball1.y += correction_y
                ball2.x -= correction_x
                ball2.y -= correction_y
                
                ball1._bbox_dirty = True
                ball2._bbox_dirty = True

def _main_loop_optimized(lcd: ST7789V, background: Image.Image, balls: List[Ball], 
                        fps_counter: FpsCounter, font, target_fps: float):
    """メインループ（計算最適化版）"""
    target_duration = 1.0 / target_fps
    last_frame_time = time.time()
    frame_count = 0
    
    # 時間制限を事前計算
    max_delta_t = target_duration * 2.5
    min_delta_t = target_duration * 0.2
    inv_substeps = 1.0 / PHYSICS_SUBSTEPS  # 除算を事前計算

    # 再利用オブジェクト
    hud_layer = Image.new("RGBA", (lcd.width, lcd.height), (0, 0, 0, 0))
    hud_draw = ImageDraw.Draw(hud_layer)
    prev_fps_bbox = None
    
    # 画面サイズを事前取得
    screen_width = lcd.width
    screen_height = lcd.height

    while True:
        frame_count += 1
        current_time = time.time()
        actual_delta_t = current_time - last_frame_time
        
        # 時間クランプ（min/max関数の組み合わせ最適化）
        if actual_delta_t > max_delta_t:
            delta_t = max_delta_t
        elif actual_delta_t < min_delta_t:
            delta_t = min_delta_t
        else:
            delta_t = actual_delta_t
            
        last_frame_time = current_time
        sub_delta_t = delta_t * inv_substeps

        # --- 物理更新ループ ---
        for _ in range(PHYSICS_SUBSTEPS):
            # 位置更新（ループ最適化）
            for ball in balls:
                ball.update_position(sub_delta_t, screen_width, screen_height)
            
            # 衝突処理
            _handle_ball_collisions_optimized(balls, frame_count)

        # --- 描画処理 ---
        new_frame_image = background.copy()
        draw = ImageDraw.Draw(new_frame_image)
        dirty_regions = []

        # ボール描画
        for ball in balls:
            prev_bbox = ball.prev_bbox
            curr_bbox = ball.get_bbox()
            dirty_region = RegionOptimizer._merge_two(prev_bbox, curr_bbox) if prev_bbox else curr_bbox
            
            if dirty_region:
                expanded_dirty_region = (dirty_region[0] - 1, dirty_region[1] - 1, dirty_region[2] + 1, dirty_region[3] + 1)
                dirty_regions.append(RegionOptimizer.clamp_region(expanded_dirty_region, screen_width, screen_height))
            
            ball.draw(draw)
            ball.prev_bbox = curr_bbox

        # FPS表示更新
        if fps_counter.update():
            if prev_fps_bbox:
                expanded_prev_fps_bbox = (
                    prev_fps_bbox[0] - 4, prev_fps_bbox[1] - 6,
                    prev_fps_bbox[2] + 4, prev_fps_bbox[3] + 6
                )
                hud_draw.rectangle(expanded_prev_fps_bbox, fill=(0, 0, 0, 0))

            current_fps_bbox = draw_text(hud_draw, fps_counter.fps_text, font, 
                                      x='left', y='top',
                                      width=screen_width, height=screen_height, 
                                      color=TEXT_COLOR)
            
            if current_fps_bbox:
                expanded_current_fps_bbox = (
                    current_fps_bbox[0] - 4, current_fps_bbox[1] - 6,
                    current_fps_bbox[2] + 4, current_fps_bbox[3] + 6
                )
                dirty_regions.append(expanded_current_fps_bbox)
                prev_fps_bbox = current_fps_bbox

        # 画面合成と表示
        frame_rgba = new_frame_image.convert("RGBA")
        frame_rgba.alpha_composite(hud_layer)
        final_frame = frame_rgba.convert("RGB")

        if dirty_regions:
            optimized = RegionOptimizer.merge_regions(dirty_regions, max_regions=8)
            for r in optimized:
                lcd.display_region(final_frame, *r)

        # フレームレート制御
        next_frame_time = last_frame_time + target_duration
        sleep_duration = next_frame_time - time.time()
        
        if 0 < sleep_duration <= target_duration:
            time.sleep(sleep_duration)

def draw_text(
        draw: ImageDraw.ImageDraw,
        text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, 
        x, y, 
        width: int,
        height: int,
        color,
        padding: int = 5
):
    """
    Draws text on a PIL ImageDraw object with flexible positioning.
    It pre-renders the text to accurately determine its bounding box.
    """
    # Get the actual bounding box of the text using ImageDraw.textbbox
    try:
        actual_bbox = draw.textbbox((0, 0), text, font=font)
    except (TypeError, ValueError):
        # Handle cases where textbbox might not be available or fails
        return (0, 0, 0, 0)

    if actual_bbox is None:
        return (0, 0, 0, 0)

    text_width = actual_bbox[2] - actual_bbox[0]
    text_height = actual_bbox[3] - actual_bbox[1]

    # Calculate X coordinate
    if isinstance(x, str):
        if x == 'left':
            final_x = padding - actual_bbox[0]
        elif x == 'center':
            final_x = (width - text_width) // 2 - actual_bbox[0]
        elif x == 'right':
            final_x = width - text_width - padding - actual_bbox[0]
        else:
            final_x = padding - actual_bbox[0]
    else:
        final_x = x - actual_bbox[0]

    # Calculate Y coordinate
    if isinstance(y, str):
        if y == 'top':
            final_y = padding - actual_bbox[1]
        elif y == 'center':
            final_y = (height - text_height) // 2 - actual_bbox[1]
        elif y == 'bottom':
            final_y = height - text_height - padding - actual_bbox[1]
        else:
            final_y = padding - actual_bbox[1]
    else:
        final_y = y - actual_bbox[1]
        
    final_pos = (final_x, final_y)
    
    draw.text(final_pos, text, font=font, fill=color)
    
    return (
        int(final_pos[0] + actual_bbox[0]),
        int(final_pos[1] + actual_bbox[1]),
        int(final_pos[0] + actual_bbox[2] + 1),
        int(final_pos[1] + actual_bbox[3] + 1)
    )

# --- CLIコマンド ---
@click.command("ball_anime")
@click.option('--spi-mhz', "-z", default=SPI_SPEED_HZ / 1_000_000, type=float, help='SPI speed in MHz', show_default=True)
@click.option('--fps', "-f", default=TARGET_FPS, type=float, help='Target frames per second', show_default=True)
@click.option('--num-balls', "-n", default=3, type=int, help='Number of balls to display', show_default=True)
@click.option('--ball-speed', "-b", default=None, type=float, help='Absolute speed of balls (pixels/second).')
def ball_anime(spi_mhz: float, fps: float, num_balls: int, ball_speed: float):
    """物理ベースのアニメーションデモを実行する（計算最適化版）。"""
    print(f"Running at {fps} FPS... Press Ctrl+C to exit.")

    try:
        with ST7789V(speed_hz=int(spi_mhz * 1_000_000)) as lcd:
            # Load the bundled font
            font_large: ImageFont.FreeTypeFont | ImageFont.ImageFont
            font_small: ImageFont.FreeTypeFont | ImageFont.ImageFont
            try:
                with importlib.resources.path('pi0disp.fonts', 'NotoSans-Regular.ttf') as font_path:
                    font_large = ImageFont.truetype(str(font_path), 40)
                    font_small = ImageFont.truetype(str(font_path), 24)
            except (IOError, FileNotFoundError) as e:
                print(f"Could not load bundled font: {e}")
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # 背景画像を生成（元の処理維持）
            background_image = Image.new("RGB", (lcd.width, lcd.height))
            draw = ImageDraw.Draw(background_image)
            for y in range(lcd.height):
                color = (y % 256, (y*2) % 256, (y*3) % 256)
                draw.line((0, y, lcd.width, y), fill=color)

            # 静的テキスト（IPアドレスなど）を描画
            draw_text(draw, "IP: N/A", font_small, 
                      x='center', y='bottom',
                      width=lcd.width, height=lcd.height, 
                      color=TEXT_COLOR)
            
            lcd.display(background_image)

            # オブジェクトを初期化
            balls = _initialize_balls_optimized(num_balls, lcd.width, lcd.height, ball_speed)
            fps_counter = FpsCounter()
            
            # メインループを開始
            _main_loop_optimized(lcd, background_image, balls, fps_counter, font_large, fps)

    except KeyboardInterrupt:
        print("\nExiting.\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)
