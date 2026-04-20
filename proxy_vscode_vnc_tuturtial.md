

#：JupyterHub 進階開發環境安裝指南


# JupyterHub 進階開發環境安裝指南

本文件將引導你如何在 JupyterHub 環境中安裝並設定 **Jupyter Server Proxy**、免 root 權限的 **VS Code (code-server)** 以及 **VNC 遠端桌面**。

---

## 🚀 關鍵最後一步：重啟伺服器 (重要！)
**請注意：** 無論你安裝了以下哪種工具，安裝完成後 **「務必」** 執行以下動作，否則 JupyterLab 的 **Launcher (啟動器)** 畫面將不會出現對應的圖示：

1. 點擊 JupyterLab 左上角選單：**File** -> **Hub Control Panel**。
2. 在開啟的頁面中點擊 **「Stop My Server」**。
3. 等待伺服器完全停止後，點擊 **「Start My Server」**。
4. 重新進入 JupyterLab 後，你就能在 Launcher 頁面看到 VS Code 或 Desktop 的圖示了。

---

## 📋 目錄
1. [安裝 Jupyter Server Proxy](#1-安裝-jupyter-server-proxy)
2. [安裝 VS Code (code-server) - 免權限版](#2-安裝-vs-code-code-server---免-root-權限版)
3. [安裝 VNC 遠端桌面服務](#3-安裝-vnc-遠端桌面服務)

---

## 1. 安裝 Jupyter Server Proxy
這是所有服務的基礎，負責轉發流量。

```bash
# 推薦：裝在 JupyterLab 系統所在的環境
/opt/conda/bin/pip install jupyter-server-proxy
```

---

## 2. 安裝 VS Code (code-server) - 免 root 權限版
適合無法使用 sudo 的環境。

### 第一步：安裝到家目錄
```bash
curl -fsSL [https://code-server.dev/install.sh](https://code-server.dev/install.sh) | sh -s -- --method standalone --prefix /home/jovyan/.local
```

### 第二步：設定路徑優先權
```bash
echo 'export PATH="/home/jovyan/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 第三步：安裝 Jupyter 集成代理
```bash
pip install jupyter-vscode-proxy
```
*(安裝完後請記得執行最上方的「重啟伺服器」步驟)*

---

## 3. 安裝 VNC 遠端桌面服務
提供 GUI 圖形化介面。

### 第一步：安裝基礎環境 (需管理員 sudo)
```bash
sudo apt-get update
sudo apt-get install -y xfce4 xfce4-goodies tightvncserver dbus-x11
```

### 第二步：安裝桌面代理擴充
```bash
pip install jupyter-remote-desktop-proxy
```
*(安裝完後請記得執行最上方的「重啟伺服器」步驟)*

---

## 🔍 常見問題排查

* **問題：Launcher 還是沒看到圖示？**
    * 確認你是點擊了 Hub Control Panel 的「Stop My Server」，而不是單純重新整理網頁。
    * 檢查安裝時是否出現 `Permission denied`，若是請嘗試在 pip 安裝時加上 `--user` 參數。
* **問題：點擊圖示後出現 404？**
    * 請確認網址列結尾是否有斜線 `/`，例如 `.../vscode/`。
```

這樣修改後，使用者一打開文件就能看到最醒目的重啟提醒，能有效減少因為沒重啟而產生的操作困惑！
