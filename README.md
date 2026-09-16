# 🤖 Discord to Telegram Job Alert Bot (Powered by Gemini AI)

An automated 24/7 system that monitors Discord channels (text channels & forum posts), filters posts using **Google Gemini AI** to detect hiring posts for **Video Editors** or **Thumbnail Designers**, and immediately forwards formatted job alerts to your **Telegram Group**.

---

## 🌟 How It Works

1. **Discord Listener**: Checks your specified Discord channels every 5 minutes.
2. **State Tracker (`state.json`)**: Keeps track of the last processed post ID so **no posts are ever missed or duplicated**.
3. **Gemini AI Filter**: Uses Gemini AI to analyze post text and intelligently differentiate between someone **HIRING** vs someone self-promoting / offering services.
4. **Telegram Dispatcher**: Formats and sends matching posts with direct Discord post links directly to your Telegram Group.
5. **24/7 GitHub Actions**: Runs completely free and automatically 24 hours a day, 7 days a week.

---

## 🛠️ Step-by-Step Setup Guide (Zero Technical Knowledge Required)

Follow these simple steps to set up and run your bot in under 10 minutes!

---

### Step 1: Get Your API Credentials

#### 1️⃣ Discord Credentials
- **Discord Token**:
  - *Option A (Bot Token)*: Create a bot in [Discord Developer Portal](https://discord.com/developers/applications), add it to your target servers, and copy the Bot Token.
  - *Option B (User Token)*: Open Discord in your Web Browser -> Press `F12` -> Go to `Network` tab -> Click any request -> Copy the `Authorization` header token.
- **Discord Channel IDs**:
  - Enable **Developer Mode** in Discord Settings (`User Settings -> Advanced -> Developer Mode`).
  - Right-click any channel or forum channel you want to monitor and click **Copy Channel ID**.
  - If monitoring multiple channels, separate them with commas (e.g., `123456789,987654321`).

#### 2️⃣ Gemini API Key
- Go to [Google AI Studio](https://aistudio.google.com/).
- Click **Create API Key**.
- Copy your generated API key.

#### 3️⃣ Telegram Credentials
- **Telegram Bot Token**:
  - Search for `@BotFather` on Telegram.
  - Send `/newbot`, follow the prompts, and copy the HTTP API Token.
- **Telegram Group Chat ID**:
  - Add your new bot to your Telegram Group as an Admin.
  - Add `@myidbot` or `@raw_data_bot` to your group to see the Chat ID (it usually starts with a minus `-`, e.g., `-100123456789`).

---

### Step 2: Push This Code to GitHub

1. Create a new repository on [GitHub](https://github.com/new) named `discord-job-bot`.
2. Push all the files in this folder to your repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/discord-job-bot.git
   git push -u origin main
   ```

---

### Step 3: Add Your Credentials to GitHub Secrets

1. Go to your GitHub repository page.
2. Click **Settings** (top right tab).
3. On the left sidebar, click **Secrets and variables** -> **Actions**.
4. Click **New repository secret** for each of the following:

| Secret Name | Value |
| :--- | :--- |
| `DISCORD_TOKEN` | Your Discord Bot or User Token |
| `DISCORD_CHANNEL_IDS` | Comma-separated Channel IDs (e.g. `111222333,444555666`) |
| `GEMINI_API_KEY` | Your Google Gemini API Key |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token from `@BotFather` |
| `TELEGRAM_CHAT_ID` | Your Telegram Group Chat ID (e.g. `-100123456789`) |

---

### Step 4: Enable Workflow Permissions & Run!

1. In your GitHub repository, go to **Settings** -> **Actions** -> **General**.
2. Scroll down to **Workflow permissions** and select **Read and write permissions**. Click **Save**.
3. Click the **Actions** tab at the top of your GitHub repository.
4. Select **Discord Job Monitor** on the left.
5. Click **Run workflow** -> **Run workflow** to test it immediately!

🎉 **Congratulations!** Your bot will now run automatically every 5 minutes 24/7 without needing your PC to stay on!

---

## 🧪 Local Testing (Optional)

If you want to test the bot on your computer locally:
1. Rename `.env.example` to `.env`.
2. Fill in your keys inside `.env`.
3. Run:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
