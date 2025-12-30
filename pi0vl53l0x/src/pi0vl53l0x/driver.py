#
# (c) 2025 Yoichi Tanibayashi
#
"""Python driver for the VL53L0X distance sensor.

V5 Changes:
- Implements Sensor ABC from ninja_utils.interfaces
- Added get_data() method for standardized output
"""

import time
import pigpio
import numpy as np
from pathlib import Path
from typing import Any

from ninja_utils import Sensor, get_logger
from .config_manager import load_config
from . import constants as C


class VL53L0X(Sensor):
    """
    VL53L0X distance sensor driver implementing the Sensor interface.
    
    This driver provides distance measurements using the VL53L0X Time-of-Flight
    laser ranging sensor via I2C communication.
    """

    def __init__(self, pi: pigpio.pi, i2c_bus: int = 1, i2c_address: int = 0x29, debug: bool = False, config_file_path: Path | None = None):
        """
        Initialize the VL53L0X sensor.
        """
        self.pi = pi
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.__log = get_logger(self.__class__.__name__)
        self.__log.debug(
            "Open VL53L0X at i2c_bus=%s, i2c_address=%s",
            self.i2c_bus,
            hex(self.i2c_address),
        )
        self.handle = self.pi.i2c_open(self.i2c_bus, self.i2c_address)
        self.__log.debug("handle=%s", self.handle)
        self.offset_mm = 0

        # Load offset from config file if provided
        if config_file_path:
            config = load_config(config_file_path)
            if "offset_mm" in config:
                self.set_offset(config["offset_mm"])
                self.__log.debug("Loaded offset_mm=%s from %s", self.offset_mm, config_file_path)

        self.initialize()

    def __enter__(self) -> "VL53L0X":
        """
        コンテキストマネージャーとして使用する際のエントリポイント。
        """
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: type | None
    ) -> None:
        """
        コンテキストマネージャーとして使用する際の終了ポイント。
        I2C接続を閉じます。
        """
        self.__log.debug(
            "exc_type=%s, exc_val=%s, exc_tb=%s",
            exc_type, exc_val, exc_tb
        )
        self.close()

    def _set_i2c_registers_initial_values(self) -> None:
        """
        I2Cレジスタの初期値を設定します。
        """
        # I2C標準モードを設定
        self.write_byte(C.I2C_STANDARD_MODE, C.VALUE_00)

        # VL53L0Xデータシートに従って各種レジスタを初期化
        self.write_byte(C.REG_80, C.VALUE_01)
        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_00, C.VALUE_00)

        # REG_91からストップ変数を読み取る
        self.stop_variable = self.read_byte(C.REG_91)

        # レジスタをデフォルトの電源投入時の値に復元
        self.write_byte(C.REG_00, C.VALUE_01)
        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_80, C.VALUE_00)

        # I/O 2.8V エクスパンダ（推奨：一度だけ）
        try:
            self.write_byte(C.VHV_CFG_PAD_SCL_SDA_EXTSUP_HV, (self.read_byte(C.VHV_CFG_PAD_SCL_SDA_EXTSUP_HV) | 0x01))
        except Exception:
            pass

    def _configure_signal_rate_limit(self) -> None:
        """
        信号レート制限を設定します。
        """
        # MSRC_CONFIG_CONTROLレジスタのSIGNAL_RATE_MSRC (ビット1) と
        # SIGNAL_RATE_PRE_RANGE (ビット4) の制限チェックを無効にする。
        current_msrc_config = self.read_byte(C.MSRC_CONFIG_CONTROL)
        self.write_byte(C.MSRC_CONFIG_CONTROL, (current_msrc_config | C.VALUE_12))

        # 最終レンジ信号レート制限を0.25 MCPS (百万カウント/秒) に設定する。
        # この値は0.25 * 128 = 32。
        self.write_word(C.FINAL_RANGE_CFG_MIN_COUNT_RATE_RTN_LIMIT, C.VALUE_32)

        # SYSTEM_SEQUENCE_CONFIGを設定して、構成のためにすべてのシーケンスを有効にする。
        self.write_byte(C.SYSTEM_SEQUENCE_CONFIG, C.VALUE_FF)

    def _setup_spad_info(self) -> None:
        """
        SPAD情報を設定します。
        """
        spad_count, spad_is_aperture = self._get_spad_info()

        # The SPAD map (RefGoodSpadMap) is read by VL53L0X_get_info_from_device()
        # in the API, but the same data seems to be written to
        # GLOBAL_CONFIG_SPAD_ENABLES_REF_0 through GLOBAL_CONFIG_SPAD_ENABLES_REF_5,
        # so read it from there.
        ref_spad_map = self.read_block(C.GLOBAL_CFG_SPAD_ENABLES_REF_0, 6)

        # Configure dynamic SPAD settings
        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.DYN_SPAD_REF_EN_START_OFFSET, C.VALUE_00)
        self.write_byte(
            C.DYN_SPAD_NUM_REQUESTED_REF_SPAD, C.SPAD_NUM_REQUESTED_REF
        )
        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.GLOBAL_CFG_REF_EN_START_SELECT, C.VALUE_B4)

        first_spad_to_enable = C.SPAD_START_INDEX_APERTURE if spad_is_aperture else 0
        spads_enabled = 0

        # Enable SPADs based on count and aperture information
        for i in range(C.SPAD_TOTAL_COUNT):
            if i < first_spad_to_enable or spads_enabled == spad_count:
                # This bit is lower than the first one to enable, or
                # (spad_count) bits have already been enabled, so zero this bit
                ref_spad_map[i // C.SPAD_MAP_BITS_PER_BYTE] &= ~(1 << (i % C.SPAD_MAP_BITS_PER_BYTE))
            elif (ref_spad_map[i // C.SPAD_MAP_BITS_PER_BYTE] >> (i % C.SPAD_MAP_BITS_PER_BYTE)) & 0x1:
                spads_enabled += 1

        self.write_block(C.GLOBAL_CFG_SPAD_ENABLES_REF_0, ref_spad_map)

        # Further SPAD configuration registers
        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_00, C.VALUE_00)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_09, C.VALUE_00)
        self.write_byte(C.REG_10, C.VALUE_00)
        self.write_byte(C.REG_11, C.VALUE_00)

        self.write_byte(C.REG_24, C.VALUE_01)
        self.write_byte(C.REG_25, C.VALUE_FF)
        self.write_byte(C.REG_75, C.VALUE_00)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_4E, C.SPAD_NUM_REQUESTED_REF)
        self.write_byte(C.REG_48, C.VALUE_00)
        self.write_byte(C.REG_30, C.VALUE_20)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_30, C.VALUE_09)
        self.write_byte(C.REG_54, C.VALUE_00)
        self.write_byte(C.REG_31, C.VALUE_04)
        self.write_byte(C.REG_32, C.VALUE_03)
        self.write_byte(C.REG_40, C.VALUE_83)
        self.write_byte(C.REG_46, C.VALUE_25)
        self.write_byte(C.REG_60, C.VALUE_00)
        self.write_byte(C.REG_27, C.VALUE_00)
        self.write_byte(C.REG_50, C.VALUE_06)
        self.write_byte(C.REG_51, C.VALUE_00)
        self.write_byte(C.REG_52, C.VALUE_96)
        self.write_byte(C.REG_56, C.VALUE_08)
        self.write_byte(C.REG_57, C.VALUE_30)
        self.write_byte(C.REG_61, C.VALUE_00)
        self.write_byte(C.REG_62, C.VALUE_00)
        self.write_byte(C.REG_64, C.VALUE_00)
        self.write_byte(C.REG_65, C.VALUE_00)
        self.write_byte(C.REG_66, C.VALUE_A0)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_22, C.VALUE_32)
        self.write_byte(C.REG_47, C.VALUE_14)
        self.write_byte(C.REG_49, C.VALUE_FF)
        self.write_byte(C.REG_4A, C.VALUE_00)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_7A, C.VALUE_0A)
        self.write_byte(C.REG_7B, C.VALUE_00)
        self.write_byte(C.REG_78, C.VALUE_21)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_23, C.VALUE_34)
        self.write_byte(C.REG_42, C.VALUE_00)
        self.write_byte(C.REG_44, C.VALUE_FF)
        self.write_byte(C.REG_45, C.VALUE_26)
        self.write_byte(C.REG_46, C.VALUE_05)
        self.write_byte(C.REG_40, C.VALUE_40)
        self.write_byte(C.REG_0E, C.VALUE_06)
        self.write_byte(C.REG_20, C.VALUE_1A)
        self.write_byte(C.REG_43, C.VALUE_40)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_34, C.VALUE_03)
        self.write_byte(C.REG_35, C.VALUE_44)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_31, C.VALUE_04)
        self.write_byte(C.REG_4B, C.VALUE_09)
        self.write_byte(C.REG_4C, C.VALUE_05)
        self.write_byte(C.REG_4D, C.VALUE_04)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_44, C.VALUE_00)
        self.write_byte(C.REG_45, C.VALUE_20)
        self.write_byte(C.REG_47, C.VALUE_08)
        self.write_byte(C.REG_48, C.VALUE_28)
        self.write_byte(C.REG_67, C.VALUE_00)
        self.write_byte(C.REG_70, C.VALUE_04)
        self.write_byte(C.REG_71, C.VALUE_01)
        self.write_byte(C.REG_72, C.VALUE_FE)
        self.write_byte(C.REG_76, C.VALUE_00)
        self.write_byte(C.REG_77, C.VALUE_00)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_0D, C.VALUE_01)

        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_80, C.VALUE_01)
        self.write_byte(C.REG_01, C.VALUE_F8)

        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_8E, C.VALUE_01)
        self.write_byte(C.REG_00, C.VALUE_01)
        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_80, C.VALUE_00)

    def _configure_interrupt_gpio(self) -> None:
        """
        割り込みGPIOを設定します。
        """
        # 割り込み出力のためにGPIOを設定
        self.write_byte(C.SYSTEM_INTERRUPT_CONFIG_GPIO, C.GPIO_INTERRUPT_CONFIG)

        # GPIO_HV_MUX_ACTIVE_HIGHレジスタをアクティブローに設定
        current_gpio_hv_mux = self.read_byte(C.GPIO_HV_MUX_ACTIVE_HIGH)
        self.write_byte(C.GPIO_HV_MUX_ACTIVE_HIGH, (current_gpio_hv_mux & ~C.VALUE_10))

        # 割り込みをクリア
        self.write_byte(C.SYSTEM_INTERRUPT_CLEAR, C.VALUE_01)

    def _set_timing_budget_and_calibrations(self) -> None:
        """
        タイミングバジェットを設定し、キャリブレーションを実行します。
        """
        # 測定タイミングバジェットを取得して設定
        self.measurement_timing_budget_us = self.get_measurement_timing_budget()
        self.__log.debug(
            "measurement_timing_budget_us=%s",
            self.measurement_timing_budget_us
        )
        self.set_measurement_timing_budget(self.measurement_timing_budget_us)

        # 以前のシーケンス設定を復元し、再度タイミングバジェットを設定
        self.write_byte(C.SYSTEM_SEQUENCE_CONFIG, C.VALUE_E8)
        self.set_measurement_timing_budget(self.measurement_timing_budget_us)

        # 単一のリファレンスキャリブレーションを実行
        self.write_byte(C.SYSTEM_SEQUENCE_CONFIG, C.VALUE_01)
        self.perform_single_ref_calibration(C.CALIBRATION_VALUE_40)

        self.write_byte(C.SYSTEM_SEQUENCE_CONFIG, C.VALUE_02)
        self.perform_single_ref_calibration(C.VALUE_00)

        # キャリブレーション後に以前のシーケンス設定を復元
        self.write_byte(C.SYSTEM_SEQUENCE_CONFIG, C.VALUE_E8)

    def check_connection(self) -> None:
        """
        Check if the sensor is connected by reading the Model ID.
        """
        try:
            model_id = self.read_byte(C.IDENTIFICATION_MODEL_ID)
            if model_id != 0xEE:
                raise ConnectionError(f"Invalid Model ID: {hex(model_id)}. Expected 0xEE.")
            self.__log.debug("Model ID verified: 0xEE")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to VL53L0X: {e}")

    def reset(self) -> None:
        """
        Perform a software reset of the sensor.
        """
        self.__log.debug("Resetting VL53L0X...")
        self.write_byte(C.SOFT_RESET_GO2_SOFT_RESET_N, C.VALUE_00)
        time.sleep(0.01)
        self.write_byte(C.SOFT_RESET_GO2_SOFT_RESET_N, C.VALUE_01)
        time.sleep(0.01)
        self.__log.debug("VL53L0X reset complete.")

    def initialize(self) -> None:
        """
        センサーを初期化します。
        """
        # Check connection first
        self.check_connection()

        # Software Reset
        self.reset()

        # I2Cレジスタの初期値を設定
        self._set_i2c_registers_initial_values()

        # 信号レート制限を設定
        self._configure_signal_rate_limit()

        # SPAD情報を設定
        self._setup_spad_info()

        # 割り込みGPIOを設定
        self._configure_interrupt_gpio()

        # タイミングバジェットを設定し、キャリブレーションを実行
        self._set_timing_budget_and_calibrations()

    def _get_spad_info(self) -> tuple[int, bool]:
        """
        SPAD情報を取得します。
        """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # SPAD情報取得のための初期レジスタ設定
                self.write_byte(C.REG_80, C.VALUE_01)
                self.write_byte(C.REG_FF, C.VALUE_01)
                self.write_byte(C.REG_00, C.VALUE_00)

                self.write_byte(C.REG_FF, C.VALUE_06)
                self.write_byte(C.VALUE_83, (self.read_byte(C.VALUE_83) | C.VALUE_04))
                self.write_byte(C.REG_FF, C.VALUE_07)
                self.write_byte(C.REG_81, C.VALUE_01)

                self.write_byte(C.REG_80, C.VALUE_01)

                # SPADキャリブレーションをトリガーし、完了を待つ
                self.write_byte(C.REG_94, C.VALUE_6B)
                self.write_byte(C.VALUE_83, C.VALUE_00)
                
                start = time.time()
                while self.read_byte(C.VALUE_83) == C.VALUE_00:
                    if time.time() - start > C.TIMEOUT_LIMIT:
                        raise Exception("Timeout waiting for SPAD info")
                self.write_byte(C.VALUE_83, C.VALUE_01)

                # SPADカウントとアパーチャ情報を読み取る
                tmp = self.read_byte(C.REG_92)
                count = tmp & C.SPAD_COUNT_MASK
                is_aperture = ((tmp & C.SPAD_APERTURE_BIT) != 0)

                # レジスタをデフォルト値に復元
                self.write_byte(C.REG_81, C.VALUE_00)
                self.write_byte(C.REG_FF, C.VALUE_06)
                self.write_byte(C.VALUE_83, (self.read_byte(C.VALUE_83) & ~C.VALUE_04))
                self.write_byte(C.REG_FF, C.VALUE_01)
                self.write_byte(C.REG_00, C.VALUE_01)

                self.write_byte(C.REG_FF, C.VALUE_00)
                self.write_byte(C.REG_80, C.VALUE_00)

                return count, is_aperture

            except Exception as e:
                self.__log.warning(f"SPAD info retrieval failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1)  # Brief pause before retry

    # 内部ヘルパー関数 (C++版 calcMacroPeriod の移植)
    def _calc_macro_period(self, vcsel_period_pclks: int) -> int:
        return ((2304 * vcsel_period_pclks * 1655) + 500) // 1000  # [ns]

    def _timeout_microseconds_to_mclks(
            self, timeout_us: int, vcsel_period_pclks: int
    ) -> int:
        # C++版 VL53L0X_calc_timeout_mclks 相当
        macro_period_ns = self._calc_macro_period(vcsel_period_pclks)
        # round up
        return (timeout_us * 1000 + (macro_period_ns // 2)) // macro_period_ns

    def _timeout_mclks_to_microseconds(self, timeout_mclks: int, vcsel_period_pclks: int) -> int:
        macro_period_ns = self._calc_macro_period(vcsel_period_pclks)
        return ((timeout_mclks * macro_period_ns) + 500) // 1000

    def _decode_timeout(self, reg_val: int) -> int:
        # C++: VL53L0X_decode_timeout()
        ls_byte = reg_val & 0xFF
        ms_byte = (reg_val >> 8) & 0xFF
        return ((ls_byte << ms_byte) + 1)

    def _encode_timeout(self, timeout_mclks: int) -> int:
        # C++: VL53L0X_encode_timeout()
        ls_byte = 0
        ms_byte = 0
        if timeout_mclks > 0:
            timeout_mclks -= 1
            while (timeout_mclks & 0xFFFFFF00) > 0:
                timeout_mclks >>= 1
                ms_byte += 1
            ls_byte = timeout_mclks & 0xFF
            return (ms_byte << 8) | ls_byte
        return 0

    def get_measurement_timing_budget(self) -> int:
        """
        現在の測定タイミングバジェットをマイクロ秒単位で返す
        """
        budget_us = 1910  # Start overhead
        enables = self.read_byte(C.SYSTEM_SEQUENCE_CONFIG)

        pre_range_us: int = 0
        pre_range_mclks: int | None = None

        # pre-range
        if (enables >> 6) & 0x01:
            pre_range_vcsel_period_pclks = self.read_byte(C.PRE_RANGE_CONFIG_VCSEL_PERIOD)
            pre_range_mclks = self._decode_timeout(
                self.read_word(C.PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI)
            )
            pre_range_us = self._timeout_mclks_to_microseconds(
                pre_range_mclks, pre_range_vcsel_period_pclks
            )
            budget_us += pre_range_us + 660  # overhead

        # final-range
        if (enables >> 7) & 0x01:
            final_range_vcsel_period_pclks = self.read_byte(C.FINAL_RANGE_CONFIG_VCSEL_PERIOD)
            final_range_mclks = self._decode_timeout(
                self.read_word(C.FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI)
            )

            if (enables >> 6) & 0x01:  # if pre-range enabled, subtract it
                if pre_range_mclks is not None:
                    final_range_mclks -= pre_range_mclks

            final_range_us = self._timeout_mclks_to_microseconds(
                final_range_mclks, final_range_vcsel_period_pclks
            )
            budget_us += final_range_us + 550  # overhead

        return budget_us

    def set_measurement_timing_budget(self, budget_us: int) -> bool:
        """
        測定タイミングバジェットを設定する
        """
        used_budget_us = 1320  # Start overhead
        enables = self.read_byte(C.SYSTEM_SEQUENCE_CONFIG)

        pre_range_us = 0
        pre_range_mclks = 0
        if (enables >> 6) & 0x01:
            pre_range_vcsel_period_pclks = self.read_byte(C.PRE_RANGE_CONFIG_VCSEL_PERIOD)
            pre_range_mclks = self._decode_timeout(
                self.read_word(C.PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI)
            )
            pre_range_us = self._timeout_mclks_to_microseconds(
                pre_range_mclks, pre_range_vcsel_period_pclks
            )
            used_budget_us += pre_range_us + 660

        if (enables >> 7) & 0x01:
            final_range_us = budget_us - used_budget_us - 550
            if final_range_us <= 0:
                raise ValueError("Requested timing budget too small")

            final_range_vcsel_period_pclks = self.read_byte(C.FINAL_RANGE_CONFIG_VCSEL_PERIOD)
            # ★ ここを μs→mclks に修正
            final_range_mclks = self._timeout_microseconds_to_mclks(
                final_range_us, final_range_vcsel_period_pclks
            )

            if (enables >> 6) & 0x01:
                final_range_mclks += pre_range_mclks

            self.write_word(
                C.FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI,
                self._encode_timeout(final_range_mclks),
            )
            return True
        return False

    def perform_single_ref_calibration(self, vhv_init_byte: int) -> None:
        self.write_byte(C.SYSRANGE_START, C.VALUE_01 | vhv_init_byte)
        start = time.time()
        # 2秒上限で待つ（環境により1秒だと落ちる場合がある）
        while (self.read_byte(C.RESULT_INTERRUPT_STATUS) & C.INTERRUPT_STATUS_MASK) == C.VALUE_00:
            if time.time() - start > 2.0:
                raise Exception("Timeout during ref calibration")
        self.write_byte(C.SYSTEM_INTERRUPT_CLEAR, C.VALUE_01)
        self.write_byte(C.SYSRANGE_START, C.VALUE_00)

    def get_range(self) -> int:
        """
        単一の測距測定を実行し、結果をmm単位で返します。
        """
        # stop_variable の復元シーケンス
        self.write_byte(C.REG_80, C.VALUE_01)
        self.write_byte(C.REG_FF, C.VALUE_01)
        self.write_byte(C.REG_00, C.VALUE_00)
        self.write_byte(C.REG_91, self.stop_variable)
        self.write_byte(C.REG_00, C.VALUE_01)
        self.write_byte(C.REG_FF, C.VALUE_00)
        self.write_byte(C.REG_80, C.VALUE_00)

        # 測定開始（シングルショット）
        self.write_byte(C.SYSRANGE_START, C.VALUE_01)

        # 予算に応じた実時間で待つ（最低1.0s）
        budget_s = getattr(self, "measurement_timing_budget_us", 33000) / 1_000_000.0
        timeout_s = max(1.0, budget_s + 0.1)

        # 割り込みステータス待ち（データ準備完了）
        start = time.time()
        while (self.read_byte(C.RESULT_INTERRUPT_STATUS) & C.INTERRUPT_STATUS_MASK) == C.VALUE_00:
            if time.time() - start > timeout_s:
                raise Exception("Timeout waiting for measurement ready")

        # 結果読み出し
        range_mm = self.read_word(C.RESULT_RANGE_STATUS + C.VALUE_0A)  # 0x14 + 0x0A

        # 割り込みクリア
        self.write_byte(C.SYSTEM_INTERRUPT_CLEAR, C.VALUE_01)

        return range_mm - self.offset_mm

    def get_data(self) -> dict[str, Any]:
        """Get sensor data in standardized format (Sensor interface).
        
        Returns:
            A dictionary containing:
                - distance_mm (int): The measured distance in millimeters.
                - is_valid (bool): Whether the measurement is valid.
                - raw_value (int): The raw sensor value before offset.
                - timestamp (float): The measurement timestamp.
        """
        try:
            raw_distance = self.get_range() + self.offset_mm  # Get raw before offset
            distance = raw_distance - self.offset_mm
            return {
                "distance_mm": distance,
                "is_valid": 0 < distance < 8190,  # VL53L0X valid range
                "raw_value": raw_distance,
                "timestamp": time.time(),
            }
        except Exception as e:
            self.__log.error("Failed to get distance: %s", e)
            return {
                "distance_mm": -1,
                "is_valid": False,
                "raw_value": None,
                "timestamp": time.time(),
            }


    def set_offset(self, offset_mm: int) -> None:
        """
        測定値のオフセット(mm)を設定します。

        Args:
            offset_mm (int): オフセット値 (mm)
        """
        self.offset_mm = offset_mm

    def get_ranges(self, num_samples: int) -> np.ndarray:
        """
        指定されたサンプル数の連続測距を実行し、結果をNumPy配列で返します。
        """
        samples = np.empty(num_samples, dtype=np.uint16)
        for i in range(num_samples):
            samples[i] = self.get_range()
        return samples

    def calibrate(self, target_distance_mm: int, num_samples: int) -> int:
        """
        指定されたターゲット距離でキャリブレーションを行い、オフセット値を計算します。

        Args:
            target_distance_mm (int): ターゲットまでの実際の距離 (mm)
            num_samples (int): 測定回数

        Returns:
            int: 計算されたオフセット値 (mm)
        """
        self.__log.debug(
            "Calibrating with target_distance_mm=%s, num_samples=%s",
            target_distance_mm, num_samples
        )

        # オフセットを一時的に0にして測定
        current_offset = self.offset_mm
        self.set_offset(0)

        samples = self.get_ranges(num_samples)
        measured_distance = int(np.mean(samples))

        # オフセットを元に戻す
        self.set_offset(current_offset)

        offset = measured_distance - target_distance_mm
        self.__log.debug("measured_distance=%s, offset=%s", measured_distance, offset)

        return offset

    def close(self) -> None:
        """
        I2C接続を閉じます。
        """
        self.pi.i2c_close(self.handle)

    def read_byte(self, register: int) -> int:
        """
        レジスタから1バイト読み取ります。
        """
        value = self.pi.i2c_read_byte_data(self.handle, register)
        # self.__log.debug("レジスタ %s からバイトを読み取り: %s", hex(register), hex(value))
        return int(value)

    def write_byte(self, register: int, value: int) -> None:
        """
        レジスタに1バイト書き込みます。
        """
        # self.__log.debug("レジスタ %s にバイトを書き込み: %s", hex(register), hex(value))
        self.pi.i2c_write_byte_data(self.handle, register, value)

    def read_word(self, register: int) -> int:
        """
        レジスタから1ワード読み取ります。
        """
        val = self.pi.i2c_read_word_data(self.handle, register)
        # pigpioはリトルエンディアンで読み取りますが、VL53L0Xはビッグエンディアンです。
        value = ((val & 0xFF) << 8) | (val >> 8)
        # self.__log.debug("レジスタ %s からワードを読み取り: %s", hex(register), hex(value))
        return int(value)

    def write_word(self, register: int, value: int) -> None:
        """
        レジスタに1ワード書き込みます。
        """
        # pigpioはリトルエンディアンで書き込みますが、VL53L0Xはビッグエンディアンです。
        value = ((value & 0xFF) << 8) | (value >> 8)
        self.pi.i2c_write_word_data(self.handle, register, value)

    def read_block(self, register: int, count: int) -> list[int]:
        """
        レジスタからデータのブロックを読み取ります。
        """
        _, data = self.pi.i2c_read_i2c_block_data(
            self.handle, register, count
        )
        if isinstance(data, bytearray):
            return list(data)
        return []

    def write_block(self, register: int, data: list[int]) -> None:
        """
        レジスタにデータのブロックを書き込みます。
        """
        self.pi.i2c_write_i2c_block_data(self.handle, register, data)
