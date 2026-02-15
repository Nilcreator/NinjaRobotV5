# NinjaRobot V5

<div align="center">

![NinjaRobot Logo](assets/logo.png)

**The Next-Generation AI-Powered Educational Robot Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
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
| **Display** | 1.3" ST7789V TFT LCD (240×240 pixels) |
| **Distance Sensor** | VL53L0X Time-of-Flight (up to 2m range) |
| **Sound** | Passive Buzzer (GPIO 17) |
| **Movement** | 8× Servo Motors (GPIO 20-27) |
| **Connectivity** | WiFi 802.11n, Bluetooth 4.2 LE |

### Software Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + Uvicorn |
| **AI Agent** | Google Gemini (gemini-3-flash-preview) |
| **Frontend** | React 18 + Vite + react-i18next |
| **BLE Service** | bless (GATT Server) |
| **Hardware Control** | pigpio + Custom Drivers |

## ✨ Key Features

### 🧠 Agentic AI
- **Natural Language Understanding**: Chat with your robot in English, Japanese, or Chinese
- **Action Planning**: AI automatically translates requests into robot actions
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

# Start the robot
uv run ninja_core server
```

Then open `http://ninjarobot.local:8000` in your browser!

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](InstallationGuide.md) | Hardware setup and software installation |
| [Development Guide](DevelopmentGuide.md) | API reference and architecture overview |
| [Development Plan](DevelopmentPlan.md) | Project roadmap and phase details |
| [Development Log](DevelopmentLog.md) | Change history and version notes |

## 📊 Current Status

**Version:** 5.2.3  
**Status:** Phase 5 Complete ✅ + pi0servo V2 + pi0vl53l0x V2

All core features have been implemented and verified:
- ✅ Modular Hardware Abstraction Layer
- ✅ Dual Connectivity (Wi-Fi + BLE)
- ✅ Agentic AI with Action Planning
- ✅ Safe Code Execution Engine
- ✅ React Web Application
- ✅ pi0vl53l0x V2 (thread-safe I2C, hardened init, CLI)

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
| **ディスプレイ** | 1.3インチ ST7789V TFT LCD（240×240ピクセル） |
| **距離センサー** | VL53L0X ToF（最大2m測定可能） |
| **音声** | パッシブブザー（GPIO 17） |
| **動作** | 8×サーボモーター（GPIO 20-27） |
| **接続** | WiFi 802.11n、Bluetooth 4.2 LE |

### ソフトウェアスタック

| レイヤー | 技術 |
|---------|------|
| **バックエンド** | FastAPI + Uvicorn |
| **AIエージェント** | Google Gemini（gemini-3-flash-preview） |
| **フロントエンド** | React 18 + Vite + react-i18next |
| **BLEサービス** | bless（GATTサーバー） |
| **ハードウェア制御** | pigpio + カスタムドライバー |

## ✨ 主な機能

### 🧠 エージェント型AI
- **自然言語理解**: 英語、日本語、中国語でロボットと会話
- **アクションプランニング**: AIがリクエストを自動的にロボットのアクションに変換
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

# ロボットを起動
uv run ninja_core server
```

ブラウザで `http://ninjarobot.local:8000` を開いてください！

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [インストールガイド](InstallationGuide.md) | ハードウェアセットアップとソフトウェアインストール |
| [開発ガイド](DevelopmentGuide.md) | APIリファレンスとアーキテクチャ概要 |
| [開発計画](DevelopmentPlan.md) | プロジェクトロードマップとフェーズ詳細 |
| [開発ログ](DevelopmentLog.md) | 変更履歴とバージョンノート |

## 📊 現在のステータス

**バージョン:** 5.2.3  
**ステータス:** フェーズ5完了 ✅ + pi0servo V2 + pi0vl53l0x V2

すべてのコア機能が実装・検証されました：
- ✅ モジュール式ハードウェア抽象化レイヤー
- ✅ デュアル接続（Wi-Fi + BLE）
- ✅ アクションプランニング付きエージェント型AI
- ✅ 安全なコード実行エンジン
- ✅ React Webアプリケーション
- ✅ pi0vl53l0x V2（スレッドセーフI2C、堅牢な初期化、CLI）

## 📄 ライセンス

このプロジェクトは**MITライセンス**の下でライセンスされています。

**Copyright © 2025 Chihkuang Chang**

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
| **顯示器** | 1.3吋 ST7789V TFT LCD（240×240像素） |
| **距離感測器** | VL53L0X ToF（最遠2公尺） |
| **音效** | 被動蜂鳴器（GPIO 17） |
| **動作** | 8×伺服馬達（GPIO 20-27） |
| **連線** | WiFi 802.11n、藍牙 4.2 LE |

### 軟體架構

| 層級 | 技術 |
|------|------|
| **後端** | FastAPI + Uvicorn |
| **AI代理** | Google Gemini（gemini-3-flash-preview） |
| **前端** | React 18 + Vite + react-i18next |
| **BLE服務** | bless（GATT伺服器） |
| **硬體控制** | pigpio + 自訂驅動程式 |

## ✨ 主要功能

### 🧠 代理式AI
- **自然語言理解**：用英文、日文或中文與機器人對話
- **動作規劃**：AI自動將請求轉換為機器人動作
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

# 啟動機器人
uv run ninja_core server
```

然後在瀏覽器開啟 `http://ninjarobot.local:8000`！

## 📚 文件

| 文件 | 說明 |
|------|------|
| [安裝指南](InstallationGuide.md) | 硬體設定與軟體安裝 |
| [開發指南](DevelopmentGuide.md) | API參考與架構概述 |
| [開發計畫](DevelopmentPlan.md) | 專案路線圖與階段詳情 |
| [開發日誌](DevelopmentLog.md) | 變更歷史與版本說明 |

## 📊 目前狀態

**版本：** 5.2.3  
**狀態：** 第五階段完成 ✅ + pi0servo V2 + pi0vl53l0x V2

所有核心功能已實作並驗證：
- ✅ 模組化硬體抽象層
- ✅ 雙重連線（Wi-Fi + BLE）
- ✅ 具動作規劃的代理式AI
- ✅ 安全程式碼執行引擎
- ✅ React網頁應用程式
- ✅ pi0vl53l0x V2（線程安全I2C、強化初始化、CLI）

## 📄 授權

本專案採用**MIT授權**。

**Copyright © 2025 Chihkuang Chang**

---

<div align="center">

Made with ❤️ for Education and Research

</div>
