# -*- coding: utf-8 -*-
"""
performance_core.py - パフォーマンス最適化のための汎用モジュール

このモジュールは、Raspberry Pi Zero 2Wのようなリソースが限られた環境で、
パフォーマンスを最適化するために設計された再利用可能なクラス群を提供します。
各クラスは特定の最適化手法に焦点を当てています。
"""
import time
import threading
from collections import deque
from typing import List, Tuple, Callable, Any, Dict

import numpy as np

# --- 最適化クラス群 ---

class MemoryPool:
    """
    再利用可能なバッファのプールを管理し、頻繁に割り当てられるメモリブロックを
    再利用することで、ガベージコレクション（不要なメモリを自動で解放する処理）の
    オーバーヘッド（余分な処理時間）を削減します。
    """
    def __init__(
            self,
            max_pools: int = 8,
            buffer_factory: Callable[[int], Any] = bytearray
    ):
        """
        メモリプールを初期化します。

        Args:
            max_pools (int): 各バッファサイズごとにプールに保持するバッファの
                             最大数。例えば、サイズ100のバッファを最大8個まで
                             プールに保持します。
            buffer_factory (Callable): 新しいバッファを作成するための関数。
                               例: `bytearray` (バイト列を扱うためのバッファ)
        """
        self._pools: Dict[int, deque] = {}  # バッファサイズごとに分類されたプール
        self._max_pools = max_pools
        self._buffer_factory = buffer_factory
        self._lock = threading.Lock()  # スレッドセーフにするためのロック
        # （複数の処理が同時にメモリプールを操作しないようにする）
        self._stats = {'hits': 0, 'misses': 0, 'created': 0}  # 統計情報
        # （ヒット数、ミス数、作成数）

    def get_buffer(self, size: int) -> Any:
        """
        指定されたサイズ以上のバッファをプールから取得します。
        適切なバッファが見つからない場合は、新しいバッファを作成します。

        Args:
            size (int): 必要な最小バッファサイズ。

        Returns:
            バッファオブジェクト。
        """
        with self._lock:  # ロックを取得し、他のスレッドからの
            # アクセスを一時的にブロック
            # 指定されたサイズ以上の、利用可能な最小のバッファを探します
            for pool_size in sorted(self._pools.keys()):
                if pool_size >= size and self._pools[pool_size]:
                    self._stats['hits'] += 1  # プールから取得できたので
                    # ヒット数を増やす
                    return self._pools[pool_size].pop()  # プールからバッファを
                    # 取り出して返す

            # 適切なバッファが見つからない場合、新しいバッファを作成します
            self._stats['misses'] += 1  # プールから取得できなかったので
            # ミス数を増やす
            self._stats['created'] += 1  # 新しく作成したので作成数を増やす
            return self._buffer_factory(size)  # バッファ生成関数を使って
            # 新しいバッファを返す

    def return_buffer(self, buffer: Any):
        """
        バッファをプールに戻し、将来の再利用に備えます。

        Args:
            buffer: プールに戻すバッファオブジェクト。
        """
        size = len(buffer)  # バッファのサイズを取得
        with self._lock:  # ロックを取得
            if size not in self._pools:
                # そのサイズのプールがまだ存在しない場合、新しく作成
                self._pools[size] = deque(maxlen=self._max_pools)

            if len(self._pools[size]) < self._max_pools:
                # プールに空きがある場合、バッファを追加
                self._pools[size].append(buffer)

    def get_stats(self) -> dict:
        """プール使用状況に関する統計情報（ヒット数、ミス数など）を返します。
        """
        with self._lock:  # ロックを取得
            return self._stats.copy()  # 統計情報のコピーを返す

    def clear(self):
        """すべてのプールを空にし、統計情報をリセットします。"""
        with self._lock:  # ロックを取得
            self._pools.clear()  # すべてのプールをクリア
            self._stats = {'hits': 0, 'misses': 0, 'created': 0}  # 統計情報をリセット


class LookupTableCache:
    """
    事前に計算されたルックアップテーブル（LUTs: LookUp Tables）をキャッシュする
    シングルトン（プログラム全体で1つしか存在しない）クラスです。
    色変換やガンマ補正のような、計算コストの高い処理を高速化するために使用されます。
    """
    _instances: Dict[str, 'LookupTableCache'] = {}
    _lock = threading.Lock()  # スレッドセーフにするためのロック

    @classmethod
    def get_instance(cls, table_type: str) -> 'LookupTableCache':
        """
        指定されたテーブルタイプに対応するシングルトンインスタンスへのアクセスを
        提供します。もしそのタイプのインスタンスがまだ作成されていなければ、
        新しく作成します。
        """
        with cls._lock:  # ロックを取得
            if table_type not in cls._instances:
                cls._instances[table_type] = cls(table_type)
            return cls._instances[table_type]

    def __init__(self, table_type: str):
        self.table_type = table_type  # テーブルのタイプ
        # （例: 'rgb565', 'gamma'）
        self._tables: Dict[str, np.ndarray] = {} # キャッシュされたテーブルを保持
        self._generators: Dict[str, Callable[..., Dict[str, np.ndarray]]] = {
            'rgb565': self._generate_rgb565_tables,  # RGB565変換テーブルの生成関数
            'gamma': self._generate_gamma_tables,    # ガンマ補正テーブルの生成関数
        }

    def _generate_rgb565_tables(self) -> Dict[str, np.ndarray]:
        """
        高速なRGBからRGB565への変換のためのLUTs（ルックアップテーブル）を生成します。
        RGB565は、赤5ビット、緑6ビット、青5ビットで色を表現する形式で、
        メモリ使用量を抑えつつ色を表現するのに使われます。
        """
        return {
            'r_shift': (np.arange(256, dtype=np.uint16) >> 3) << 11,  # 赤成分のシフト値
            'g_shift': (np.arange(256, dtype=np.uint16) >> 2) << 5,   # 緑成分のシフト値
            'b_shift': (np.arange(256, dtype=np.uint16) >> 3),        # 青成分のシフト値
        }

    def _generate_gamma_tables(
            self,
            gamma: float = 2.2
    ) -> Dict[str, np.ndarray]:
        """
        ガンマ補正のためのLUTを生成します。
        ガンマ補正は、画像の明るさやコントラストを調整するために使われる技術です。
        人間の目の明るさに対する感度に合わせて画像を調整します。
        """
        table = np.array([
            int(255 * ((i / 255.0) ** gamma)) for i in range(256)
        ], dtype=np.uint8)  # 0-255の各値に対してガンマ補正を適用した
        # テーブルを作成
        return {'gamma_table': table}

    def get_table(self, table_name: str, **kwargs: Any) -> np.ndarray:
        """
        テーブルを取得します。もしキャッシュに存在しない場合は、新しく生成して
        キャッシュします。
        
        Args:
            table_name (str): 取得するテーブルの名前。
            **kwargs: テーブル生成関数に渡すパラメータ（例: `gamma=2.2`）。
                 これにより、同じ種類のテーブルでも異なる設定で生成できます。

        Returns:
            要求されたルックアップテーブル（通常はNumPy配列）。
        """
        # キャッシュキーを作成（テーブル名とパラメータのハッシュ値で一意に識別）
        cache_key = (
            f"{table_name}_{hash(str(sorted(kwargs.items())))}"
        )  # キャッシュキーを作成
        # （テーブル名とパラメータのハッシュ値で一意に識別）
        if cache_key not in self._tables:  # キャッシュに存在しない場合
            if self.table_type not in self._generators:
                raise ValueError(f"不明なテーブルタイプ: {self.table_type}")
            
            # テーブル生成関数を呼び出してテーブルを生成
            generated = self._generators[self.table_type](**kwargs)
            if table_name not in generated:
                raise KeyError(
                    f"Table '{table_name}' not found for type '{self.table_type}'"
                )
            
            self._tables[cache_key] = generated[table_name]
        
        return self._tables[cache_key]


class RegionOptimizer:
    """
    Optimizes lists of rectangular regions ("dirty regions") by merging
    overlapping or nearby rectangles to reduce the number of drawing operations.
    """
    @staticmethod
    def merge_regions(
            regions: List[Tuple[int, int, int, int]], 
            max_regions: int = 8, 
            merge_threshold: int = 50
    ) -> List[Tuple[int, int, int, int]]:
        """
        Merges a list of regions into a smaller, optimized list.

        Args:
            regions: A list of tuples, where each tuple is (x0, y0, x1, y1).
            max_regions: The maximum number of regions to return.
            merge_threshold: The maximum distance between regions to be considered for mering.

        Returns:
            An optimized list of merged regions.
        """
        if len(regions) <= 1:
            return regions

        valid_regions = [r for r in regions if r and r[2] > r[0] and r[3] > r[1]]
        if not valid_regions:
            return []

        # Start with the smallest regions to encourage merging
        merged: List[Tuple[int, int, int, int]] = []
        sorted_regions = sorted(
            valid_regions, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])
        )

        while sorted_regions:
            current = sorted_regions.pop(0)
            was_merged = False
            for i, existing in enumerate(merged):
                if RegionOptimizer._should_merge(
                        current, existing, merge_threshold
                ):
                    merged[i] = RegionOptimizer._merge_two(current, existing)
                    was_merged = True
                    break
            if not was_merged:
                merged.append(current)

        # If we still have too many regions, perform more aggressive merging
        while len(merged) > max_regions:
            # Find the pair of regions that results in the smallest new area when merged
            min_area_increase = float('inf')
            best_pair_to_merge = (0, 1)
            for i in range(len(merged)):
                for j in range(i + 1, len(merged)):
                    r1, r2 = merged[i], merged[j]
                    merged_bbox = RegionOptimizer._merge_two(r1, r2)
                    area_increase = (
                        (merged_bbox[2] - merged_bbox[0]) * \
                        (merged_bbox[3] - merged_bbox[1])
                    ) - (
                        (r1[2] - r1[0]) * (r1[3] - r1[1])
                    ) - (
                        (r2[2] - r2[0]) * (r2[3] - r2[1])
                    )
                    if area_increase < min_area_increase:
                        min_area_increase = area_increase
                        best_pair_to_merge = (i, j)
            
            i, j = sorted(best_pair_to_merge, reverse=True)
            merged_region = RegionOptimizer._merge_two(merged[i], merged[j])
            merged.pop(j)
            merged.pop(i)
            merged.append(merged_region)

        return merged

    @staticmethod
    def _should_merge(
            r1: Tuple[int, int, int, int],
            r2: Tuple[int, int, int, int],
            threshold: int
    ) -> bool:
        """Determines if two regions are close enough to be merged."""
        # Check for overlap or proximity within the threshold
        x_overlap = (r1[0] <= r2[2] + threshold) and (r1[2] >= r2[0] - threshold)
        y_overlap = (r1[1] <= r2[3] + threshold) and (r1[3] >= r2[1] - threshold)
        return x_overlap and y_overlap

    @staticmethod
    def _merge_two(
            r1: Tuple[int, int, int, int],
            r2: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """Merges two regions into their bounding box."""
        return (
            min(r1[0], r2[0]),
            min(r1[1], r2[1]),
            max(r1[2], r2[2]),
            max(r1[3], r2[3])
        )

    @staticmethod
    def clamp_region(
            region: Tuple[int, int, int, int],
            width: int,
            height: int
    ) -> Tuple[int, int, int, int]:
        """Clamps a region's coordinates to be within screen boundaries."""
        return (
            max(0, region[0]),
            max(0, region[1]),
            min(width, region[2]),
            min(height, region[3])
        )


class PerformanceMonitor:
    """
    Tracks performance metrics like FPS and processing time.
    """
    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: The number of frames to average over for statistics.
        """
        self.window_size = window_size
        self._frame_times: deque[float] = deque(maxlen=window_size)
        self._process_times: deque[float] = deque(maxlen=window_size)
        self._last_frame_time = time.monotonic()

    def frame_start(self) -> float:
        """Marks the beginning of a new frame."""
        now = time.monotonic()
        delta = now - self._last_frame_time
        self._frame_times.append(delta)
        self._last_frame_time = now
        return now

    def frame_end(self, start_time: float):
        """Marks the end of a frame's processing."""
        self._process_times.append(time.monotonic() - start_time)

    def get_fps(self) -> float:
        """Calculates the current average frames per second."""
        if not self._frame_times:
            return 0.0
        return 1.0 / (sum(self._frame_times) / len(self._frame_times))

    def get_stats(self) -> dict:
        """Returns a dictionary of all current performance statistics."""
        return {
            'fps': self.get_fps(),
            'avg_process_time_ms': (
                sum(self._process_times) / len(self._process_times) * 1000
            ) if self._process_times else 0,
        }


class AdaptiveChunking:
    """
    Dynamically adjusts data transfer chunk sizes based on performance to
    optimize throughput.
    """
    def __init__(
            self,
            initial_size: int = 4096,
            min_size: int = 1024,
            max_size: int = 16384
    ):
        self.chunk_size = initial_size
        self.min_size = min_size
        self.max_size = max_size
        self._throughputs: deque[float] = deque(maxlen=20)
        self._last_adjustment = time.monotonic()

    def record_transfer(self, data_size: int, transfer_time: float):
        """Records a data transfer to adjust future chunk sizes."""
        if transfer_time > 0:
            self._throughputs.append(data_size / transfer_time)
        
        if time.monotonic() - self._last_adjustment > 1.0 and len(self._throughputs) >= 10:
            self._adjust_chunk_size()

    def _adjust_chunk_size(self):
        """Adjusts chunk size based on recent throughput."""
        if len(self._throughputs) < 10:
            return

        recent_avg = sum(list(self._throughputs)[-10:]) / 10
        older_avg = sum(list(self._throughputs)[:-10]) / 10 \
            if len(self._throughputs) > 10 else recent_avg

        if recent_avg > older_avg * 1.05:  # Throughput is improving
            self.chunk_size = min(self.max_size, int(self.chunk_size * 1.2))
        elif recent_avg < older_avg * 0.95:  # Throughput is degrading
            self.chunk_size = max(self.min_size, int(self.chunk_size * 0.8))
        
        self._last_adjustment = time.monotonic()

    def get_chunk_size(self) -> int:
        """Returns the current optimal chunk size."""
        return self.chunk_size


class ColorConverter:
    """
    Provides fast color space conversion utilities using cached lookup tables.
    """
    def __init__(self):
        self._rgb565_cache = LookupTableCache.get_instance('rgb565')
        self._gamma_cache = LookupTableCache.get_instance('gamma')

    def rgb_to_rgb565_bytes(self, rgb_array: np.ndarray) -> bytes:
        """
        Converts an RGB NumPy array to a big-endian RGB565 byte string.

        Args:
            rgb_array: A NumPy array with shape (height, width, 3).

        Returns:
            A byte string containing the RGB565 pixel data.
        """
        r = self._rgb565_cache.get_table('r_shift')[rgb_array[:, :, 0]]
        g = self._rgb565_cache.get_table('g_shift')[rgb_array[:, :, 1]]
        b = self._rgb565_cache.get_table('b_shift')[rgb_array[:, :, 2]]
        
        rgb565 = r | g | b
        return rgb565.astype('>u2').tobytes()

    def apply_gamma(self, rgb_array: np.ndarray, gamma: float = 2.2) -> np.ndarray:
        """Applies gamma correction to an RGB NumPy array."""
        gamma_table = self._gamma_cache.get_table('gamma_table', gamma=gamma)
        return gamma_table[rgb_array]

# --- Factory Function ---

def create_optimizer_pack() -> dict:
    """
    Creates a standard dictionary of optimizer instances for convenience.

    Returns:
        A dictionary containing instances of the core optimization classes.
    """
    return {
        'memory_pool': MemoryPool(),
        'region_optimizer': RegionOptimizer(),
        'performance_monitor': PerformanceMonitor(),
        'adaptive_chunking': AdaptiveChunking(),
        'color_converter': ColorConverter(),
    }
