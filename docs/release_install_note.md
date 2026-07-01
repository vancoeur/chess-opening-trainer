---

## Install

Download `Opening Trainer.app.zip` below, unzip, and move **Opening Trainer.app** to your Applications folder. **Apple Silicon (M1 or newer) only.**

**First launch — Gatekeeper.** The app is free and open-source but **not notarised**, so macOS blocks it on first launch (on Apple Silicon often as *“… is damaged”* — it is **not** damaged, just unsigned).

**Reliable fix — remove the quarantine flag (Terminal):**
1. Open **Terminal** (Applications → Utilities → Terminal).
2. Type or copy this — do **not** press Enter yet:
   `xattr -dr com.apple.quarantine`
3. Press the **spacebar once** (there must be a space after the command).
4. **Drag `Opening Trainer.app` from Finder into the Terminal window**, then press **Enter**.
5. Open the app by double-click.

Alternative: open once, dismiss the warning, then **System Settings → Privacy & Security → “Open Anyway”**. You only need to do this once.
