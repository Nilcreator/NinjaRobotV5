# NinjaRobot V5

<div align="center">

**The Next-Gen Modular AI Robot Platform for Research and STEAM Education**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi%20Zero%202W-red.svg)](https://www.raspberrypi.com/)

</div>

---

## 📋 Table of Contents

- [Project Objective](#-project-objective)
- [NinjaRobot V5 Overview](#-ninjarobot-v5-overview)
- [New V5 Features](#-new-v5-features)
- [System Architecture](#-system-architecture)
- [Library Introduction](#-library-introduction)
- [Getting Started](#-getting-started)
- [Documentation](#-documentation)
- [Current Status](#-current-status)
- [License](#-license)

---

## 🎯 Project Objective

**NinjaRobot V5** represents the evolution of the NinjaRobot platform. While maintaining the core mission of accessible **AI-integrated Robot Research and STEAM Education**, V5 shifts focus to **modularity**, **connectivity**, and **agentic AI**.

We aim to create a robot that:
- **Adapts to Hardware**: Users can swap sensors and actuators as easily as installing a plugin.
- **Connects Instantly**: No complex WiFi setup required—connect directly via Bluetooth for instant local control.
- **Teaches Visually**: Programs can be built with blocks, making logic accessible to beginners.
- **Codes Itself**: The AI doesn't just chat; it writes code to learn new skills on the fly.

---

## 🤖 NinjaRobot V5 Overview

### What is NinjaRobot V5?

NinjaRobot V5 is an advanced, plugin-based robotics platform powered by a **Raspberry Pi Zero 2W**. It utilizes **Google Gemini** not just for conversation, but as a "coding partner" that runs directly on the robot. It features a new **Hardware Abstraction Layer (HAL)** that allows for dynamic driver loading, making it fully sensor-agnostic.

### Key Features (V5)

#### 🧩 **Hyper-Modularity**
- **Plugin-Based HAL**: Hardware drivers are loaded dynamically from `config.json`.
- **Sensor Agnostic**: Swap the VL53L0X Time-of-Flight sensor for an Ultrasonic sensor or LiDAR without rewriting application code.
- **Unified Interfaces**: All components adhere to strict `Sensor` and `Actuator` protocols.

#### 🔗 **Dual Connectivity (Hybrid Mode)**
NinjaRobot V5 offers two simultaneous ways to connect, ensuring flexibility for any scenario:
1.  **Local Bluetooth (BLE)**: Instant, zero-setup control via Web Bluetooth or mobile app. Best for classrooms and quick demos.
2.  **Remote Web Control (ngrok)**: Full AI interaction and telepresence via a secure public tunnel. Best for remote research.
**Both modes work simultaneously** via a unified Command Dispatcher.

#### 🧩 **Visual Programming (Blockly)**
- **Drag-and-Drop Coding**: Integrated **Google Blockly** interface allows users to program robot movements, sounds, and logic visually.
- **Real-time Deployment**: Blocks are converted to Python and executed safely on the robot instantly.
- **Education First**: Perfect for STEAM workshops to teach programming concepts without syntax errors.

#### 🧠 **Agentic AI Coding**
- **Self-Programming**: The AI agent can generate executable Python code to create new behaviors (e.g., "Create a dance that reacts to loud noises").
- **Sandboxed Execution**: Generated code runs in a safe, restricted environment.
- **Context Awareness**: The agent understands the robot's current hardware configuration and API availability.

---

## 🏗️ System Architecture

NinjaRobot V5 introduces a modular architecture with a new Bluetooth layer and dynamic driver loading.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                 │
│  ┌────────────────┐  ┌───────────────┐  ┌─────────────┐  ┌────────────┐   │
│  │ Blockly Editor │  │  Web Client   │  │ Mobile APP  │  │ Voice / CLI│   │
│  │ (Visual Code)  │  │  (WebSocket)  │  │ (Bluetooth) │  │ (Term)     │   │
│  └───────┬────────┘  └──────┬────────┘  └──────┬──────┘  └──────┬─────┘   │
└──────────┼──────────────────┼──────────────────┼────────────────┼─────────┘
           │                  │                  │                │
┌──────────▼──────────────────▼──────────────────▼────────────────▼─────────┐
│                          APPLICATION LAYER                                │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │           ninja_core (Unified Orchestration)                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │         Command Dispatcher & Safe Executor                   │  │   │
│  │  └──────┬──────────────┬───────────────┬───────────┬────────────┘  │   │
│  │         │              │               │           │               │   │
│  │  ┌──────▼─────┐  ┌─────▼──────┐  ┌─────▼───────┐ ┌─▼─────────┐     │   │
│  │  │ Web Server │  │ BLE Service│  │ NinjaAgent  │ │Code Sandbox│    │   │
│  │  └────────────┘  └────────────┘  └─────────────┘ └───────────┘     │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │     Hardware Abstraction Layer (Dynamic HAL)                       │   │
│  │       (Loads drivers based on config.json)                         │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│             ▲                    ▲                   ▲                    │
└─────────────┼────────────────────┼───────────────────┼────────────────────┘
              │ Implements         │ Implements        │                    │
┌─────────────▼──────┐   ┌─────────▼───────┐   ┌───────▼──────┐             │
│   ninja_interfaces │   │ ninja_interfaces│   │ ...          │             │
│      (Sensor)      │   │   (Actuator)    │   │              │             │
└─────────────┬──────┘   └─────────┬───────┘   └──────────────┘             │
              │                    │                                        │
┌─────────────▼──────┐   ┌─────────▼───────┐   ┌──────────────┐             │
│  pi0vl53l0x        │   │  pi0servo       │   │ pi0disp      │             │
│  (Driver)          │   │  (Driver)       │   │ (Driver)     │             │
└─────────────┬──────┘   └─────────┬───────┘   └───────┬──────┘             │
                                   │                   │                    │
┌──────────────────────────────────▼───────────────────▼────────────────────┐
│                    HARDWARE (Raspberry Pi)                                │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Library Introduction

NinjaRobot V5 consists of specific packages optimized for modularity.

### 🧩 Core & Utils

- **`ninja_core`**: The brain. Contains the Agent, Web Server, BLE Service, and Dynamic HAL.
- **`ninja_utils`**: Shared utilities and **new Interface Definitions** (`Sensor`, `Actuator`).
- **`ninja_ble`** *(New)*: Dedicated Bluetooth Low Energy stack.

### 🛠️ Hardware Drivers (Plugins)

These libraries now implement standard interfaces:

- **`pi0servo`**: Servo controller (implements `Actuator`).
- **`pi0disp`**: ST7789V Display driver (implements `Actuator`).
- **`pi0vl53l0x`**: Distance sensor driver (implements `Sensor`).
- **`pi0buzzer`**: Sound driver (implements `Actuator`).

---

## 🚀 Getting Started

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# Install everything (using uv)
uv pip install -e .

# Configure your hardware (V5 Style)
# Create a config that specifies which drivers to use
uv run ninja_core config init --defaults

# Start the robot (BLE + Web)
uv run ninja_core start
```

### Documentation Links
- **[Development Plan (V5)](DevelopmentPlan.md)** - The roadmap for V5 features.
- **[Development Guide](DevelopmentGuide.md)** - Technical API reference.
- **[Installation Guide](InstallationGuide.md)** - Setup instructions.

---

## 📊 Current Status

**Development Phase:** **V5 Phase 1 Complete ✅**

Phase 1 (Modularity & Foundation) has been implemented and verified on Raspberry Pi Zero 2W.

- ✅ **V4 Base**: Stable web control, ngrok remote access, basic AI agent.
- ✅ **Health Check**: Comprehensive codebase review completed (2025-12-30).
- ✅ **Modularity (Phase 1)**: ABCs created, HAL refactored, all drivers updated. **VERIFIED.**
- 📅 **Connectivity (Phase 2)**: BLE integration planned.
- 📅 **Visual Programming (Phase 3)**: Google Blockly integration planned.
- 📅 **AI Coding (Phase 3)**: Code generation agent planned.


---

## 📄 License

This project is licensed under the **MIT License**.

**Copyright © 2025 Chihkuang Chang**

---
---

# NinjaRobot V5 (日本語版)

<div align="center">

**研究とSTEAM教育のための、次世代モジュール型AIロボットプラットフォーム**

</div>

---

## 📋 目次

- [プロジェクトの目的](#-プロジェクトの目的)
- [NinjaRobot V5の概要](#-ninjarobot-v5の概要)
- [V5の新機能](#-v5の新機能)
- [システム構成](#-システム構成-1)
- [ライブラリの紹介](#-ライブラリの紹介-1)
- [はじめに](#-はじめに-1)
- [現在の状況](#-現在の状況-1)

---

## 🎯 プロジェクトの目的

**NinjaRobot V5**は、NinjaRobotプラットフォームの進化形です。**AI統合ロボット研究とSTEAM教育**という核心的な使命を維持しながら、V5では**モジュール性**、**接続性**、そして**エージェント型AI**に焦点を移します。

私たちが目指すロボット:
- **ハードウェアへの適応**: プラグインをインストールするように、センサーやアクチュエーターを簡単に交換できる。
- **瞬時の接続**: 複雑なWiFi設定は不要。Bluetoothで直接接続してローカルですぐに制御できる。
- **視覚的に学ぶ**: ブロックを使ってプログラムを構築できるので、初心者でもプログラミングの論理を学べる。
- **自己プログラミング**: AIは単におしゃべりするだけでなく、コードを書いて新しいスキルをその場で学習する。

---

## 🤖 NinjaRobot V5の概要

### NinjaRobot V5とは？

NinjaRobot V5は、**Raspberry Pi Zero 2W**で動作する、高度なプラグインベースのロボットプラットフォームです。**Google Gemini**を単なる会話相手としてだけでなく、ロボット上で直接動作する「コーディングパートナー」として活用します。動的ドライバー読み込みを可能にする新しい**ハードウェア抽象化レイヤー (HAL)** を備えており、センサーの種類に依存しません。

### 主な機能 (V5)

#### 🧩 **超モジュール性 (Hyper-Modularity)**
- **プラグインベースHAL**: ハードウェアドライバーは`config.json`から動的に読み込まれます。
- **センサー非依存**: アプリケーションコードを書き換えることなく、VL53L0X距離センサーを超音波センサーやLiDARに交換できます。
- **統一インターフェース**: すべてのコンポーネントは厳格な`Sensor`および`Actuator`プロトコルに準拠します。

#### 🔗 **デュアル接続 (ハイブリッドモード)**
NinjaRobot V5は、あらゆるシナリオに対応するために、2つの同時接続方法を提供します:
1.  **ローカルBluetooth (BLE)**: Web Bluetoothやモバイルアプリで瞬時に接続。教室やデモに最適。
2.  **リモートWeb制御 (ngrok)**: ngrok経由の安全なトンネルで、どこからでもAI対話や制御が可能。

#### 🧩 **ビジュアルプログラミング (Blockly)**
- **ドラッグ＆ドロップ**: **Google Blockly**インターフェースを統合し、ロボットの動作や音、ロジックを視覚的にプログラムできます。
- **リアルタイム実行**: ブロックはPythonに変換され、瞬時にロボット上で安全に実行されます。
- **教育ファースト**: 構文エラーを気にせずプログラミング概念を教えるSTEAMワークショップに最適です。

#### 🧠 **エージェント型AIコーディング**
- **自己プログラミング**: AIエージェントは実行可能なPythonコードを生成して、新しい振る舞いを作成できます（例：「大きな音に反応して踊るダンスを作って」）。
- **サンドボックス実行**: 生成されたコードは、安全で制限された環境で実行されます。
- **文脈認識**: エージェントはロボットの現在のハードウェア構成とAPIの可用性を理解しています。

---

## 🏗️ システム構成

NinjaRobot V5は、新しいBluetoothレイヤーと動的ドライバー読み込みを備えたモジュール型アーキテクチャを導入しています。

*(アーキテクチャ図は英語版を参照してください)*

---

## 📚 ライブラリの紹介

NinjaRobot V5は、モジュール性のために最適化された特定のパッケージで構成されています。

### 🧩 コア & ユーティリティ

- **`ninja_core`**: 頭脳。エージェント、Webサーバー、BLEサービス、動的HALを含みます。
- **`ninja_utils`**: 共有ユーティリティと**新しいインターフェース定義** (`Sensor`, `Actuator`)。
- **`ninja_ble`** *(新規)*: 専用のBluetooth Low Energyスタック。

### 🛠️ ハードウェアドライバー (プラグイン)

これらのライブラリは、標準インターフェースを実装するようになります:

- **`pi0servo`**: サーボコントローラー (`Actuator`を実装)。
- **`pi0disp`**: ST7789Vディスプレイドライバー (`Actuator`を実装)。
- **`pi0vl53l0x`**: 距離センサードライバー (`Sensor`を実装)。
- **`pi0buzzer`**: サウンドドライバー (`Actuator`を実装)。

---

## 🚀 はじめに

### クイックインストール

```bash
# リポジトリをクローン
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# すべてをインストール (uvを使用)
uv pip install -e .

# ハードウェアの設定 (V5スタイル)
# どのドライバーを使用するかを指定する設定を作成
uv run ninja_core config init --defaults

# ロボットを起動 (BLE + Web)
uv run ninja_core start
```

---

## 📊 現在の状況

**開発フェーズ:** **V5 フェーズ1 完了 ✅**

フェーズ1（モジュール性と基盤）は、Raspberry Pi Zero 2Wで実装および検証が完了しました。

- ✅ **V4ベース**: 安定したWeb制御、ngrokリモートアクセス、基本的なAIエージェント。
- ✅ **ヘルスチェック**: 包括的なコードベースレビュー完了 (2025-12-30)。
- ✅ **モジュール性（フェーズ1)**: ABC作成、HALリファクタリング、全ドライバー更新完了。**検証済み。**
- 📅 **接続性（フェーズ2)**: BLE統合を計画中。
- 📅 **ビジュアルプログラミング（フェーズ3)**: Google Blockly統合を計画中。
- 📅 **AIコーディング（フェーズ3)**: コード生成エージェントを計画中。


---

## 📄 ライセンス

このプロジェクトは**MITライセンス**の下でライセンスされています。

**Copyright © 2025 Chihkuang Chang**

---
