# NinjaRobot V5

<div align="center">

![NinjaRobot Logo](assets/logo.png)

**The Next-Generation AI-Powered Educational Robot Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi%20Zero%202W-red.svg)](https://www.raspberrypi.com/)
[![AI: Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)

[English](#english) | [日本語](#日本語) | [繁體中文](#繁體中文)

</div>

---

# English

## 🎯 Project Overview

**NinjaRobot V5** is an advanced, modular AI robot platform designed for Research and STEAM Education. Built on the Raspberry Pi Zero 2W, it combines cutting-edge AI capabilities with an intuitive web interface, making robotics accessible to learners of all ages.

Unlike traditional educational robots, NinjaRobot features an **Agentic AI** powered by Google Gemini that can understand natural language, execute commands, and even generate code to learn new behaviors autonomously.

## 🤖 Robot Specifications

### Hardware

| Component | Specification |
|-----------|---------------|
| **Brain** | Raspberry Pi Zero 2W (Quad-core ARM Cortex-A53, 512MB RAM) |
| **Display** | 2.0" ST7789V IPS LCD (240×320 pixels) |
| **Distance Sensor** | VL53L0X Time-of-Flight (up to 2m range) |
| **Sound** | Passive Buzzer (GPIO 17) |
| **Movement** | 8× Servo Motors (GPIO 20-27) |
| **Connectivity** | WiFi 802.11n, Bluetooth 4.2 LE |

### Software Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + Uvicorn |
| **AI Agent** | Google Gemini (user-selected available model) |
| **Frontend** | React 18 + Vite + react-i18next |
| **BLE Service** | bless (GATT Server) |
| **Hardware Control** | pigpio + Custom Drivers |

## ✨ Key Features

### 🧠 Agentic AI
- **Natural Language Understanding**: Chat with your robot in English, Japanese, or Chinese
- **Validated Model Selection**: Discover models available to your Gemini API key and save a model only after a bounded generation check succeeds
- **Gemini 3 Compatibility**: Use low-thinking REST generation with a 60-second bound when the legacy Python SDK cannot express current Gemini 3 thinking controls
- **Action Planning**: AI automatically translates requests into robot actions
- **Saved Blockly Actions**: Replay complete Code IDE actions saved over Bluetooth from the robot's local action library
- **Reliable BLE Save Status**: Code IDE saves are confirmed by robot-cached request status, so missed browser notifications do not look like failed uploads
- **Code Generation**: AI can write Python code to create new robot behaviors
- **Voice Input**: Speak commands using your device's microphone

### 📱 Modern Web Interface
- **Mobile-First Design**: Optimized for smartphones and tablets
- **Real-Time Feedback**: WebSocket-powered distance sensor display
- **Hardware Controls**: Trigger expressions, sounds, and movements
- **System Log Panel**: Monitor robot activities in real-time
- **Multi-Language UI**: Switch between EN, JA, ZH-TW, ZH-CN

### 🔗 Dual Connectivity
- **Local Wi-Fi**: Direct control via `http://ninjarobot.local:8000`
- **Bluetooth LE**: Zero-setup mobile app connection
- **BLE Request Recovery**: Dedicated command-status readback for robust Chrome/Raspberry Pi save confirmations
- **Remote Access**: ngrok tunnel for telepresence

### 🛡️ Safety First
- **Sandboxed Execution**: User/AI-generated code runs in a restricted environment
- **Emergency Stop**: Instant halt capability for all motors
- **Graceful Shutdown**: Safe power-off with "sleepy" animation (face, sound, and pose)
- **Shutdown Animation**: Robot displays sleepy face, plays sleepy sound, and moves to rest position before powering off

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# Install dependencies (using uv)
uv pip install -e .

# Build the web interface
cd ninja_webapp && npm install && npm run build && cd ..

# Configure the Gemini key and select a validated model
# Option 1 hides the API key while you enter it.
uv run ninja_core init-tool

# Start the robot
uv run ninja_core server
```

Then open `http://ninjarobot.local:8000` in your browser!

During Gemini setup, NinjaRobot retrieves the models available to the supplied key and runs a minimal generation request before saving the key/model pair. Thinking-model validation can take up to 60 seconds. If lookup, validation, or selection fails, the previous Gemini configuration remains unchanged. The server console reports the configured model and returns a visible timeout instead of waiting indefinitely.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](InstallationGuide.md) | Hardware setup and software installation |
| [Development Guide](DevelopmentGuide.md) | API reference and architecture overview |
| [Project Upgrade Plan](ProjectUpgradePlan.md) | Project roadmap and phase details |
| [Development Log](DevelopmentLog.md) | Change history and version notes |
| [AI Development Protocol](AGENTS.md) | Cross-tool development, safety, validation, and wiki rules |
| [NinjaRobotPi0 Wiki](Wiki/NinjaRobotPi0_Wiki/README.md) | Local, source-traceable knowledge base for AI-assisted development |
| [Wiki Integration Workflow](WikiIntegrationWorkflowPlan.md) | Integration design, maintenance gates, and rollout checks |

## 📊 Current Status

**Version:** 5.3.0  
**Status:** Phase 5 Complete ✅ + All Hardware Libraries Rebuilt

All core features have been implemented and verified:
- ✅ Modular Hardware Abstraction Layer
- ✅ Dual Connectivity (Wi-Fi + BLE)
- ✅ Agentic AI with Action Planning
- ✅ Saved Blockly Action Library for Code IDE uploads
- ✅ Safe Code Execution Engine
- ✅ React Web Application
- ✅ pi0servo V1.0 (velocity-based motion, per-servo speed, easing curves)
- ✅ pi0vl53l0x V2.0 (thread-safe I2C, hardened init, CLI)
- ✅ pi0disp V2.0 (thread-safe SPI, delta rendering, PWM brightness)
- ✅ pi0buzzer V1.0 (non-blocking queue, emotion sounds, interactive TUI)

## 📄 License

This project is licensed under the **MIT License**.

**Copyright © 2026 Chihkuang Chang**

---

# 日本語

## 🎯 プロジェクト概要

**NinjaRobot V5**は、研究およびSTEAM教育向けに設計された先進的なモジュール式AIロボットプラットフォームです。Raspberry Pi Zero 2Wをベースに構築され、最先端のAI機能と直感的なWebインターフェースを組み合わせ、あらゆる年齢の学習者がロボット工学にアクセスできるようにしています。

従来の教育用ロボットとは異なり、NinjaRobotはGoogle Geminiを搭載した**エージェント型AI**を特徴とし、自然言語を理解し、コマンドを実行し、さらには自律的に新しい動作を学習するためのコードを生成することができます。

## 🤖 ロボット仕様

### ハードウェア

| コンポーネント | 仕様 |
|---------------|------|
| **頭脳** | Raspberry Pi Zero 2W（クアッドコアARM Cortex-A53、512MB RAM） |
| **ディスプレイ** | 2.0インチ ST7789V IPS LCD（240×320ピクセル） |
| **距離センサー** | VL53L0X ToF（最大2m測定可能） |
| **音声** | パッシブブザー（GPIO 17） |
| **動作** | 8×サーボモーター（GPIO 20-27） |
| **接続** | WiFi 802.11n、Bluetooth 4.2 LE |

### ソフトウェアスタック

| レイヤー | 技術 |
|---------|------|
| **バックエンド** | FastAPI + Uvicorn |
| **AIエージェント** | Google Gemini（利用可能なモデルをユーザーが選択） |
| **フロントエンド** | React 18 + Vite + react-i18next |
| **BLEサービス** | bless（GATTサーバー） |
| **ハードウェア制御** | pigpio + カスタムドライバー |

## ✨ 主な機能

### 🧠 エージェント型AI
- **自然言語理解**: 英語、日本語、中国語でロボットと会話
- **検証付きモデル選択**: Gemini APIキーで利用可能なモデルを取得し、時間制限付き生成テストに成功したモデルだけを保存
- **Gemini 3互換性**: 従来のPython SDKで現在の思考制御を指定できない場合、低思考レベルと60秒の上限を設定したREST生成を使用
- **アクションプランニング**: AIがリクエストを自動的にロボットのアクションに変換
- **保存済みBlocklyアクション**: Bluetooth経由で保存したCode IDEの完全な動作をローカルアクションライブラリから再生
- **コード生成**: AIが新しいロボットの動作を作成するPythonコードを記述
- **音声入力**: デバイスのマイクを使用してコマンドを話す

### 📱 モダンなWebインターフェース
- **モバイルファーストデザイン**: スマートフォンやタブレット向けに最適化
- **リアルタイムフィードバック**: WebSocket対応の距離センサー表示
- **ハードウェアコントロール**: 表情、音、動きをトリガー
- **システムログパネル**: ロボットの活動をリアルタイムで監視
- **多言語UI**: EN、JA、ZH-TW、ZH-CNで切り替え

### 🔗 デュアル接続
- **ローカルWi-Fi**: `http://ninjarobot.local:8000`経由で直接制御
- **Bluetooth LE**: セットアップ不要のモバイルアプリ接続
- **リモートアクセス**: テレプレゼンス用ngrokトンネル

### 🛡️ 安全第一
- **サンドボックス実行**: ユーザー/AI生成コードは制限された環境で実行
- **緊急停止**: すべてのモーターを即座に停止する機能
- **安全なシャットダウン**: 「眠い」アニメーション付きの安全な電源オフ（表情、音、姿勢）
- **シャットダウンアニメーション**: 電源オフ前に眠い顔を表示、眠い音を再生、休憩姿勢に移動

## 🚀 クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# 依存関係をインストール（uvを使用）
uv pip install -e .

# Webインターフェースをビルド
cd ninja_webapp && npm install && npm run build && cd ..

# Gemini APIキーを設定し、検証済みモデルを選択
# オプション1では入力中のAPIキーが非表示になります。
uv run ninja_core init-tool

# ロボットを起動
uv run ninja_core server
```

ブラウザで `http://ninjarobot.local:8000` を開いてください！

Geminiの設定時、NinjaRobotは入力したキーで利用可能なモデルを取得し、キーとモデルを保存する前に最小生成テストを実行します。思考モデルの検証には最大60秒かかる場合があります。取得、検証、または選択に失敗した場合、以前のGemini設定は変更されません。サーバーコンソールには設定中のモデルが表示され、無期限に待機する代わりに明確なタイムアウトが返されます。

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [インストールガイド](InstallationGuide.md) | ハードウェアセットアップとソフトウェアインストール |
| [開発ガイド](DevelopmentGuide.md) | APIリファレンスとアーキテクチャ概要 |
| [プロジェクトアップグレード計画](ProjectUpgradePlan.md) | プロジェクトロードマップとフェーズ詳細 |
| [開発ログ](DevelopmentLog.md) | 変更履歴とバージョンノート |
| [AI開発プロトコル](AGENTS.md) | AIツール共通の開発、安全、検証、Wiki運用ルール |
| [NinjaRobotPi0 Wiki](Wiki/NinjaRobotPi0_Wiki/README.md) | AI支援開発向けの出典追跡可能なローカル知識ベース |
| [Wiki統合ワークフロー](WikiIntegrationWorkflowPlan.md) | 統合設計、保守ゲート、導入確認 |

## 📊 現在のステータス

**バージョン:** 5.3.0  
**ステータス:** フェーズ5完了 ✅ + 全ハードウェアライブラリ再構築済み

すべてのコア機能が実装・検証されました：
- ✅ モジュール式ハードウェア抽象化レイヤー
- ✅ デュアル接続（Wi-Fi + BLE）
- ✅ アクションプランニング付きエージェント型AI
- ✅ Code IDEアップロード用の保存済みBlocklyアクションライブラリ
- ✅ 安全なコード実行エンジン
- ✅ React Webアプリケーション
- ✅ pi0servo V1.0（速度ベース制御、サーボ別速度、イージングカーブ）
- ✅ pi0vl53l0x V2.0（スレッドセーフI2C、堅牢な初期化、CLI）
- ✅ pi0disp V2.0（スレッドセーフSPI、デルタレンダリング、PWM輝度制御）
- ✅ pi0buzzer V1.0（ノンブロッキングキュー、感情サウンド、インタラクティブTUI）

## 📄 ライセンス

このプロジェクトは**MITライセンス**の下でライセンスされています。

**Copyright © 2026 Chihkuang Chang**

---

# 繁體中文

## 🎯 專案概述

**NinjaRobot V5**是一個為研究與STEAM教育設計的先進模組化AI機器人平台。基於Raspberry Pi Zero 2W構建，結合尖端AI功能與直覺的網頁介面，讓各年齡層的學習者都能輕鬆接觸機器人技術。

與傳統教育機器人不同，NinjaRobot搭載由Google Gemini驅動的**代理式AI**，能夠理解自然語言、執行指令，甚至自主生成程式碼來學習新行為。

## 🤖 機器人規格

### 硬體

| 元件 | 規格 |
|------|------|
| **大腦** | Raspberry Pi Zero 2W（四核心 ARM Cortex-A53，512MB RAM） |
| **顯示器** | 2.0吋 ST7789V IPS LCD（240×320像素） |
| **距離感測器** | VL53L0X ToF（最遠2公尺） |
| **音效** | 被動蜂鳴器（GPIO 17） |
| **動作** | 8×伺服馬達（GPIO 20-27） |
| **連線** | WiFi 802.11n、藍牙 4.2 LE |

### 軟體架構

| 層級 | 技術 |
|------|------|
| **後端** | FastAPI + Uvicorn |
| **AI代理** | Google Gemini（由使用者選擇可用模型） |
| **前端** | React 18 + Vite + react-i18next |
| **BLE服務** | bless（GATT伺服器） |
| **硬體控制** | pigpio + 自訂驅動程式 |

## ✨ 主要功能

### 🧠 代理式AI
- **自然語言理解**：用英文、日文或中文與機器人對話
- **經驗證的模型選擇**：取得Gemini API金鑰可用的模型，並只在有時限的生成測試成功後儲存模型
- **Gemini 3相容性**：當舊版Python SDK無法設定目前的Gemini 3思考控制時，使用低思考等級與60秒上限的REST生成
- **動作規劃**：AI自動將請求轉換為機器人動作
- **已儲存Blockly動作**：可從本機動作庫重播經由藍牙儲存的完整Code IDE動作
- **程式碼生成**：AI能撰寫Python程式碼來創建新的機器人行為
- **語音輸入**：使用裝置麥克風說出指令

### 📱 現代化網頁介面
- **行動優先設計**：針對智慧型手機和平板優化
- **即時回饋**：WebSocket驅動的距離感測器顯示
- **硬體控制**：觸發表情、音效和動作
- **系統日誌面板**：即時監控機器人活動
- **多語言介面**：支援EN、JA、ZH-TW、ZH-CN切換

### 🔗 雙重連線
- **本地Wi-Fi**：透過`http://ninjarobot.local:8000`直接控制
- **藍牙LE**：免設定的行動應用程式連線
- **遠端存取**：ngrok通道實現遠端遙控

### 🛡️ 安全至上
- **沙盒執行**：使用者/AI生成的程式碼在受限環境中執行
- **緊急停止**：即時停止所有馬達的功能
- **安全關機**：透過「睏倦」動畫安全關閉電源（表情、音效和姿勢）
- **關機動畫**：電源關閉前顯示睡眠表情、播放睡眠音效並移動至休息姿勢

## 🚀 快速開始

```bash
# 複製儲存庫
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5

# 安裝相依套件（使用uv）
uv pip install -e .

# 建置網頁介面
cd ninja_webapp && npm install && npm run build && cd ..

# 設定Gemini API金鑰並選擇經驗證的模型
# 選項1會在輸入時隱藏API金鑰。
uv run ninja_core init-tool

# 啟動機器人
uv run ninja_core server
```

然後在瀏覽器開啟 `http://ninjarobot.local:8000`！

設定Gemini時，NinjaRobot會取得此金鑰可用的模型，並在儲存金鑰與模型前執行最小生成測試。思考模型的驗證最多可能需要60秒。若取得、驗證或選擇失敗，先前的Gemini設定不會被變更。伺服器主控台會顯示目前設定的模型，並在逾時時回傳明確錯誤，而不是無限等待。

## 📚 文件

| 文件 | 說明 |
|------|------|
| [安裝指南](InstallationGuide.md) | 硬體設定與軟體安裝 |
| [開發指南](DevelopmentGuide.md) | API參考與架構概述 |
| [專案升級計畫](ProjectUpgradePlan.md) | 專案路線圖與階段詳情 |
| [開發日誌](DevelopmentLog.md) | 變更歷史與版本說明 |
| [AI 開發協定](AGENTS.md) | 跨工具開發、安全、驗證與 Wiki 維護規則 |
| [NinjaRobotPi0 Wiki](Wiki/NinjaRobotPi0_Wiki/README.md) | 供 AI 輔助開發使用、可追溯來源的本機知識庫 |
| [Wiki 整合工作流程](WikiIntegrationWorkflowPlan.md) | 整合設計、維護閘門與導入檢查 |

## 📊 目前狀態

**版本：** 5.3.0  
**狀態：** 第五階段完成 ✅ + 全硬體函式庫重建完成

所有核心功能已實作並驗證：
- ✅ 模組化硬體抽象層
- ✅ 雙重連線（Wi-Fi + BLE）
- ✅ 具動作規劃的代理式AI
- ✅ 支援Code IDE上傳的已儲存Blockly動作庫
- ✅ 安全程式碼執行引擎
- ✅ React網頁應用程式
- ✅ pi0servo V1.0（速度控制、獨立伺服速度、緩動曲線）
- ✅ pi0vl53l0x V2.0（線程安全I2C、強化初始化、CLI）
- ✅ pi0disp V2.0（線程安全SPI、差異渲染、PWM亮度控制）
- ✅ pi0buzzer V1.0（非阻塞佇列、情緒音效、互動式TUI）

## 📄 授權

本專案採用**MIT授權**。

**Copyright © 2026 Chihkuang Chang**

---

<div align="center">

Made with ❤️ for Education and Research

</div>
