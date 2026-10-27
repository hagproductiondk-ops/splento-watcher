# Splento Denmark watcher

Checks the Splento dashboard every 10 minutes, 24/7, on GitHub Actions. When a
new job in Denmark shows up under **Sessions awaiting photographers**, it sends
you a Telegram message with the title, date, address and a link.

## 1. Create a Telegram bot (2 minutes)

1. In Telegram, open a chat with **@BotFather** and send `/newbot`.
2. Pick a name and a username (must end in `bot`). BotFather replies with a
   **token** like `123456789:AA...`. Keep it secret.
3. Open a chat with your new bot and send it any message, e.g. `hi`.
4. In a browser, open
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   and find `"chat":{"id":123456789` — that number is your **chat ID**.

## 2. Create the GitHub repository

1. Go to <https://github.com/new>.
2. Name it e.g. `splento-watcher`.
3. Choose **Public**. Public repos get unlimited free Actions minutes; private
   repos get 2,000 min/month, which is not enough for a check every 10 minutes.
   Your password and Telegram token are stored as encrypted secrets and are
   never visible. The repo only contains this code and a list of session ID
   numbers, and the logs only show counts.
   (If you prefer **Private**, change `*/10` to `*/30` in
   `.github/workflows/watch.yml` to stay within the free minutes.)
4. Upload all files from this folder, including the hidden `.github` folder.
   Easiest: on the empty repo page click **uploading an existing file** and
   drag the files in. To include `.github/workflows/watch.yml`, you can instead
   click **Add file → Create new file**, type the name
   `.github/workflows/watch.yml` and paste its contents.

## 3. Add your secrets

In the repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add these four:

| Name | Value |
|---|---|
| `SPLENTO_USERNAME` | your Splento login |
| `SPLENTO_PASSWORD` | your Splento password |
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | the chat ID number from step 1 |

## 4. Switch it on and test

1. Open the **Actions** tab. If asked, click **I understand my workflows, go
   ahead and enable them**.
2. Click **Splento Denmark watcher → Run workflow**, tick **Only send a
   Telegram test message**, and run. You should get a ✅ message in Telegram.
3. Run it again without the tick. The first real run sends you all Denmark jobs
   that are open right now; after that you only get new ones.

From then on it runs by itself every 10 minutes (GitHub sometimes delays
scheduled runs by a few minutes).

## Good to know

- **If a run fails** (wrong password, Splento changed their page, site down),
  GitHub emails you about the failed run. Check the run's log in the Actions tab.
- **If you change your Splento password**, update the `SPLENTO_PASSWORD` secret.
- **To pause it:** Actions → Splento Denmark watcher → **⋯ → Disable workflow**.
- A job that disappears and later comes back (e.g. a photographer dropped out)
  is sent again.
- Denmark is detected by addresses ending in `, DK` or containing
  "Denmark"/"Danmark".
